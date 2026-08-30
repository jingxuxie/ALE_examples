import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import scipy.linalg as sla
import scipy.optimize as spo
import torch

from physics import COMPOSITE_QUARTETS, exact_composite_covariance, exact_density, exact_order, metrics, stationary

torch.set_num_threads(1)
torch.set_default_dtype(torch.float64)


def as_tensor(value):
    return torch.as_tensor(value, dtype=torch.float64)


class Model:
    def __init__(self, initial, precondition=0.0):
        self.half = initial.shape[1] // 2
        half = self.half
        density = stationary(initial)[0].real
        rotations = [sla.eigh(density[start:start+half, start:start+half])[1][:, ::-1].copy() for start in (0, half)]
        rotation = sla.block_diag(*rotations)
        initial = np.einsum('ab,sbc,cd->sad', rotation.T, initial, rotation)
        density = rotation.T @ density @ rotation
        self.scale = as_tensor(np.maximum(np.diag(density), 1e-5) ** (-precondition))[:, None]
        self.base = as_tensor(np.concatenate((np.concatenate((initial[0, :half, :half], initial[1, :half, half:]), axis=1), np.concatenate((initial[1, half:, :half], initial[0, half:, half:]), axis=1)), axis=0))
        columns = []
        for row in range(half):
            for col in range(row, half):
                value = np.zeros((half, half))
                value[row, col] = 1.0 if row == col else 1 / np.sqrt(2)
                value[col, row] = value[row, col]
                columns.append(value.ravel())
        self.sym = as_tensor(np.array(columns).T)
        self.ns = self.sym.shape[1]
        self.ident = torch.cat([self.sym.T @ torch.eye(half).reshape(-1)] * 2)
        self.perm = torch.arange(half * half).reshape(half, half).T.reshape(-1)
        self.orders = np.unique(np.r_[np.arange(1, 33), np.rint(np.geomspace(33, 1024, 65)).astype(int), [16, 32, 64, 96]])
        self.densities = np.unique(np.r_[np.arange(1, 17), np.rint(np.geomspace(17, 256, 45)).astype(int)])
        self.ys = np.unique(np.r_[np.arange(1, 17), np.rint(np.geomspace(17, 128, 35)).astype(int)])
        self.exorder = as_tensor([exact_order(int(distance)) for distance in self.orders])
        self.exdensity = as_tensor([exact_density(int(distance)) for distance in self.densities])
        self.exy = as_tensor([-exact_order(int(distance))/(4*distance*distance-1) for distance in self.ys])
        self.excomp = as_tensor([exact_composite_covariance(quartet) for quartet in COMPOSITE_QUARTETS])
        intervals = [16, 32, 64, 96]
        gaps = [32, 64, 96, 128]
        self.left_idx = torch.tensor([intervals.index(second-first) for first, second, third, fourth in COMPOSITE_QUARTETS])
        self.right_idx = torch.tensor([gaps.index(third-second)*4+intervals.index(fourth-third) for first, second, third, fourth in COMPOSITE_QUARTETS])

    def canonical(self, parameters):
        half = self.half
        matrices = (self.base + parameters.reshape(2*half, 2*half) * self.scale).reshape(2, half, 2*half)
        chol = torch.linalg.cholesky(matrices @ matrices.mT)
        matrices = torch.linalg.solve_triangular(chol, matrices, upper=False)
        return matrices[0, :, :half].contiguous(), matrices[0, :, half:].contiguous(), matrices[1, :, :half].contiguous(), matrices[1, :, half:].contiguous()

    def tensor(self, parameters):
        block_a, block_b, block_c, block_d = self.canonical(as_tensor(parameters))
        zeros = torch.zeros_like(block_a)
        even_tensor = torch.cat((torch.cat((block_a, zeros), 1), torch.cat((zeros, block_d), 1)))
        odd_tensor = torch.cat((torch.cat((zeros, block_b), 1), torch.cat((block_c, zeros), 1)))
        return torch.stack((even_tensor, odd_tensor))

    def maps(self, parameters):
        block_a, block_b, block_c, block_d = self.canonical(parameters)
        sym = self.sym
        def reduced(first, second):
            return sym.T @ torch.kron(first, second) @ sym
        map_aa = reduced(block_a, block_a)
        map_bb = reduced(block_b, block_b)
        map_cc = reduced(block_c, block_c)
        map_dd = reduced(block_d, block_d)
        even = torch.cat((torch.cat((map_aa, map_bb), 1), torch.cat((map_cc, map_dd), 1)))
        density_map = torch.cat((torch.cat((map_aa, -map_bb), 1), torch.cat((-map_cc, map_dd), 1)))
        odd_direct = torch.kron(block_a, block_d)
        odd_cross = torch.kron(block_b, block_c)[:, self.perm]
        odd = odd_direct + odd_cross
        odd_y = odd_direct - odd_cross
        cross_ac = torch.kron(block_a, block_c) @ sym
        cross_bd = torch.kron(block_b, block_d) @ sym
        from_even = torch.cat((cross_ac, cross_bd), 1)
        from_even_y = torch.cat((cross_ac, -cross_bd), 1)
        to_even_up = sym.T @ (torch.kron(block_a, block_b) + torch.kron(block_b, block_a)[:, self.perm])
        to_even_down = sym.T @ (torch.kron(block_c, block_d) + torch.kron(block_d, block_c)[:, self.perm])
        to_even = torch.cat((to_even_up, to_even_down))
        to_even_y = torch.cat((-to_even_up, to_even_down))
        return even, odd, odd_y, from_even, to_even, from_even_y, to_even_y, density_map

    def powers(self, matrix, count):
        result = [matrix]
        for unused in range(count-1):
            result.append(result[-1] @ result[-1])
        return result

    def propagate(self, powers, vectors, exponents):
        exponents = np.asarray(exponents)
        if vectors.ndim == 1:
            vectors = vectors[:, None].expand(-1, len(exponents))
        for bit, power in enumerate(powers):
            mask = as_tensor((exponents >> bit) & 1).bool()[None, :]
            vectors = torch.where(mask, power @ vectors, vectors)
        return vectors

    def observables(self, parameters):
        even, odd, odd_y, from_even, to_even, from_even_y, to_even_y, density_map = self.maps(parameters)
        ident = self.ident
        rho = torch.linalg.solve(torch.eye(even.shape[0]) - even.T + ident[:, None]*ident[None, :], ident)
        rho = rho / (rho @ ident)
        odd_powers = self.powers(odd, 10)
        even_powers = self.powers(even, 8)
        y_powers = self.powers(odd_y, 7)
        right_order = from_even @ ident
        left_order = rho @ to_even
        order_values = left_order @ self.propagate(odd_powers, right_order, self.orders-1)
        right_density = density_map @ ident
        transverse = rho @ right_density
        right_density = right_density - transverse * ident
        density_values = (rho @ density_map) @ self.propagate(even_powers, right_density, self.densities-1)
        y_values = (rho @ to_even_y) @ self.propagate(y_powers, from_even_y @ ident, self.ys-1)
        energy = -order_values[0] - transverse + 4/np.pi
        intervals = np.array([16, 32, 64, 96])
        right_intervals = to_even @ self.propagate(odd_powers, right_order, intervals-1)
        means = rho @ right_intervals
        right_intervals = right_intervals - ident[:, None]*means[None, :]
        left_intervals = self.propagate([power.T for power in odd_powers], left_order, intervals-1).T @ from_even
        environments = self.propagate(even_powers, right_intervals.repeat(1, 4), np.repeat([31, 63, 95, 127], 4))
        composite = torch.sum(left_intervals[self.left_idx] * environments[:, self.right_idx].T, dim=1)
        return energy, order_values/self.exorder-1, density_values/self.exdensity-1, y_values/self.exy-1, composite/self.excomp-1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--initial', default='../../participant/baseline/state.npz')
    parser.add_argument('--prefix', default='fit')
    parser.add_argument('--iterations', type=int, default=1500)
    parser.add_argument('--seconds', type=float, default=2400)
    parser.add_argument('--precondition', type=float, default=0.0)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    initial = np.load(args.initial)['A'].real
    model = Model(initial, args.precondition)
    parameters = np.zeros(model.base.numel())
    started = time.monotonic()
    calls = 0
    best = float('inf')
    limits = [5e-5, 0.025, 0.1, 0.1, 0.01]

    def objective(values):
        nonlocal calls, best
        parameters_t = as_tensor(values).requires_grad_(True)
        observables = model.observables(parameters_t)
        scaled = [value / limit for value, limit in zip(observables, limits)]
        maxima = np.array([float(value.detach().abs().max()) for value in scaled])
        loss = scaled[-1].square().mean()
        for value in scaled[:-1]:
            loss = loss + 0.02 * value.square().mean() + 10.0 * torch.relu(value.abs()-0.65).square().mean()
        loss.backward()
        calls += 1
        score = max(maxima)
        if score < best and np.isfinite(score):
            best = score
            tensor = model.tensor(values).detach().numpy()
            np.savez(args.prefix+'_best.npz', A=tensor)
            Path(args.prefix+'_best.json').write_text(json.dumps({'calls': calls, 'seconds': time.monotonic()-started, 'loss': float(loss), 'ratios': maxima.tolist()}))
            if score < 1.0:
                np.savez('state.npz', A=tensor)
        if calls % 25 == 0 or calls == 1:
            print(calls, round(time.monotonic()-started, 2), float(loss.detach()), 'ratios', maxima, 'best', best, flush=True)
        if time.monotonic()-started > args.seconds:
            raise TimeoutError('optimization budget complete')
        return float(loss.detach()), parameters_t.grad.detach().numpy().ravel()

    if args.check:
        observables = model.observables(as_tensor(parameters))
        reconstructed = model.tensor(parameters).detach().numpy()
        reference = metrics(reconstructed)
        print('energy comparison', float(observables[0]), reference['energy_excess'])
        for index, family, distances in [(1, 'order_correlations', model.orders), (2, 'density_connected_correlations', model.densities), (3, 'y_correlations', model.ys)]:
            exact = [model.exorder, model.exdensity, model.exy][index-1].numpy()
            reference_errors = np.array(reference[family])[distances-1] / exact - 1
            print(family, 'difference', np.max(np.abs(observables[index].detach().numpy()-reference_errors)))
        reference_comp = np.array(reference['composite_order_covariances'])/model.excomp.numpy()-1
        print('composite difference', np.max(np.abs(observables[-1].detach().numpy()-reference_comp)))
        loss, gradient = objective(parameters)
        direction = np.random.default_rng(5).normal(size=parameters.shape)
        direction /= np.linalg.norm(direction)
        for step in [1e-5, 1e-6, 1e-7]:
            positive = objective(parameters+step*direction)[0]
            negative = objective(parameters-step*direction)[0]
            print('gradient', step, gradient @ direction, (positive-negative)/(2*step), flush=True)
        return
    try:
        result = spo.minimize(objective, parameters, method='L-BFGS-B', jac=True, options={'maxiter': args.iterations, 'maxls': 35, 'maxcor': 30, 'ftol': 1e-15, 'gtol': 1e-8})
        print(result.message, result.fun, result.nit, flush=True)
        np.savez(args.prefix+'_last.npz', A=model.tensor(result.x).detach().numpy())
    except TimeoutError as error:
        print(str(error), flush=True)


if __name__ == '__main__':
    main()
