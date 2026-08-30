import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import argparse
import json
import time
from pathlib import Path

import numpy as np
import scipy.optimize
import torch

torch.set_num_threads(1)
torch.set_default_dtype(torch.float64)


def exact_orders():
    values = []
    for distance in range(1, 129):
        indices = np.arange(distance)
        matrix = 2 / (np.pi * (2 * (indices[:, None] - indices[None, :]) + 1))
        sign, logdet = np.linalg.slogdet(matrix)
        values.append(sign * np.exp(logdet))
    return torch.tensor(values)


class Model:
    def __init__(self, dimension):
        self.dimension = dimension
        self.half = dimension // 2
        self.eye = torch.eye(dimension)
        self.block_eye = torch.eye(self.half).reshape(-1)
        self.trace = torch.cat((self.block_eye, self.block_eye))
        self.system_eye = torch.eye(2 * self.half**2)
        self.rank_one = self.trace[:, None] * self.trace[None, :] / dimension
        self.order_exact = exact_orders()
        distances = torch.arange(1, 33)
        self.density_exact = 4 / (np.pi**2 * (4 * distances**2 - 1))

    def tensor(self, parameters):
        raw = parameters.reshape(2, 2 * self.half, self.half)
        orthogonal, triangular = torch.linalg.qr(raw)
        signs = torch.sign(torch.diagonal(triangular, dim1=-2, dim2=-1))
        orthogonal = orthogonal * signs[:, None, :]
        rows = orthogonal.transpose(1, 2)
        upper_zero, upper_one = rows[0, :, :self.half], rows[0, :, self.half:]
        lower_zero, lower_one = rows[1, :, :self.half], rows[1, :, self.half:]
        zero = torch.zeros_like(upper_zero)
        physical_zero = torch.cat((torch.cat((upper_zero, zero), 1), torch.cat((zero, lower_zero), 1)), 0)
        physical_one = torch.cat((torch.cat((zero, upper_one), 1), torch.cat((lower_one, zero), 1)), 0)
        return torch.stack((physical_zero, physical_one)), (upper_zero, upper_one, lower_zero, lower_one)

    def stationary(self, blocks):
        upper_zero, upper_one, lower_zero, lower_one = blocks
        def product(block):
            return torch.einsum('ac,bd->abcd', block, block).reshape(self.half**2, self.half**2)
        transfer = torch.cat((torch.cat((product(upper_zero), product(upper_one)), 1),
                              torch.cat((product(lower_one), product(lower_zero)), 1)), 0)
        density = torch.linalg.solve(self.system_eye - transfer.T + self.rank_one, self.trace / self.dimension)
        density = density.reshape(2, self.half, self.half)
        zero = torch.zeros_like(density[0])
        return torch.cat((torch.cat((density[0], zero), 1), torch.cat((zero, density[1]), 1)), 0)

    def observables(self, parameters, full=True):
        tensor, blocks = self.tensor(parameters)
        density = self.stationary(blocks)
        physical_zero, physical_one = tensor.unbind()
        def transfer(matrix):
            return physical_zero @ matrix @ physical_zero.T + physical_one @ matrix @ physical_one.T
        order_environment = physical_zero @ physical_one.T + physical_one @ physical_zero.T
        order_left = physical_zero.T @ density @ physical_one + physical_one.T @ density @ physical_zero
        density_environment = physical_zero @ physical_zero.T - physical_one @ physical_one.T
        transverse = torch.sum(density * density_environment.T)
        order_one = torch.sum(order_left * order_environment.T)
        energy = -order_one - transverse
        if not full:
            return energy, tensor
        density_left = physical_zero.T @ density @ physical_zero - physical_one.T @ density @ physical_one
        density_environment = density_environment - transverse * self.eye
        order_values = []
        density_values = []
        for distance in range(128):
            order_values.append(torch.sum(order_left * order_environment.T))
            if distance < 32:
                density_values.append(torch.sum(density_left * density_environment.T))
                density_environment = transfer(density_environment)
            order_environment = transfer(order_environment)
        return energy, torch.stack(order_values), torch.stack(density_values), tensor


