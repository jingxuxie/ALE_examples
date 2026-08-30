import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from landscape import best_sector
from search import Problem, ROWS, SPINS, project
from verify import BOUND, LOWER, evaluate


ROOT = Path(__file__).resolve().parent


def hessian(problem, weights):
    matrix = np.zeros((16, 16))
    matrix[LOWER] = weights
    logits = SPINS @ matrix.T
    conditional = expit(logits)
    log_proposal = -np.logaddexp(0, -SPINS * logits).sum(axis=1)
    proposal = 2 * np.exp(log_proposal)
    reward = problem.potential + log_proposal
    centered = reward - proposal @ reward
    residual = (SPINS + 1) / 2 - conditional
    scores = residual[:, LOWER[0]] * SPINS[:, LOWER[1]]
    result = scores.T @ (scores * (proposal * (centered + 1))[:, None])
    for row in range(1, 16):
        start, stop = row * (row - 1) // 2, row * (row + 1) // 2
        prefix = SPINS[:, :row]
        factors = proposal * centered * conditional[:, row] * (1 - conditional[:, row])
        result[start:stop, start:stop] -= prefix.T @ (prefix * factors[:, None])
    return result


def refine(witness, iterations=250, verbose=True):
    problem = Problem(witness)
    weights = project(np.array(witness['weights'])[LOWER])
    metrics, derivatives = problem.calculate(weights)
    initial_t = max(metrics[1] / .05, np.max(np.abs(derivatives[0])) / .003,
                    3 / metrics[3], .4 / metrics[0], metrics[4] / .001,
                    abs(metrics[2] - problem.target_energy) / .32, .35 / problem.target_sector)
    initial = np.r_[np.maximum(weights, 0), np.maximum(-weights, 0), initial_t + 1e-6]
    row_matrix = np.c_[ROWS, ROWS, np.zeros(15)]
    last_hessian = None
    last_weights = None
    started = time.time()
    steps = 0

    def unpack(values):
        return values[:120] - values[120:240]

    def function(values):
        gradient = np.zeros(241)
        gradient[-1] = 1
        return values[-1], gradient

    def constraints(values):
        metrics, derivatives = problem.calculate(unpack(values))
        scale = values[-1]
        return np.r_[(.05 * scale - metrics[1]) * 10,
                     (.003 * scale - derivatives[0]) * 100,
                     (.003 * scale + derivatives[0]) * 100,
                     scale * metrics[3] - 3,
                     scale * metrics[0] - .4,
                     .32 * scale - metrics[2] + problem.target_energy,
                     .32 * scale + metrics[2] - problem.target_energy,
                     (.001 * scale - metrics[4]) * 100,
                     scale * problem.target_sector - .35]

    def jacobian(values):
        nonlocal last_weights, last_hessian
        weights = unpack(values)
        metrics, derivatives = problem.calculate(weights)
        scale = values[-1]
        if last_weights is None or not np.array_equal(weights, last_weights):
            last_hessian = hessian(problem, weights)
            last_weights = weights.copy()
        weight_jacobian = np.vstack([-10 * derivatives[1], -100 * last_hessian,
                                     100 * last_hessian, scale * derivatives[3],
                                     scale * derivatives[0], -derivatives[2], derivatives[2],
                                     -100 * derivatives[4], np.zeros(120)])
        scale_jacobian = np.r_[.5, np.full(240, .3), metrics[3], metrics[0], .32, .32, .1, problem.target_sector]
        return np.c_[weight_jacobian, -weight_jacobian, scale_jacobian]

    def callback(values):
        nonlocal steps
        steps += 1
        if verbose and steps % 20 == 0:
            metrics, derivatives = problem.calculate(unpack(values))
            print('step', steps, 'seconds', round(time.time() - started), 'scale', values[-1],
                  'metrics', metrics, 'gradient', np.max(np.abs(derivatives[0])), flush=True)

    result = minimize(function, initial, jac=True, method='SLSQP',
                      bounds=[(0, BOUND)] * 240 + [(.01, max(100., initial_t * 2))],
                      constraints=[{'type': 'ineq', 'fun': lambda values: BOUND - 1e-10 - row_matrix @ values,
                                    'jac': lambda values: -row_matrix},
                                   {'type': 'ineq', 'fun': constraints, 'jac': jacobian}],
                      callback=callback, options={'maxiter': iterations, 'ftol': 1e-11, 'disp': verbose})
    return problem.pack(unpack(result.x)), result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'witness.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'refined.json')
    parser.add_argument('--iterations', type=int, default=250)
    parser.add_argument('--cycles', type=int, default=2)
    parser.add_argument('--test', action='store_true')
    arguments = parser.parse_args()
    witness = json.loads(arguments.input.read_text())
    if arguments.test:
        problem = Problem(witness)
        weights = np.array(witness['weights'])[LOWER]
        problem.calculate(weights)
        direction = np.random.default_rng(9).normal(size=120)
        started = time.time()
        matrix = hessian(problem, weights)
        print('hessian seconds', time.time() - started, 'action error',
              np.max(np.abs(matrix @ direction - problem.hessian_vector(direction))),
              'symmetry error', np.max(np.abs(matrix - matrix.T)))
        return
    for cycle in range(arguments.cycles):
        witness, sector = best_sector(witness)
        witness, result = refine(witness, arguments.iterations)
        witness, sector = best_sector(witness)
        arguments.output.write_text(json.dumps(witness, indent=2) + '\n')
        print('cycle', cycle, json.dumps(evaluate(witness)), flush=True)


if __name__ == '__main__':
    main()
