import argparse
import json
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from model import LOWER, UPPER, diagnose
from audit import perturbations
from robust import evaluate
from spectral import SpectralEvaluator


class Constraints:
    def __init__(self, pool, variations, size, output, internal_gap=0., local=False):
        self.pool = pool
        self.variations = variations
        self.size = size
        self.output = output
        self.last_parameters = None
        self.best_violation = np.inf
        self.iterations = 0
        self.began = time.time()
        self.internal_gap = internal_gap
        self.spectral = SpectralEvaluator()
        self.local = local

    def compute(self, parameters):
        if self.last_parameters is not None and np.array_equal(parameters, self.last_parameters):
            return self.last_values, self.last_jacobian
        results = self.pool.map(evaluate, [(parameters + delta, self.size) for delta in self.variations])
        values_all = []
        derivatives_all = []
        for index, (values, jacobian) in enumerate(results):
            rows = []
            offsets = []
            weights = []
            corner = np.count_nonzero(np.abs(self.variations[index][:21]) > .0199) > 10
            for indices in [[2], [3], [2, 3]]:
                for sign in [-1, 1]:
                    row = np.zeros(12)
                    row[indices] = sign
                    rows.append(row)
                    limit = .004 if index == 0 else .0075
                    if self.local:
                        limit = .003 if index == 0 else (.012 if corner else .0068)
                    offsets.append(-limit)
                    weights.append(200)
            mean_limit = .405 if index == 0 else (.45 if corner else .418)
            if self.local and index == 0:
                mean_limit = .39
            for sign, limit in [(1, .20), (-1, -mean_limit)]:
                row = np.zeros(12)
                row[:4] = sign * np.array([1, 1, 2 / 3, 1 / 3])
                rows.append(row)
                offsets.append(limit)
                weights.append(100 if self.local and index == 0 else 10)
            for optical in range(5, 9):
                row = np.zeros(12)
                row[optical] = 1
                rows.append(row)
                offsets.append((.0164 if index == 0 else .0152) if self.local
                               else (.0158 if index == 0 else .0151))
                weights.append(500)
            row = np.zeros(12)
            row[10] = 1
            rows.append(row)
            offsets.append(.11 if index == 0 else .05)
            weights.append(100 if index == 0 else 10)
            for sign in [-1, 1]:
                row = np.zeros(12)
                row[:5] = sign
                rows.append(row)
                offsets.append(sign - .0005)
                weights.append(10)
            rows = np.array(rows)
            values_all.append((rows @ values - offsets) * weights)
            derivatives_all.append((rows * np.array(weights)[:, None]) @ jacobian)
        if self.internal_gap:
            values, jacobian = self.spectral.compute(parameters)
            values_all.append((values - self.internal_gap) * 20)
            derivatives_all.append(jacobian * 20)
        self.last_parameters = parameters.copy()
        self.last_values = np.concatenate(values_all)
        self.last_jacobian = np.concatenate(derivatives_all)
        self.iterations += 1
        violation = -self.last_values.min()
        if violation < self.best_violation:
            self.best_violation = violation
            wrapped = parameters.copy()
            wrapped[21:] = (wrapped[21:] + np.pi) % (2 * np.pi) - np.pi
            Path(self.output).write_text(json.dumps({'parameters': wrapped.tolist(),
                                                     'violation': float(violation)}, indent=2))
        print('evaluation', self.iterations, 'seconds', time.time() - self.began,
              'violation', violation, 'best', self.best_violation, flush=True)
        return self.last_values, self.last_jacobian

    def fun(self, variables):
        return self.compute(variables[:25])[0] + variables[-1]

    def jac(self, variables):
        jacobian = self.compute(variables[:25])[1]
        return np.c_[jacobian, np.ones(len(jacobian))]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('output')
    parser.add_argument('--extra', required=True)
    parser.add_argument('--size', type=int, default=25)
    parser.add_argument('--iterations', type=int, default=100)
    parser.add_argument('--internal-gap', type=float, default=0.)
    parser.add_argument('--local', action='store_true')
    options = parser.parse_args()
    start = np.array(json.loads(Path(options.source).read_text())['parameters'])
    variations = np.r_[np.zeros((1, 25)), perturbations(8, 1719),
                       np.array(json.loads(Path(options.extra).read_text()))]
    with Pool(4) as pool:
        constraints = Constraints(pool, variations, options.size,
                                  Path(options.output).stem + '_checkpoint.json', options.internal_gap,
                                  options.local)
        initial_slack = max(0, -constraints.compute(start)[0].min()) + .001
        lower = np.r_[LOWER[:21], np.full(4, -10 * np.pi), 0]
        upper = np.r_[UPPER[:21], np.full(4, 10 * np.pi), 100]
        if options.local:
            lower[:21] = np.maximum(lower[:21], start[:21] - .04)
            upper[:21] = np.minimum(upper[:21], start[:21] + .04)
            lower[21:25] = start[21:] - .3
            upper[21:25] = start[21:] + .3

        def objective(variables):
            displacement = variables[:25] - start
            return (variables[-1] + .0001 * (displacement @ displacement),
                    np.r_[.0002 * displacement, 1])

        result = minimize(objective, np.r_[start, initial_slack], jac=True, method='SLSQP',
                          bounds=list(zip(lower, upper)),
                          constraints={'type': 'ineq', 'fun': constraints.fun, 'jac': constraints.jac},
                          options={'maxiter': options.iterations, 'ftol': 1e-9, 'disp': True})
    parameters = result.x[:25]
    parameters[21:] = (parameters[21:] + np.pi) % (2 * np.pi) - np.pi
    payload = {'parameters': parameters.tolist(), 'slack': float(result.x[-1]),
               'diagnostic': diagnose(parameters, 73), 'message': result.message}
    Path(options.output).write_text(json.dumps(payload, indent=2))
    print(payload, flush=True)