def parameters_from_tensor(tensor):
    half = tensor.shape[-1] // 2
    rows = np.stack((np.concatenate((tensor[0, :half, :half], tensor[1, :half, half:]), 1),
                     np.concatenate((tensor[0, half:, half:], tensor[1, half:, :half]), 1)))
    return rows.transpose(0, 2, 1).copy().reshape(-1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dimension', type=int, default=24)
    parser.add_argument('--iterations', type=int, default=1000)
    parser.add_argument('--mode', choices=['energy', 'witness', 'feasible'], default='energy')
    parser.add_argument('--initial')
    parser.add_argument('--output', default='state.npz')
    parser.add_argument('--seed', type=int, default=5582)
    parser.add_argument('--energy-weight', type=float, default=1.0)
    parser.add_argument('--margin', type=float, default=0.8)
    arguments = parser.parse_args()
    model = Model(arguments.dimension)
    random = np.random.default_rng(arguments.seed)
    if arguments.initial:
        initial_tensor = np.load(arguments.initial)['A'].real
        if initial_tensor.shape[-1] != arguments.dimension:
            old_half = initial_tensor.shape[-1] // 2
            half = model.half
            tensor = np.zeros((2, arguments.dimension, arguments.dimension))
            indices = np.r_[np.arange(old_half), half + np.arange(old_half)]
            tensor[:, indices[:, None], indices] = initial_tensor
            for physical in range(2):
                noise = random.standard_normal(tensor[physical].shape) * 0.015
                parity = np.r_[np.ones(half), -np.ones(half)]
                noise *= parity[:, None] * parity[None, :] == (-1)**physical
                tensor[physical] += noise
            for index in np.r_[np.arange(old_half, half), half + np.arange(old_half, half)]:
                tensor[0, index, index] += 0.7
            initial_tensor = tensor
        initial = parameters_from_tensor(initial_tensor)
    else:
        half = model.half
        raw = random.standard_normal((2, 2 * half, half)) * 0.2 / np.sqrt(half)
        raw[:, :half, :] += np.eye(half)[None, :, :] * 0.8
        raw[:, half:, :] += np.eye(half)[None, :, :] * 0.3
        initial = raw.reshape(-1)
    started = time.monotonic()
    count = 0
    best = np.inf
    best_quality = np.inf

    def objective(values):
        nonlocal count, best, best_quality
        parameters = torch.tensor(values, requires_grad=True)
        if arguments.mode == 'energy':
            energy, tensor = model.observables(parameters, full=False)
            loss = energy
        else:
            energy, order, density, tensor = model.observables(parameters)
            order_error = (order / model.order_exact - 1) / 0.025
            density_error = (density / model.density_exact - 1) / 0.1
            energy_error = (energy + 4 / np.pi) / 5e-5
            if arguments.mode == 'feasible':
                loss = (arguments.energy_weight * torch.relu(energy_error - arguments.margin)**2
                        + torch.relu(order_error.abs() - arguments.margin).square().mean()
                        + torch.relu(density_error.abs() - arguments.margin).square().mean())
            else:
                loss = (arguments.energy_weight * energy_error**2 + order_error.square().mean() + density_error.square().mean())
        loss.backward()
        count += 1
        numeric_loss = float(loss.detach())
        if arguments.mode == 'energy':
            quality = float(energy.detach())
        else:
            quality = max(float(energy_error.detach()), float(order_error.detach().abs().max()), float(density_error.detach().abs().max()))
        if quality < best_quality:
            best_quality = quality
            np.savez(arguments.output, A=tensor.detach().numpy())
        if numeric_loss < best:
            best = numeric_loss
        if count % 50 == 0 or count == 1:
            message = {'evaluations': count, 'seconds': round(time.monotonic() - started, 2), 'loss': numeric_loss,
                       'energy_excess': float(energy.detach()) + 4 / np.pi, 'best_quality': best_quality}
            if arguments.mode != 'energy':
                message.update(order_error=float(order_error.detach().abs().max()) * 0.025,
                               density_error=float(density_error.detach().abs().max()) * 0.1)
            print(json.dumps(message), flush=True)
        return numeric_loss, parameters.grad.numpy()

    result = scipy.optimize.minimize(objective, initial, jac=True, method='L-BFGS-B',
                                     options={'maxiter': arguments.iterations, 'maxls': 40, 'maxcor': 50,
                                              'ftol': 1e-15, 'gtol': 1e-10})
    np.savez(Path(arguments.output).with_suffix('.last.npz'), A=model.tensor(torch.tensor(result.x))[0].numpy())
    print(str(result.message), 'iterations', result.nit, flush=True)


if __name__ == '__main__':
    main()
