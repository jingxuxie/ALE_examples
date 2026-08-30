import argparse
import json
import os
import sys
import time
from pathlib import Path

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import numpy as np
import scipy.optimize as opt
import torch

torch.set_num_threads(1)
torch.set_default_dtype(torch.float64)
SOURCE = Path(os.environ['SRC'])
sys.path.insert(0, str(SOURCE / 'workspace'))
import physics


def basis(parity, antisymmetric=False):
    rows, columns = [], []
    for row in range(24):
        for column in range(row + int(antisymmetric), 24):
            if ((row < 12) == (column < 12)) == (parity == 0):
                rows.append(row)
                columns.append(column)
    rows, columns = torch.tensor(rows), torch.tensor(columns)
    diagonal = rows == columns
    first = torch.where(diagonal, 1., 2. ** -.5)
    second = torch.where(diagonal, 0., (-1. if antisymmetric else 1.) * 2. ** -.5)
    scale = torch.where(diagonal, 1., 2. ** .5)
    return rows, columns, first, second, scale


EVEN, ODD, SKEW = basis(0), basis(1), basis(1, True)
IDENTITY = (EVEN[0] == EVEN[1]).to(torch.float64)


def reduced(tensor, output, source, operator):
    outrow, outcol, unused_first, unused_second, scale = output
    inrow, incol, first, second, unused_scale = source
    direct = tensor[:, outrow[:, None], inrow[None, :]]
    reverse = tensor[:, outcol[:, None], incol[None, :]]
    crossed = tensor[:, outrow[:, None], incol[None, :]]
    crossed_reverse = tensor[:, outcol[:, None], inrow[None, :]]
    result = torch.zeros((len(outrow), len(inrow)))
    for ket, bra, factor in operator:
        result = result + factor * (direct[ket] * reverse[bra] * first + crossed[ket] * crossed_reverse[bra] * second)
    return scale[:, None] * result


TRANSFER = ((0, 0, 1.), (1, 1, 1.))
XMAP = ((0, 1, 1.), (1, 0, 1.))
YMAP = ((0, 1, 1.), (1, 0, -1.))
ZMAP = ((0, 0, 1.), (1, 1, -1.))


def canonical(parameters):
    gram = parameters @ parameters.transpose(-1, -2)
    factor = torch.linalg.cholesky(gram)
    rows = torch.linalg.solve_triangular(factor, parameters, upper=False)
    zero = torch.zeros((12, 12))
    first = torch.cat((torch.cat((rows[0, :, :12], zero), 1), torch.cat((zero, rows[1, :, 12:]), 1)), 0)
    second = torch.cat((torch.cat((zero, rows[0, :, 12:]), 1), torch.cat((rows[1, :, :12], zero), 1)), 0)
    return torch.stack((first, second))


def parameters_from(tensor):
    return np.stack((np.concatenate((tensor[0, :12, :12], tensor[1, :12, 12:]), 1), np.concatenate((tensor[1, 12:, :12], tensor[0, 12:, 12:]), 1)))


