import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logsumexp

from landscape import best_sector
from search import Problem, SPINS, optimize, project
from verify import BOUND, LOWER, STATES, PRODUCTS, evaluate


ROOT = Path(__file__).resolve().parent


def fit_distribution(physical_distribution, order, iterations=150):
    physical = SPINS[:, np.argsort(order)]
    indices = ((physical > 0).astype(np.int64) * (1 << np.arange(16))).sum(axis=1)
    distribution = physical_distribution[indices] + physical_distribution[65535 - indices]
    weights = np.zeros((16, 16))
    for row in range(1, 16):
        prefix_count = 1 << (row - 1)
        pair = distribution.reshape(-1, 2, prefix_count).sum(axis=0)
        mass = pair.sum(axis=0)
        active = mass > 1e-17
        design = np.ascontiguousarray(SPINS[:prefix_count, :row][active])
        positive, mass = pair[1, active], mass[active]
        sufficient = positive @ design

        def objective(values):
            coefficients = values[:row] - values[row:]
            logits = design @ coefficients
            value = mass @ np.logaddexp(0, logits) - sufficient @ coefficients
            gradient = design.T @ (mass * expit(logits)) - sufficient
            return value, np.r_[gradient, -gradient]

        result = minimize(objective, np.zeros(2 * row), jac=True, method='SLSQP',
                          bounds=[(0, BOUND)] * (2 * row),
                          constraints=[{'type': 'ineq', 'fun': lambda values: BOUND - 1e-10 - values.sum(),
                                        'jac': lambda values: -np.ones(2 * row)}],
                          options={'maxiter': iterations, 'ftol': 1e-12})
        weights[row, :row] = result.x[:row] - result.x[row:]
    weights[LOWER] = project(weights[LOWER])
    return weights


def trial(seed, base, mode, iterations):
    rng = np.random.default_rng(seed)
    witness = json.loads(json.dumps(base))
    witness['beta'] = 1.
    energy = -PRODUCTS @ witness['bonds']
    core = [0, 1, 2, 3, 8, 9, 10, 11]
    if mode == 'core':
        rng.shuffle(core)
        rest = [site for site in range(16) if site not in core]
        rng.shuffle(rest)
        order = core + rest
        aligned = np.abs(STATES[:, core].sum(axis=1)) == len(core)
        log_distribution = -energy + np.where(aligned, 0, -25)
        distribution = np.exp(log_distribution - logsumexp(log_distribution))
    elif mode == 'reorder':
        order = list(rng.permutation(16))
        result, target, distribution, energy, gradients = evaluate(base, True)
    elif mode == 'backbone':
        core = [site for site in range(16) if site not in (4, 6, 13, 15)]
        rng.shuffle(core)
        order = core + list(rng.permutation([4, 6, 13, 15]))
        result, target, distribution, energy, gradients = evaluate(base, True)
    else:
        raise ValueError(mode)
    witness['order'] = [int(site) for site in order]
    witness['weights'] = fit_distribution(distribution, order).tolist()
    witness, unused = best_sector(witness)
    before = evaluate(witness)
    print('start', seed, mode, before['metrics'], flush=True)
    witness, result = optimize(witness, objective='variance', iterations=iterations,
                               constraints=False, verbosity=0)
    witness, unused = best_sector(witness)
    report = evaluate(witness)
    filename = ROOT / f'trial_{mode}_{seed}.json'
    filename.write_text(json.dumps(witness, indent=2) + '\n')
    print('end', seed, mode, report['core_score'], report['metrics'], flush=True)
    return witness, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'beta1_free_sector.json')
    parser.add_argument('--mode', default='core')
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--count', type=int, default=8)
    parser.add_argument('--iterations', type=int, default=150)
    arguments = parser.parse_args()
    base = json.loads(arguments.input.read_text())
    for seed in range(arguments.start, arguments.start + arguments.count):
        trial(seed, base, arguments.mode, arguments.iterations)


if __name__ == '__main__':
    main()
