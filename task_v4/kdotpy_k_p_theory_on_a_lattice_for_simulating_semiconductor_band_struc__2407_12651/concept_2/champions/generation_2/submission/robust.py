import argparse
import json
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from model import LOWER, UPPER, diagnose
from fast_eval import Evaluator
from audit import perturbations


EVALUATORS = {}


def evaluate(item):
    parameters, size = item
    if size not in EVALUATORS:
        EVALUATORS[size] = Evaluator(size)
    return EVALUATORS[size].compute(parameters, True)


class RobustObjective:
    def __init__(self, pool, variations, size=25, optical=.017, spread=.004, checkpoint=None):
        self.pool = pool
        self.variations = variations
        self.size = size
        self.optical = optical
        self.spread = spread
        self.last_parameters = None
        self.iterations = 0
        self.began = time.time()
        self.checkpoint = checkpoint
        self.best_loss = np.inf

    def compute(self, parameters):
        if self.last_parameters is not None and np.array_equal(parameters, self.last_parameters):
            return self.last_residual, self.last_jacobian
        results = self.pool.map(evaluate, [(parameters + variation, self.size)
                                          for variation in self.variations])
        residuals = []
        jacobians = []
        for index, (values, jacobian) in enumerate(results):
            rows = []
            offsets = []
            weights = []
            hinges = []
            for selected in [[2], [3], [2, 3]]:
                row = np.zeros(12)
                row[selected] = 1
                rows.extend([row, row, -row])
                limit = .003 if index == 0 else self.spread
                offsets.extend([0, -limit, -limit])
                weights.extend([5 if index == 0 else 0, 200, 200])
                hinges.extend([False, True, True])
            for sign, limit in [(1, .22), (-1, -.405 if index == 0 else -.415)]:
                row = np.zeros(12)
                row[:4] = sign * np.array([1, 1, 2 / 3, 1 / 3])
                rows.append(row)
                offsets.append(limit)
                weights.append(50)
                hinges.append(True)
            for selected in range(5, 9):
                row = np.zeros(12)
                row[selected] = 1
                rows.append(row)
                offsets.append(self.optical if index == 0 else self.optical - .001)
                weights.append(180)
                hinges.append(True)
            row = np.zeros(12)
            row[10] = 1
            rows.append(row)
            offsets.append(.115 if index == 0 else .07)
            weights.append(150 if index == 0 else 5)
            hinges.append(True)
            row = np.zeros(12)
            row[:5] = 1
            rows.append(row)
            offsets.append(1)
            weights.append(10)
            hinges.append(False)
            rows = np.array(rows)
            residual = rows @ values - offsets
            active = np.logical_or(np.logical_not(hinges), residual < 0)
            multiplier = np.array(weights) * active / np.sqrt(len(results))
            residuals.append(residual * multiplier)
            jacobians.append((rows * multiplier[:, None]) @ jacobian)
        self.last_parameters = parameters.copy()
        self.last_residual = np.concatenate(residuals)
        self.last_jacobian = np.concatenate(jacobians)
        self.iterations += 1
        loss = np.linalg.norm(self.last_residual)
        if self.checkpoint and loss < self.best_loss:
            self.best_loss = loss
            wrapped = parameters.copy()
            wrapped[21:] = (wrapped[21:] + np.pi) % (2 * np.pi) - np.pi
            Path(self.checkpoint).write_text(json.dumps({'parameters': wrapped.tolist(), 'loss': loss}))
        if self.iterations % 5 == 1:
            print('iteration', self.iterations, 'seconds', time.time() - self.began,
                  'loss', np.linalg.norm(self.last_residual), 'nominal', results[0][0].tolist(), flush=True)
            print('training extremes', 'spread', max(max(abs(item[0][2]), abs(item[0][3]),
                  abs(item[0][2] + item[0][3])) for item in results), 'optical',
                  min(item[0][5:9].min() for item in results), 'mean',
                  max(item[0][0] + item[0][1] + 2 * item[0][2] / 3 + item[0][3] / 3
                      for item in results), flush=True)
        return self.last_residual, self.last_jacobian

    def fun(self, parameters):
        return self.compute(parameters)[0]

    def jac(self, parameters):
        return self.compute(parameters)[1]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('output')
    parser.add_argument('--count', type=int, default=8)
    parser.add_argument('--size', type=int, default=25)
    parser.add_argument('--iterations', type=int, default=100)
    parser.add_argument('--optical', type=float, default=.017)
    parser.add_argument('--spread', type=float, default=.004)
    parser.add_argument('--extra')
    options = parser.parse_args()
    start = np.array(json.loads(Path(options.source).read_text())['parameters'])
    variations = np.r_[np.zeros((1, 25)), perturbations(options.count, 1719)]
    if options.extra:
        variations = np.r_[variations, np.array(json.loads(Path(options.extra).read_text()))]
    with Pool(4) as pool:
        objective = RobustObjective(pool, variations, options.size, options.optical, options.spread,
                                    Path(options.output).stem + '_checkpoint.json')
        lower = np.r_[LOWER[:21], np.full(4, -10 * np.pi)]
        upper = np.r_[UPPER[:21], np.full(4, 10 * np.pi)]
        result = least_squares(objective.fun, start, jac=objective.jac, bounds=(lower, upper),
                               max_nfev=options.iterations, ftol=1e-8, xtol=1e-8, gtol=1e-8)
    result.x[21:] = (result.x[21:] + np.pi) % (2 * np.pi) - np.pi
    payload = {'parameters': result.x.tolist(), 'loss': float(np.linalg.norm(result.fun)),
               'diagnostic': diagnose(result.x, 73)}
    Path(options.output).write_text(json.dumps(payload, indent=2))
    print(payload, flush=True)
