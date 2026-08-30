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


def exact_order(distance):
    positions = np.arange(1, distance)
    return np.exp(distance * np.log(2 / np.pi) - np.sum((distance - positions) * np.log1p(-1 / (4 * positions**2))))


class Model:
    def __init__(self, tensor, samples=64, precondition=0):
        self.half = tensor.shape[1] // 2
        half = self.half
        self.base = torch.tensor(np.stack((tensor[0, :half, :half], tensor[0, half:, half:], tensor[1, :half, half:], tensor[1, half:, :half])))
        basis = []
        for row in range(half):
            for col in range(row, half):
                matrix = np.zeros((half, half))
                matrix[row, col] = 1 if row == col else 1 / np.sqrt(2)
                matrix[col, row] = matrix[row, col]
                basis.append(matrix.ravel())
        self.basis = torch.tensor(np.array(basis).T.copy())
        self.sym = self.basis.shape[1]
        self.ident = torch.eye(half)
        self.iv = torch.cat([self.ident.flatten() @ self.basis] * 2)
        self.transposition = torch.tensor(np.arange(half**2).reshape(half, half).T.flatten())
        self.distances = [np.unique(np.r_[np.arange(1, 17), np.rint(np.geomspace(1, maximum, samples)).astype(int)]) for maximum in (1024, 256, 128)]
        self.targets = [torch.tensor([exact_order(distance) for distance in self.distances[0]]),
                        torch.tensor(4 / (np.pi**2 * (4 * self.distances[1]**2 - 1))),
                        torch.tensor([-exact_order(distance) / (4 * distance**2 - 1) for distance in self.distances[2]])]
        self.masks = [[torch.tensor(((distances - 1) & (1 << bit)) != 0)[:, None] for bit in range(int(max(distances) - 1).bit_length())] for distances in self.distances]
        self.scale = torch.eye(half).repeat(4, 1, 1)
        if precondition:
            with torch.no_grad():
                blocks = self.canonical(torch.zeros_like(self.base))
                even, rho, rho_top, rho_bottom = self.stationary(blocks)
                scales = []
                for density in (rho_top, rho_bottom, rho_top, rho_bottom):
                    eigenvalues, vectors = torch.linalg.eigh(density)
                    scales.append((vectors * eigenvalues.clamp(min=1e-8).pow(-precondition / 2)) @ vectors.T)
                self.scale = torch.stack(scales)

    def canonical(self, parameters):
        raw = self.base + self.scale @ parameters
        top = torch.cat((raw[0], raw[2]), dim=1)
        bottom = torch.cat((raw[3], raw[1]), dim=1)
        top = torch.linalg.solve_triangular(torch.linalg.cholesky(top @ top.T), top, upper=False)
        bottom = torch.linalg.solve_triangular(torch.linalg.cholesky(bottom @ bottom.T), bottom, upper=False)
        return top[:, :self.half], bottom[:, self.half:], top[:, self.half:], bottom[:, :self.half]

    def kron(self, first, second):
        return torch.einsum('ac,bd->abcd', first, second).reshape(self.half**2, self.half**2)

    def stationary(self, blocks):
        top, bottom, upper, lower = blocks
        basis = self.basis
        components = [basis.T @ self.kron(matrix, matrix) @ basis for matrix in (top, upper, lower, bottom)]
        even = torch.cat((torch.cat(components[:2], dim=1), torch.cat(components[2:], dim=1)), dim=0)
        rho = torch.linalg.solve(torch.eye(2 * self.sym) - even.T + torch.outer(self.iv, self.iv) / (2 * self.half), self.iv / (2 * self.half))
        rho_top = (basis @ rho[:self.sym]).reshape(self.half, self.half)
        rho_bottom = (basis @ rho[self.sym:]).reshape(self.half, self.half)
        return even, rho, rho_top, rho_bottom

    def correlations(self, transfer, right, left, family):
        environments = right[None, :].expand(len(self.distances[family]), -1)
        for bit, mask in enumerate(self.masks[family]):
            environments = torch.where(mask, environments @ transfer.T, environments)
            if bit + 1 < len(self.masks[family]):
                transfer = transfer @ transfer
        return environments @ left

    def observables(self, parameters):
        blocks = self.canonical(parameters)
        top, bottom, upper, lower = blocks
        even, rho, rho_top, rho_bottom = self.stationary(blocks)
        direct = self.kron(top, bottom)
        exchange = self.kron(upper, lower)[:, self.transposition]
        right_x = (top @ lower.T + upper @ bottom.T).flatten()
        left_x = 2 * (top.T @ rho_top @ upper + lower.T @ rho_bottom @ bottom).flatten()
        right_y = (top @ lower.T - upper @ bottom.T).flatten()
        left_y = 2 * (-top.T @ rho_top @ upper + lower.T @ rho_bottom @ bottom).flatten()
        right_z = torch.cat(((top @ top.T - upper @ upper.T).flatten() @ self.basis, (bottom @ bottom.T - lower @ lower.T).flatten() @ self.basis))
        left_z = torch.cat(((top.T @ rho_top @ top - lower.T @ rho_bottom @ lower).flatten() @ self.basis, (bottom.T @ rho_bottom @ bottom - upper.T @ rho_top @ upper).flatten() @ self.basis))
        transverse = rho @ right_z
        order = self.correlations(direct + exchange, right_x, left_x, 0)
        density = self.correlations(even - torch.outer(self.iv, rho), right_z - transverse * self.iv, left_z - transverse * rho, 1)
        y_spin = self.correlations(direct - exchange, right_y, left_y, 2)
        energy = 4 / np.pi - order[0] - transverse
        return energy, (order, density, y_spin)

    def tensor(self, parameters):
        with torch.no_grad():
            blocks = self.canonical(torch.tensor(parameters).reshape(self.base.shape))
            result = np.zeros((2, 2 * self.half, 2 * self.half))
            result[0, :self.half, :self.half] = blocks[0].numpy()
            result[0, self.half:, self.half:] = blocks[1].numpy()
            result[1, :self.half, self.half:] = blocks[2].numpy()
            result[1, self.half:, :self.half] = blocks[3].numpy()
            return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default=str(ROOT / 'state.npz'))
    parser.add_argument('--prefix', default='run1')
    parser.add_argument('--iterations', type=int, default=3000)
    parser.add_argument('--seconds', type=float, default=1800)
    parser.add_argument('--precondition', type=float, default=0)
    parser.add_argument('--samples', type=int, default=64)
    parser.add_argument('--energy-weight', type=float, default=1)
    parser.add_argument('--power', type=int, default=2)
    parser.add_argument('--check-gradient', action='store_true')
    args = parser.parse_args()
    tensor = np.load(args.input)['A'].real
    model = Model(tensor, args.samples, args.precondition)
    started = time.monotonic()
    evaluations = 0
    best = float('inf')
    log = open(ROOT / (args.prefix + '.jsonl'), 'a', buffering=1)

    def objective(flat):
        nonlocal evaluations, best
        parameters = torch.tensor(flat.reshape(model.base.shape), requires_grad=True)
        energy, correlations = model.observables(parameters)
        errors = [(values / target - 1) / tolerance for values, target, tolerance in zip(correlations, model.targets, (.025, .1, .1))]
        energy_error = energy / 5e-5
        loss = args.energy_weight * energy_error.square() + sum(error.pow(args.power).mean() for error in errors)
        loss.backward()
        value = loss.item()
        maxima = [error.detach().abs().max().item() for error in errors]
        worst = max(energy_error.item(), *maxima)
        evaluations += 1
        if worst < best:
            best = worst
            np.savez(ROOT / (args.prefix + '_best.npz'), A=model.tensor(flat))
        if evaluations % 20 == 0 or evaluations == 1:
            entry = dict(evaluation=evaluations, seconds=round(time.monotonic() - started, 2), loss=value, energy=energy.item(), relative_errors=[maximum * tolerance for maximum, tolerance in zip(maxima, (.025, .1, .1))], worst=worst, best=best, gradient=float(parameters.grad.norm()))
            print(json.dumps(entry), flush=True)
            log.write(json.dumps(entry) + '\n')
            np.savez(ROOT / (args.prefix + '_last.npz'), A=model.tensor(flat))
        if time.monotonic() - started > args.seconds:
            raise TimeoutError('time budget reached')
        return value, parameters.grad.numpy().ravel().copy()

    initial = np.zeros(model.base.numel())
    if args.check_gradient:
        value, gradient = objective(initial)
        direction = np.random.default_rng(42).normal(size=initial.shape)
        direction /= np.linalg.norm(direction)
        for delta in (1e-5, 1e-6, 1e-7):
            forward = objective(initial + delta * direction)[0]
            backward = objective(initial - delta * direction)[0]
            print('gradient', delta, gradient @ direction, (forward - backward) / (2 * delta), flush=True)
        return
    try:
        result = so.minimize(objective, initial, jac=True, method='L-BFGS-B', options=dict(maxiter=args.iterations, maxcor=50, ftol=1e-14, gtol=1e-9, maxls=30))
        print(result.message, flush=True)
        np.savez(ROOT / (args.prefix + '_final.npz'), A=model.tensor(result.x))
    except TimeoutError as error:
        print(error, flush=True)


if __name__ == '__main__':
    main()
