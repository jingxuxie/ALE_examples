import argparse
import ctypes
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

from verify import BOUND, EDGES, LOWER, evaluate, frustrated


ROOT = Path(__file__).resolve().parent
LIBRARY = ctypes.CDLL(str(ROOT / 'fast.so'))
POINTER = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
LIBRARY.evaluate_fast.argtypes = [POINTER] * 5
LIBRARY.hessian_fast.argtypes = [POINTER] * 2
SPINS = np.column_stack((np.ones(32768), 2 * ((np.arange(32768)[:, None] >> np.arange(15)) & 1) - 1))
ROWS = np.zeros((15, 120))
for row in range(1, 16):
    ROWS[row - 1, row * (row - 1) // 2:row * (row + 1) // 2] = 1


def project(weights, bound=BOUND - 1e-12):
    weights = np.array(weights, dtype=float).copy()
    for row in range(1, 16):
        start, stop = row * (row - 1) // 2, row * (row + 1) // 2
        values = weights[start:stop]
        if np.abs(values).sum() > bound:
            ordered = np.sort(np.abs(values))[::-1]
            cumulative = np.cumsum(ordered) - bound
            active = np.nonzero(ordered - cumulative / np.arange(1, row + 1) > 0)[0][-1]
            threshold = cumulative[active] / (active + 1)
            weights[start:stop] = np.sign(values) * np.maximum(np.abs(values) - threshold, 0)
    return weights


class Problem:
    def __init__(self, witness):
        self.witness = json.loads(json.dumps(witness))
        self.physical = SPINS[:, np.argsort(witness['order'])]
        self.products = self.physical[:, EDGES[:, 0]] * self.physical[:, EDGES[:, 1]]
        self.energy = np.ascontiguousarray(-self.products @ witness['bonds'])
        self.potential = np.ascontiguousarray(witness['beta'] * self.energy)
        distance = np.count_nonzero(self.physical != witness['pattern'], axis=1)
        self.sector = (np.minimum(distance, 16 - distance) <= witness['radius']).astype(float)
        self.log_partition = logsumexp(-self.potential) + np.log(2)
        self.target = np.exp(-self.potential - logsumexp(-self.potential))
        self.target_energy = self.target @ self.potential
        self.target_sector = self.target @ self.sector
        self.last_weights = None
        self.calls = 0
        self.started = time.time()

    def calculate(self, weights):
        if self.last_weights is not None and np.array_equal(weights, self.last_weights):
            return self.metrics, self.derivatives
        metrics = np.empty(5)
        derivatives = np.empty((5, 120))
        LIBRARY.evaluate_fast(np.ascontiguousarray(weights), self.potential, self.sector, metrics, derivatives)
        metrics[0] += self.log_partition
        self.last_weights = weights.copy()
        self.metrics, self.derivatives = metrics, derivatives
        self.calls += 1
        return metrics, derivatives

    def pack(self, weights):
        witness = json.loads(json.dumps(self.witness))
        matrix = np.zeros((16, 16))
        matrix[LOWER] = project(weights)
        witness['weights'] = matrix.tolist()
        return witness

    def hessian_vector(self, direction):
        result = np.empty(120)
        LIBRARY.hessian_fast(np.ascontiguousarray(direction), result)
        return result


def optimize(witness, objective='variance', iterations=300, constraints=True, verbosity=1, sector_limit=.001, entropy_min=3., split=True):
    problem = Problem(witness)
    initial = project(np.array(witness['weights'])[LOWER])
    if split:
        initial = np.r_[np.maximum(initial, 0), np.maximum(-initial, 0)]
        matrix = np.c_[ROWS, ROWS]
        unpack = lambda values: values[:120] - values[120:]
        chain = lambda values: np.concatenate((values, -values), axis=-1)
        bounds = [(0, BOUND)] * 240
        row_fun = lambda values: BOUND - 1e-10 - matrix @ values
        row_jac = lambda values: -matrix
    else:
        unpack = lambda values: values
        chain = lambda values: values
        bounds = [(-BOUND, BOUND)] * 120
        row_fun = lambda values: BOUND - 1e-10 - ROWS @ np.abs(values)
        row_jac = lambda values: -ROWS * np.sign(values)
    constraints_list = [{'type': 'ineq', 'fun': row_fun, 'jac': row_jac}]
    if constraints:
        def other_fun(values):
            metrics, derivatives = problem.calculate(unpack(values))
            return np.array([(sector_limit - metrics[4]) * 100,
                             metrics[3] - entropy_min, metrics[0] - .4,
                             .32 - (metrics[2] - problem.target_energy),
                             .32 + (metrics[2] - problem.target_energy)])

        def other_jac(values):
            metrics, derivatives = problem.calculate(unpack(values))
            return chain(np.array([-100 * derivatives[4], derivatives[3], derivatives[0],
                                   -derivatives[2], derivatives[2]]))
        constraints_list.append({'type': 'ineq', 'fun': other_fun, 'jac': other_jac})

    def function(values):
        metrics, derivatives = problem.calculate(unpack(values))
        if objective == 'variance':
            return metrics[1], chain(derivatives[1])
        if objective == 'kl':
            return metrics[0], chain(derivatives[0])
        if objective == 'mixed':
            return metrics[1] + .2 * metrics[0], chain(derivatives[1] + .2 * derivatives[0])
        if objective in ('minimax', 'gradvar'):
            gradient = derivatives[0]
            temperature = .00015
            soft_gradient = temperature * logsumexp(np.abs(gradient) / temperature)
            direction = np.sign(gradient) * np.exp((np.abs(gradient) - soft_gradient) / temperature)
            gradient_derivative = problem.hessian_vector(direction)
            if objective == 'gradvar':
                return metrics[1] + 15 * soft_gradient, chain(derivatives[1] + 15 * gradient_derivative)
            ratios = np.array([metrics[1] / .05, soft_gradient / .003,
                               metrics[4] / .001, abs(metrics[2] - problem.target_energy) / .32,
                               3 / metrics[3], .4 / max(metrics[0], 1e-10)])
            ratio_derivatives = np.array([derivatives[1] / .05, gradient_derivative / .003,
                                          derivatives[4] / .001,
                                          np.sign(metrics[2] - problem.target_energy) * derivatives[2] / .32,
                                          -3 * derivatives[3] / metrics[3] ** 2,
                                          -.4 * derivatives[0] / max(metrics[0], 1e-10) ** 2])
            value = .03 * logsumexp(ratios / .03)
            probabilities = np.exp((ratios - value) / .03)
            return value, chain(probabilities @ ratio_derivatives)
        raise ValueError(objective)

    steps = 0
    def callback(values):
        nonlocal steps
        steps += 1
        if verbosity and steps % 25 == 0:
            metrics, derivatives = problem.calculate(unpack(values))
            print(steps, 'calls', problem.calls, 'seconds', round(time.time() - problem.started, 1),
                  'metrics', np.round(metrics, 7), 'gmax', np.max(np.abs(derivatives[0])), flush=True)

    result = minimize(function, initial, method='SLSQP', jac=True, bounds=bounds,
                      constraints=constraints_list, callback=callback,
                      options={'maxiter': iterations, 'ftol': 1e-11, 'disp': bool(verbosity)})
    return problem.pack(unpack(result.x)), result


def test(witness):
    problem = Problem(witness)
    weights = np.array(witness['weights'])[LOWER].copy()
    started = time.time()
    metrics, derivatives = problem.calculate(weights)
    print('fast', metrics, 'gmax', np.max(np.abs(derivatives[0])), 'seconds', time.time() - started)
    reference = evaluate(witness)
    print('reference', json.dumps(reference, indent=2))
    for coordinate in (0, 6, 58, 100):
        upper, lower = weights.copy(), weights.copy()
        upper[coordinate] += 1e-5
        lower[coordinate] -= 1e-5
        numerical = (problem.calculate(upper)[0] - problem.calculate(lower)[0]) / 2e-5
        print(coordinate, 'max derivative error', np.max(np.abs(numerical - derivatives[:, coordinate])))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=ROOT / 'witness.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'optimized.json')
    parser.add_argument('--beta', type=float)
    parser.add_argument('--iterations', type=int, default=300)
    parser.add_argument('--objective', choices=['variance', 'kl', 'mixed', 'minimax', 'gradvar'], default='variance')
    parser.add_argument('--unconstrained', action='store_true')
    parser.add_argument('--nosplit', action='store_true')
    parser.add_argument('--test', action='store_true')
    arguments = parser.parse_args()
    witness = json.loads(arguments.input.read_text())
    if arguments.beta:
        witness['beta'] = arguments.beta
    if arguments.test:
        test(witness)
        return
    witness, result = optimize(witness, arguments.objective, arguments.iterations,
                               not arguments.unconstrained, split=not arguments.nosplit)
    arguments.output.write_text(json.dumps(witness, indent=2) + '\n')
    print(json.dumps(evaluate(witness), indent=2), flush=True)


if __name__ == '__main__':
    main()
