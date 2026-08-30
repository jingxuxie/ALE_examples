import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import argparse
import json
import multiprocessing as mp
from pathlib import Path
import sys
import time

import numpy as np
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parent
PARTICIPANT = ROOT.parent.parent / 'participant'
sys.path.insert(0, str(PARTICIPANT / 'workspace'))
from model import LOWER, UPPER, diagnose


def residual(parameters, size=25):
    result = diagnose(parameters, size)
    integrals = np.array(result['contributions'])
    sign = 1.0
    return np.r_[
        integrals[2:4] * 3,
        (result['plateau_mean'] - sign * .30),
        np.maximum(.0175 - np.array(result['optical'][:4]), 0) * 8,
        max(.16 - result['sampled_gap'] +
            (result['sampled_gap'] - result['gap_lower_bound']) * size / 49, 0) * .7,
        max(result['norm_upper_bound'] - 5.7, 0) * .4,
        (result['full'] - sign) * .6,
    ]


def worker(seed):
    random = np.random.default_rng(seed)
    started = time.monotonic()
    baseline = json.loads((PARTICIPANT / 'baseline/witness.json').read_text())['parameters']
    parameters = np.array(baseline)
    parameters[:5] += random.normal(0, .10, 5)
    parameters[5:9] = np.sort(random.uniform(-.4, .4, 4))
    parameters[9:13] = random.uniform(-.12, .12, 4)
    parameters[13:21] = random.uniform(.22, .48, 8)
    parameters[21:] = random.uniform(-np.pi, np.pi, 4)
    parameters = np.clip(parameters, LOWER + 1e-6, UPPER - 1e-6)
    initial = diagnose(parameters, 25)
    print(json.dumps({'seed': seed, 'initial': initial}), flush=True)
    solution = least_squares(residual, parameters, bounds=(LOWER, UPPER),
                             max_nfev=350, ftol=1e-10, xtol=1e-10, gtol=1e-8)
    final = diagnose(solution.x, 49)
    payload = {'parameters': solution.x.tolist(), 'diagnostic': final,
               'cost': float(solution.cost), 'nfev': int(solution.nfev),
               'seed': seed, 'elapsed': time.monotonic() - started}
    (ROOT / f'candidate_{seed}.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload), flush=True)
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=int, default=1)
    parser.add_argument('--count', type=int, default=4)
    options = parser.parse_args()
    with mp.Pool(min(4, options.count)) as pool:
        results = pool.map(worker, range(options.start, options.start + options.count))
    print('DONE', flush=True)