class Powers:
    def __init__(self, transfer):
        self.cache = {0: torch.eye(len(transfer)), 1: transfer}

    def __call__(self, exponent):
        if exponent not in self.cache:
            half = self(exponent // 2)
            result = half @ half
            if exponent % 2:
                result = result @ self.cache[1]
            self.cache[exponent] = result
        return self.cache[exponent]

    def sequence(self, vector, count):
        values = vector[:, None]
        while values.shape[1] < count:
            values = torch.cat((values, self(values.shape[1]) @ values), 1)
        return values[:, :count]


LENGTHS = (16, 32, 64, 96)
GAPS = (32, 64, 96, 128)
QUARTETS = physics.COMPOSITE_QUARTETS
SEXTUPLES = physics.THREE_INTERVAL_SEXTUPLES
FOUR_SPECIFICATIONS = [(LENGTHS.index(second-first), GAPS.index(third-second), LENGTHS.index(fourth-third))
                       for first, second, third, fourth in QUARTETS]
SIX_SPECIFICATIONS = [(LENGTHS.index(second-first), GAPS.index(third-second), LENGTHS.index(fourth-third),
                      GAPS.index(fifth-fourth), LENGTHS.index(sixth-fifth))
                     for first, second, third, fourth, fifth, sixth in SEXTUPLES]
FOUR_INDEX = tuple(torch.tensor([entry[index] for entry in FOUR_SPECIFICATIONS]) for index in range(3))
SIX_INDEX = tuple(torch.tensor([entry[index] for entry in SIX_SPECIFICATIONS]) for index in range(5))
TARGET_ORDER = torch.tensor([physics.exact_order(distance) for distance in range(1, 1025)])
TARGET_DENSITY = torch.tensor([physics.exact_density(distance) for distance in range(1, 257)])
TARGET_Y = -TARGET_ORDER[:128] / (4 * torch.arange(1, 129) ** 2 - 1)
TARGET_FOUR = torch.tensor([physics.exact_composite_covariance(quartet) for quartet in QUARTETS])
TARGET_SIX = torch.tensor([physics.exact_three_interval_cumulant(sextuple) for sextuple in SEXTUPLES])


def observables(tensor):
    even = reduced(tensor, EVEN, EVEN, TRANSFER)
    odd = reduced(tensor, ODD, ODD, TRANSFER)
    skew = reduced(tensor, SKEW, SKEW, TRANSFER)
    xright = reduced(tensor, ODD, EVEN, XMAP)
    xleft = reduced(tensor, EVEN, ODD, XMAP)
    yright = reduced(tensor, SKEW, EVEN, YMAP)
    yleft = reduced(tensor, EVEN, SKEW, YMAP)
    zmap = reduced(tensor, EVEN, EVEN, ZMAP)
    density = torch.linalg.solve(torch.eye(len(even)) - even.T + torch.outer(IDENTITY, IDENTITY) / 24, IDENTITY / 24)
    epower, opower, apower = Powers(even), Powers(odd), Powers(skew)
    order = (density @ xleft) @ opower.sequence(xright @ IDENTITY, 1024)
    transverse = density @ zmap @ IDENTITY
    zright = zmap @ IDENTITY - transverse * IDENTITY
    zleft = density @ zmap - transverse * density
    density_values = zleft @ epower.sequence(zright, 256)
    yvalues = -(density @ yleft) @ apower.sequence(yright @ IDENTITY, 128)
    energy = -transverse - order[0]
    pairs = torch.stack([xleft @ opower(length - 1) @ xright for length in LENGTHS])
    means = torch.einsum('a,lab,b->l', density, pairs, IDENTITY)
    pair_left = torch.einsum('a,lab->lb', density, pairs) - means[:, None] * density
    pair_right = pairs @ IDENTITY - means[:, None] * IDENTITY
    left_gap = torch.stack([pair_left @ epower(gap - 1) for gap in GAPS], 1)
    right_gap = torch.stack([pair_right @ epower(gap - 1).T for gap in GAPS], 0)
    four_all = torch.einsum('lga,ra->lgr', left_gap, pair_right)
    centered = pairs - means[:, None, None] * torch.stack([epower(length + 1) for length in LENGTHS])
    six_all = torch.einsum('lga,mab,hrb->lgmhr', left_gap, centered, right_gap)
    return energy, order, density_values, yvalues, four_all[FOUR_INDEX], six_all[SIX_INDEX]


def errors(values):
    energy, order, density, yvalues, four, six = values
    return ((energy + 4 / np.pi).reshape(1) / 5e-5, (order / TARGET_ORDER - 1) / .025,
            (density / TARGET_DENSITY - 1) / .1, (yvalues / TARGET_Y - 1) / .1,
            (four / TARGET_FOUR - 1) / .01, (six / TARGET_SIX - 1) / .1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='state.npz')
    parser.add_argument('--prefix', default='run1')
    parser.add_argument('--iterations', type=int, default=2000)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--mode', default='squares')
    arguments = parser.parse_args()
    original = np.load(arguments.input)['A']
    initial = parameters_from(original)
    started = time.monotonic()
    calls = 0
    best = np.inf
    logfile = open(arguments.prefix + '.jsonl', 'w', buffering=1)

    def evaluate(flat):
        nonlocal calls, best
        parameters = torch.tensor(flat.reshape(initial.shape), requires_grad=True)
        tensor = canonical(parameters)
        values = observables(tensor)
        residuals = errors(values)
        if arguments.mode == 'hinge':
            loss = sum((torch.relu(residual.abs() - .65) ** 2).mean() + .002 * (residual ** 2).mean() for residual in residuals)
        else:
            loss = sum((residual ** 2).mean() for residual in residuals)
        maxima = [float(residual.detach().abs().max()) for residual in residuals]
        score = max(maxima)
        calls += 1
        if score < best:
            best = score
            np.savez(arguments.prefix + '_best.npz', A=tensor.detach().numpy())
        if calls % 10 == 0 or calls == 1:
            record = dict(call=calls, seconds=time.monotonic()-started, loss=float(loss.detach()), maxima=maxima, best=best)
            print(json.dumps(record), flush=True)
            logfile.write(json.dumps(record) + '\n')
            np.savez(arguments.prefix + '_latest.npz', A=tensor.detach().numpy())
        if arguments.check_only:
            reference = json.load(open('baseline_check.json'))['metrics']
            names = ['energy_density', 'order_correlations', 'density_connected_correlations', 'y_correlations', 'composite_order_covariances', 'three_interval_cumulants']
            for name, value in zip(names, values):
                print(name, np.max(np.abs(value.detach().numpy() - np.asarray(reference[name]))))
        loss.backward()
        gradient = parameters.grad.numpy().ravel().copy()
        return float(loss.detach()), gradient

    if arguments.check_only:
        loss, gradient = evaluate(initial.ravel())
        direction = np.random.default_rng(1).normal(size=initial.size)
        direction /= np.linalg.norm(direction)
        step = 1e-7
        upper, unused_gradient = evaluate(initial.ravel() + step * direction)
        lower, unused_gradient = evaluate(initial.ravel() - step * direction)
        print('gradient check', gradient @ direction, (upper-lower)/(2*step), flush=True)
        return
    result = opt.minimize(evaluate, initial.ravel(), jac=True, method='L-BFGS-B', options=dict(maxiter=arguments.iterations, maxcor=80, ftol=1e-15, gtol=1e-10, maxls=30))
    final = canonical(torch.tensor(result.x.reshape(initial.shape))).numpy()
    np.savez(arguments.prefix + '_final.npz', A=final)
    print(result.message, flush=True)


if __name__ == '__main__':
    main()
