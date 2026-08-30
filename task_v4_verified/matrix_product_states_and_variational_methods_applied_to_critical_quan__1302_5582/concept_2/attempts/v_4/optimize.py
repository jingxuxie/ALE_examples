import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import json
import time
from pathlib import Path
import numpy as np
import scipy.optimize as so
import torch

torch.set_num_threads(1)
torch.set_default_dtype(torch.float64)
ROOT = Path(__file__).resolve().parent
ASSETS = ROOT.parents[1] / 'participant'


def basis(parity, symmetric=True):
    first, second, weight_first, weight_second = [], [], [], []
    for row in range(24):
        for col in range(row if symmetric else row + 1, 24):
            if ((row < 12) == (col < 12)) != parity:
                continue
            first.append(row * 24 + col)
            second.append(col * 24 + row)
            weight_first.append(1.0 if row == col else 2**-0.5)
            weight_second.append(0.0 if row == col else (1 if symmetric else -1) * 2**-0.5)
    return (torch.tensor(first), torch.tensor(second), torch.tensor(weight_first), torch.tensor(weight_second))


BASES = [basis(True), basis(False), basis(False, False)]


def reduce_vector(matrix, spec):
    first, second, weight_first, weight_second = spec
    flat = matrix.reshape(-1)
    return flat[first] * weight_first + flat[second] * weight_second


def expand_vector(vector, spec):
    first, second, weight_first, weight_second = spec
    result = torch.zeros(576)
    result = result.scatter_add(0, first, vector * weight_first)
    result = result.scatter_add(0, second, vector * weight_second)
    return result.reshape(24, 24)


def reduce_transfer(transfer, spec):
    first, second, weight_first, weight_second = spec
    result = transfer[first[:, None], first] * weight_first[:, None] * weight_first
    result = result + transfer[first[:, None], second] * weight_first[:, None] * weight_second
    result = result + transfer[second[:, None], first] * weight_second[:, None] * weight_first
    result = result + transfer[second[:, None], second] * weight_second[:, None] * weight_second
    return result


def canonical(parameters):
    blocks = parameters.reshape(2, 12, 24)
    orthogonal, triangular = torch.linalg.qr(blocks.transpose(-1, -2))
    signs = torch.sign(torch.diagonal(triangular, dim1=-2, dim2=-1))
    blocks = (orthogonal * signs[:, None, :]).transpose(-1, -2)
    zeros = torch.zeros(12, 12)
    even = torch.cat((torch.cat((blocks[0, :, :12], zeros), 1), torch.cat((zeros, blocks[1, :, :12]), 1)), 0)
    odd = torch.cat((torch.cat((zeros, blocks[0, :, 12:]), 1), torch.cat((blocks[1, :, 12:], zeros), 1)), 0)
    return torch.stack((even, odd))


def correlations(transfer, right, left, levels):
    vectors = right[:, None]
    power = transfer
    for level in range(levels):
        vectors = torch.cat((vectors, power @ vectors), dim=1)
        if level + 1 < levels:
            power = power @ power
    return left @ vectors


def observables(tensor):
    transfer = torch.einsum('sac,sbd->abcd', tensor, tensor).reshape(576, 576)
    even, order, spin_y = [reduce_transfer(transfer, spec) for spec in BASES]
    identity = torch.eye(24)
    identity_vector = reduce_vector(identity, BASES[0])
    rho_vector = torch.linalg.solve(torch.eye(len(identity_vector)) - even.T + torch.outer(identity_vector, identity_vector), identity_vector)
    rho = expand_vector(rho_vector, BASES[0])
    physical_even, physical_odd = tensor
    right_x = physical_even @ physical_odd.T + physical_odd @ physical_even.T
    right_y = physical_even @ physical_odd.T - physical_odd @ physical_even.T
    right_z = physical_even @ physical_even.T - physical_odd @ physical_odd.T
    left_x = physical_even.T @ rho @ physical_odd + physical_odd.T @ rho @ physical_even
    left_y = physical_odd.T @ rho @ physical_even - physical_even.T @ rho @ physical_odd
    left_z = physical_even.T @ rho @ physical_even - physical_odd.T @ rho @ physical_odd
    magnetization = torch.sum(rho * right_z)
    order_values = correlations(order, reduce_vector(right_x, BASES[1]), reduce_vector(left_x, BASES[1]), 10)
    y_values = correlations(spin_y, reduce_vector(right_y, BASES[2]), reduce_vector(left_y, BASES[2]), 7)
    density_values = correlations(even - torch.outer(identity_vector, rho_vector), reduce_vector(right_z - magnetization * identity, BASES[0]), reduce_vector(left_z - magnetization * rho, BASES[0]), 8)
    energy_excess = 4 / np.pi - magnetization - order_values[0]
    return energy_excess, order_values, density_values, y_values


