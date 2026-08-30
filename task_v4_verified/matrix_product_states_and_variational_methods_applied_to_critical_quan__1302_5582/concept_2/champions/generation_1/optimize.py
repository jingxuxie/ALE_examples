import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import argparse
import json
import time
from pathlib import Path
import sys
import numpy as np
import scipy.linalg as sla
from scipy.optimize import minimize
import torch

torch.set_num_threads(1)
torch.set_default_dtype(torch.float64)
ASSETS = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/matrix_product_states_and_variational_methods_applied_to_critical_quan__1302_5582/concept_2/participant')
sys.path.insert(0, str(ASSETS / 'workspace'))
from physics import exact_order, metrics, score_metrics


def from_raw(raw):
    half = raw.shape[-1]
    frame_q, frame_r = torch.linalg.qr(raw)
    frames = (frame_q * torch.sign(torch.diagonal(frame_r, dim1=-2, dim2=-1))[:, None, :]).transpose(1, 2)
    block_b, block_c = frames[0, :, :half], frames[0, :, half:]
    block_g, block_f = frames[1, :, :half], frames[1, :, half:]
    zero = torch.zeros_like(block_b)
    tensor = torch.stack((torch.cat((torch.cat((block_b, zero), 1), torch.cat((zero, block_g), 1)), 0),
                          torch.cat((torch.cat((zero, block_c), 1), torch.cat((block_f, zero), 1)), 0)))
    return tensor, (block_b, block_c, block_f, block_g)


def to_raw(tensor):
    half = tensor.shape[1] // 2
    return np.stack((np.concatenate((tensor[0, :half, :half], tensor[1, :half, half:]), 1).T,
                     np.concatenate((tensor[0, half:, half:], tensor[1, half:, :half]), 1).T))


def stationary_blocks(blocks):
    block_b, block_c, block_f, block_g = [block.contiguous() for block in blocks]
    half = block_b.shape[0]
    transfer = torch.cat((torch.cat((torch.kron(block_b, block_b), torch.kron(block_c, block_c)), 1),
                          torch.cat((torch.kron(block_f, block_f), torch.kron(block_g, block_g)), 1)), 0)
    identity = torch.eye(half)
    trace_vector = torch.cat((identity.flatten(), identity.flatten()))
    fixed = torch.linalg.solve(torch.eye(2 * half**2) - transfer.T + torch.outer(trace_vector, trace_vector) / (2 * half),
                               trace_vector / (2 * half))
    zero = torch.zeros_like(identity)
    density = torch.cat((torch.cat((fixed[:half**2].reshape(half, half), zero), 1),
                         torch.cat((zero, fixed[half**2:].reshape(half, half)), 1)), 0)
    return (density + density.T) / 2


def observables(tensor, density, long_range=True):
    first, second = tensor
    order_env = first @ second.T + second @ first.T
    density_env = first @ first.T - second @ second.T
    transverse = torch.sum(density * density_env.T)
    order_left = first.T @ density @ second + second.T @ density @ first
    density_left = first.T @ density @ first - second.T @ density @ second
    order_values = []
    density_values = []
    for distance in range(128 if long_range else 1):
        order_values.append(torch.sum(order_left * order_env.T))
        if distance < 32 and long_range:
            density_values.append(torch.sum(density_left * density_env.T) - transverse**2)
            density_env = first @ density_env @ first.T + second @ density_env @ second.T
        if distance < 127 and long_range:
            order_env = first @ order_env @ first.T + second @ order_env @ second.T
    return -order_values[0] - transverse, torch.stack(order_values), torch.stack(density_values) if long_range else None


def grow(tensor, dimension, seed):
    old_half = tensor.shape[1] // 2
    half = dimension // 2
    rng = np.random.default_rng(seed)
    expanded = np.zeros((2, dimension, dimension))
    indices = np.r_[np.arange(old_half), half + np.arange(old_half)]
    expanded[:, indices[:, None], indices[None, :]] = tensor
    for sector in range(2):
        for index in range(old_half, half):
            expanded[0, sector * half + index, sector * half + index] = 0.4
            expanded[1, sector * half + index, (1 - sector) * half + index % old_half] = np.sqrt(0.84)
    raw = to_raw(expanded)
    raw += 0.002 * rng.normal(size=raw.shape)
    return raw


def run(raw, mode, iterations, prefix, energy_weight=1.0):
    shape = raw.shape
    exact_orders = torch.tensor([exact_order(distance) for distance in range(1, 129)])
    exact_densities = torch.tensor([4 / (np.pi**2 * (4 * distance**2 - 1)) for distance in range(1, 33)])
    started = time.monotonic()
    count = 0
    best = float('inf')
    best_raw = raw.copy()

    def objective(flat):
        nonlocal count, best, best_raw
        variables = torch.tensor(flat.reshape(shape), requires_grad=True)
        tensor, blocks = from_raw(variables)
        density = stationary_blocks(blocks)
        energy, orders, densities = observables(tensor, density, mode != 'energy')
        if mode == 'energy':
            loss = energy
            summary = [float(energy.detach()) + 4 / np.pi]
        else:
            order_error = (orders / exact_orders - 1) / 0.025
            density_error = (densities / exact_densities - 1) / 0.1
            energy_error = (energy + 4 / np.pi) / 5e-5
            loss = energy_weight * energy_error**2 + torch.mean(order_error**2) + torch.mean(density_error**2)
            summary = [float(energy_error.detach()), float(order_error.detach().abs().max()), float(density_error.detach().abs().max())]
        loss.backward()
        value = float(loss.detach())
        count += 1
        if value < best:
            best = value
            best_raw = flat.reshape(shape).copy()
        if count % 100 == 0:
            print(mode, shape[-1] * 2, count, round(time.monotonic() - started, 2), value, summary, flush=True)
            np.savez(prefix + '_checkpoint.npz', A=from_raw(torch.tensor(best_raw))[0].numpy())
        return value, variables.grad.numpy().flatten().copy()

    result = minimize(objective, raw.flatten(), jac=True, method='L-BFGS-B',
                      options={'maxiter': iterations, 'maxls': 40, 'ftol': 1e-15, 'gtol': 1e-10, 'maxcor': 40})
    tensor = from_raw(torch.tensor(best_raw))[0].numpy()
    np.savez(prefix + '.npz', A=tensor)
    print('FINISH', result.message, 'evaluations', count, 'time', time.monotonic() - started, flush=True)
    values = score_metrics(metrics(tensor))
    Path(prefix + '.json').write_text(json.dumps(values, indent=2))
    print({key: value for key, value in values['metrics'].items() if 'correlations' not in key}, flush=True)
    return tensor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input')
    parser.add_argument('--dimensions', default='2,4,8,16,24')
    parser.add_argument('--iterations', type=int, default=1500)
    parser.add_argument('--mode', default='energy')
    parser.add_argument('--prefix', default='energy')
    parser.add_argument('--energy-weight', type=float, default=1.)
    args = parser.parse_args()
    tensor = np.load(args.input)['A'] if args.input else None
    for dimension in map(int, args.dimensions.split(',')):
        if tensor is None:
            raw = np.random.default_rng(1302).normal(size=(2, dimension, dimension // 2))
        elif dimension == tensor.shape[1]:
            raw = to_raw(tensor)
        else:
            raw = grow(tensor, dimension, dimension)
        tensor = run(raw, args.mode, args.iterations, args.prefix + str(dimension), args.energy_weight)


if __name__ == '__main__':
    main()
