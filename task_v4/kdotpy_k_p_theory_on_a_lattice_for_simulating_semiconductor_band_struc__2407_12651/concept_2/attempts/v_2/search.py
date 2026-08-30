import json
import time
from pathlib import Path
from multiprocessing import Pool

import numpy as np
from scipy.optimize import least_squares
from model import LOWER, UPPER, diagnose
from fast_eval import Evaluator


def residual_transform(values, optical_target=.018, gap_target=.10):
    rows = []
    offsets = []
    weights = []
    hinges = []
    for index in [2, 3]:
        row = np.zeros(12)
        row[index] = 1
        rows.append(row)
        offsets.append(0)
        weights.append(100)
        hinges.append(False)
    for sign, limit in [(1, .26), (-1, -.395)]:
        row = np.zeros(12)
        row[:4] = sign * np.array([1, 1, 2 / 3, 1 / 3])
        rows.append(row)
        offsets.append(sign * limit if sign == 1 else limit)
        weights.append(20)
        hinges.append(True)
    for index in range(5, 9):
        row = np.zeros(12)
        row[index] = 1
        rows.append(row)
        offsets.append(optical_target)
        weights.append(180)
        hinges.append(True)
    for index, sign, limit, weight in [(10, 1, gap_target, 10), (11, -1, -5.7, 3)]:
        row = np.zeros(12)
        row[index] = sign
        rows.append(row)
        offsets.append(limit)
        weights.append(weight)
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
    derivative = rows * (np.array(weights) * active)[:, None]
    return residual * weights * active, derivative


class Objective:
    def __init__(self, size=25, optical_target=.018, gap_target=.10):
        self.evaluator = Evaluator(size)
        self.optical_target = optical_target
        self.gap_target = gap_target

    def fun(self, parameters):
        values, _ = self.evaluator.compute(parameters, False)
        return residual_transform(values, self.optical_target, self.gap_target)[0]

    def jac(self, parameters):
        values, jacobian = self.evaluator.compute(parameters)
        return residual_transform(values, self.optical_target, self.gap_target)[1] @ jacobian


def search(seed):
    rng = np.random.default_rng(seed + 1000)
    objective = Objective()
    if seed < 60 and Path(f'third_{seed}.json').exists():
        start = np.array(json.loads(Path(f'third_{seed}.json').read_text())['parameters'])
    else:
        for attempt in range(200):
            start = rng.uniform(LOWER, UPPER)
            start[13:21] = rng.uniform(.08, .5, 8)
            values, _ = objective.evaluator.compute(start, False)
            if abs(values[:5].sum() - 1) < .01 and values[10] > .04:
                break
    began = time.time()
    result = least_squares(objective.fun, start, jac=objective.jac, bounds=(LOWER, UPPER),
                           max_nfev=300, ftol=2e-9, xtol=2e-9, gtol=2e-9)
    payload = {'parameters': result.x.tolist(), 'loss': float(np.linalg.norm(result.fun)),
               'diagnostic': diagnose(result.x, 73), 'message': result.message,
               'optimality': result.optimality}
    Path(f'fourth_{seed}.json').write_text(json.dumps(payload, indent=2))
    print(seed, 'seconds', time.time() - began, 'loss', payload['loss'],
          payload['diagnostic'], flush=True)
    return payload


if __name__ == '__main__':
    import sys
    first = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    with Pool(4) as pool:
        pool.map(search, range(first, first + count), chunksize=1)
