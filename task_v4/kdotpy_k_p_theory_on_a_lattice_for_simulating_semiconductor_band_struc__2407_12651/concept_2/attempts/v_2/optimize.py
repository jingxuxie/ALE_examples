import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from model import LOWER, UPPER, diagnose


BASE = np.array([-1., 1., 1., 1., 1., -.3, -.1, .1, .3,
                 .05, -.05, .05, -.05, .16, .16, .16, .16,
                 .16, .16, .16, .16, .2, 1.1, -1.4, 2.2])


def residual(parameters, size=25):
    result = diagnose(parameters, size)
    gap49 = (result['sampled_gap'] -
             (result['sampled_gap'] - result['gap_lower_bound']) * size / 49)
    return np.r_[
        np.array(result['contributions'][2:4]) * 100,
        (result['plateau_mean'] - .33) * 20,
        np.minimum(np.array(result['optical'][:4]) - .018, 0) * 100,
        min(gap49 - .13, 0) * 10,
        min(5.7 - result['norm_upper_bound'], 0) * 3,
        (result['full'] - 1) * 10,
    ]


def search(seed):
    rng = np.random.default_rng(seed)
    start = BASE.copy()
    if seed < 8 and Path(f'candidate_{seed}.json').exists():
        start = np.array(json.loads(Path(f'candidate_{seed}.json').read_text())['parameters'])
    elif seed:
        start[:5] += rng.normal(0, .1, 5)
        start[5:13] += rng.normal(0, .06, 8)
        start[13:21] = rng.uniform(.12, .38, 8)
        start[21:] = rng.uniform(-np.pi, np.pi, 4)
    start = np.clip(start, LOWER + 1e-5, UPPER - 1e-5)
    began = time.time()
    result = least_squares(residual, start, bounds=(LOWER, UPPER),
                           max_nfev=200, ftol=1e-8, xtol=1e-8, gtol=1e-8)
    payload = {'parameters': result.x.tolist(), 'loss': float(np.linalg.norm(result.fun)),
               'diagnostic': diagnose(result.x, 73)}
    Path(f'second_{seed}.json').write_text(json.dumps(payload, indent=2))
    print(seed, 'seconds', time.time() - began, 'loss', payload['loss'],
          payload['diagnostic'], flush=True)
    return payload


if __name__ == '__main__':
    import sys
    from multiprocessing import Pool
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    with Pool(4) as pool:
        pool.map(search, range(count))
