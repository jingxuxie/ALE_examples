import argparse
import json
import time
from pathlib import Path
import sys
import numpy as np
from scipy.linalg import cholesky, solve, solve_triangular
from scipy.optimize import minimize


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
from physics import laplacian, score


def fit(catalogue, seed, seconds, strategy='degree'):
    start = time.monotonic()
    generator = np.random.default_rng(seed)
    source = catalogue['source']
    target = catalogue['target']
    state_count = len(catalogue['velocities'])
    edge_count = len(source)
    weights = catalogue['channels'] @ catalogue['mixing'].T
    degree = np.zeros((state_count, weights.shape[1]))
    np.add.at(degree, source, weights)
    np.add.at(degree, target, weights)
    importance = np.mean(weights * (1 / degree[source] + 1 / degree[target]), axis=1)
    if strategy == 'probe':
        differences = catalogue['probes'][source] - catalogue['probes'][target]
        energies = weights.T @ (differences ** 2)
        sensitivity = np.mean(weights[:, :, None] * differences[:, None, :] ** 2 / energies[None, :, :], axis=(1, 2))
        importance = 0.35 * importance / importance.sum() + 0.65 * sensitivity / sensitivity.sum()
    if strategy == 'leverage':
        sensitivity = np.zeros(edge_count)
        for temperature in range(weights.shape[1]):
            matrix = laplacian(state_count, source, target, weights[:, temperature])
            inverse = solve(matrix + np.ones_like(matrix) / state_count, np.eye(state_count), assume_a='pos')
            resistance = np.diag(inverse)[source] + np.diag(inverse)[target] - 2 * inverse[source, target]
            sensitivity += weights[:, temperature] * resistance
        importance = 0.2 * importance / importance.sum() + 0.8 * sensitivity / sensitivity.sum()
    indices = generator.choice(edge_count, int(catalogue['budget']), p=importance / importance.sum(), replace=False)
    selected_source = source[indices]
    selected_target = target[indices]
    selected_weights = weights[indices]
    drives = catalogue['velocities']
    probes = catalogue['probes']
    probe_difference = probes[source] - probes[target]
    dissipation = weights.T @ (probe_difference ** 2)
    selected_difference = probe_difference[indices]
    frames = []
    for temperature in range(weights.shape[1]):
        original = laplacian(state_count, source, target, weights[:, temperature])
        response = solve(original + np.ones_like(original) / state_count, drives, assume_a='pos')
        conductivity = drives.T @ response
        root = cholesky(conductivity, lower=True)
        whitened = solve_triangular(root, drives.T, lower=True).T
        frames.append(whitened)
    best = [float('inf'), None, 0]

    def objective(factors):
        if time.monotonic() - start > seconds:
            raise TimeoutError
        loss = 0.0
        gradient = np.zeros_like(factors)
        for temperature, frame in enumerate(frames):
            selected = selected_weights[:, temperature]
            active = selected * factors
            matrix = laplacian(state_count, selected_source, selected_target, active)
            degrees = np.diag(matrix)
            residual_degree = degrees / degree[:, temperature] - 1
            loss += 12 * np.mean(residual_degree ** 2)
            scaled = 24 * residual_degree / degree[:, temperature] / state_count
            gradient += selected * (scaled[selected_source] + scaled[selected_target])
            residual_probe = active @ (selected_difference ** 2) / dissipation[temperature] - 1
            loss += 2 * np.mean(residual_probe ** 2)
            gradient += 4 * selected * ((selected_difference ** 2) @ (residual_probe / dissipation[temperature])) / len(residual_probe)
            response = solve(matrix + np.ones_like(matrix) / state_count, frame, assume_a='pos')
            residual_tensor = frame.T @ response - np.eye(3)
            loss += 5 * np.sum(residual_tensor ** 2)
            response_difference = response[selected_source] - response[selected_target]
            gradient -= 10 * selected * np.einsum('ei,ij,ej->e', response_difference, residual_tensor, response_difference)
        if loss < best[0]:
            best[:] = [loss, factors.copy(), best[2] + 1]
        return loss, gradient

    initial = np.full(len(indices), edge_count / len(indices))
    try:
        minimize(objective, initial, jac=True, bounds=[(1e-5, 500)] * len(initial),
                 method='L-BFGS-B', options={'maxiter': 15000, 'ftol': 1e-15, 'gtol': 1e-9, 'maxcor': 30})
    except TimeoutError:
        pass
    if best[1] is None:
        raise RuntimeError('no optimization step completed')
    return indices, best[1], {'objective': best[0], 'improvements': best[2], 'seconds': time.monotonic() - start, 'strategy': strategy}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=300)
    parser.add_argument('--seed', type=int, default=43)
    parser.add_argument('--strategy', choices=['degree', 'probe', 'leverage'], default='degree')
    args = parser.parse_args()
    with np.load(args.input, allow_pickle=False) as archive:
        catalogue = dict(archive)
    indices, multipliers, metadata = fit(catalogue, args.seed, args.seconds, args.strategy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.output, indices=indices, multipliers=multipliers)
    metadata.update(score(catalogue, indices, multipliers))
    args.output.with_suffix('.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps(metadata), flush=True)


if __name__ == '__main__':
    main()
