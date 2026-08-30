import argparse
import json
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from fast_eval import Evaluator
from model import diagnose


def optimize_probe(item):
    parameters, row, label, seed, size = item
    evaluator = Evaluator(size)
    row = np.array(row)
    parameters = np.array(parameters)
    rng = np.random.default_rng(seed + 321)
    initial = np.zeros(21) if seed == 0 else rng.uniform(-.02, .02, 21)

    def objective(variation):
        perturbed = parameters.copy()
        perturbed[:21] += variation
        values, jacobian = evaluator.compute(perturbed, True)
        return -float(row @ values), -(row @ jacobian)[:21]

    result = minimize(objective, initial, jac=True, method='L-BFGS-B',
                      bounds=[(-.02, .02)] * 21,
                      options={'maxiter': 100, 'ftol': 1e-11, 'gtol': 1e-7, 'maxls': 30})
    variation = np.r_[result.x, np.zeros(4)]
    diagnostic = diagnose(parameters + variation, 73)
    print(label, seed, 'value', -result.fun, 'spread', diagnostic['plateau_spread'],
          'optical', diagnostic['retained_optical_min'], 'mean', diagnostic['plateau_mean'], flush=True)
    return {'label': label, 'seed': seed, 'value': -float(result.fun),
            'variation': variation.tolist(), 'diagnostic': diagnostic}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('output')
    parser.add_argument('--size', type=int, default=33)
    parser.add_argument('--restarts', type=int, default=2)
    parser.add_argument('--all', action='store_true')
    options = parser.parse_args()
    parameters = json.loads(Path(options.source).read_text())['parameters']
    targets = []
    for indices, label in [([2], 'third'), ([3], 'fourth'), ([2, 3], 'sum')]:
        for sign in [-1, 1]:
            row = np.zeros(12)
            row[indices] = sign
            targets.append((row, f'{label}_{sign}'))
    if options.all:
        for index in range(5, 9):
            row = np.zeros(12)
            row[index] = -1
            targets.append((row, f'optical_{index - 4}'))
        for sign in [-1, 1]:
            row = np.zeros(12)
            row[:4] = sign * np.array([1, 1, 2 / 3, 1 / 3])
            targets.append((row, f'mean_{sign}'))
    tasks = [(parameters, row, label, seed, options.size) for row, label in targets
             for seed in range(options.restarts)]
    with Pool(4) as pool:
        results = pool.map(optimize_probe, tasks, chunksize=1)
    Path(options.output).write_text(json.dumps(results, indent=2))
    Path(Path(options.output).stem + '_deltas.json').write_text(
        json.dumps([result['variation'] for result in results]))