def targets():
    distances = np.arange(1, 1025)
    exact_order = np.array([np.exp(distance * np.log(2 / np.pi) - np.sum((distance - np.arange(1, distance)) * np.log1p(-1 / (4 * np.arange(1, distance)**2)))) for distance in distances])
    return [torch.tensor(exact_order), torch.tensor(4 / (np.pi**2 * (4 * distances[:256]**2 - 1))), torch.tensor(-exact_order[:128] / (4 * distances[:128]**2 - 1))]


def parameters_from_tensor(tensor):
    return np.stack((np.concatenate((tensor[0, :12, :12], tensor[1, :12, 12:]), 1), np.concatenate((tensor[0, 12:, 12:], tensor[1, 12:, :12]), 1))).reshape(-1).real


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default=str(ASSETS / 'baseline/state.npz'))
    parser.add_argument('--seconds', type=float, default=2400)
    parser.add_argument('--maxiter', type=int, default=10000)
    parser.add_argument('--energy-weight', type=float, default=1.0)
    parser.add_argument('--power', type=float, default=2.0)
    parser.add_argument('--tag', default='run')
    parser.add_argument('--margin', type=float, default=1.0)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    initial = np.load(args.input)['A']
    exact = targets()
    started = time.monotonic()
    count = 0
    best = float('inf')
    best_score = 0
    best_rank = (0, -float('inf'))
    log = (ROOT / (args.tag + '.jsonl')).open('a', buffering=1)

    def objective(parameters):
        nonlocal count, best, best_score, best_rank
        raw = torch.tensor(parameters, requires_grad=True)
        tensor = canonical(raw)
        energy, *values = observables(tensor)
        errors = [(value / target - 1) / tolerance for value, target, tolerance in zip(values, exact, [0.025, 0.1, 0.1])]
        energy_error = energy / 5e-5
        loss = args.energy_weight * energy_error.square()
        for error in errors:
            loss = loss + (error.abs() ** args.power).mean() ** (2 / args.power)
        loss.backward()
        count += 1
        worst = [float(energy_error.detach())] + [float(error.detach().abs().max()) for error in errors]
        quality = float(np.prod(np.minimum(1, 1 / np.maximum(worst, 1e-20))) ** .25)
        objective_value = float(loss.detach())
        rank = (quality, -max(worst))
        if rank > best_rank:
            best_rank = rank
            best_score = quality
            np.savez(ROOT / 'state.npz', A=tensor.detach().numpy())
            np.savez(ROOT / (args.tag + '_best.npz'), A=tensor.detach().numpy())
        if objective_value < best:
            best = objective_value
            np.savez(ROOT / (args.tag + '_loss.npz'), A=tensor.detach().numpy())
        if count % 10 == 1 or quality >= 1:
            record = dict(evaluation=count, seconds=time.monotonic()-started, loss=objective_value, normalized_errors=worst, score=quality, best_score=best_score)
            print(json.dumps(record), flush=True)
            log.write(json.dumps(record)+'\n')
        if time.monotonic() - started > args.seconds or max(worst) <= args.margin:
            np.savez(ROOT / (args.tag + '_last.npz'), A=tensor.detach().numpy())
            raise StopIteration
        return objective_value, raw.grad.numpy()

    parameters = parameters_from_tensor(initial)
    if args.check:
        value, gradient = objective(parameters)
        direction = np.random.default_rng(52).normal(size=parameters.size)
        direction /= np.linalg.norm(direction)
        step = 1e-6
        upper, _ = objective(parameters + step * direction)
        lower, _ = objective(parameters - step * direction)
        print('gradient', np.dot(gradient, direction), (upper-lower)/(2*step), flush=True)
        return
    try:
        result = so.minimize(objective, parameters, jac=True, method='L-BFGS-B', options={'maxiter':args.maxiter, 'maxls':40, 'maxcor':50, 'ftol':1e-15, 'gtol':1e-9})
        print(result.message, flush=True)
        np.savez(ROOT / (args.tag + '_last.npz'), A=canonical(torch.tensor(result.x)).numpy())
    except StopIteration:
        print('Stopped at time limit or passing witness.', flush=True)


if __name__ == '__main__':
    main()
