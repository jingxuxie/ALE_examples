import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import time
import numpy as np
from scipy.optimize import least_squares
from search import OUT, assess, witness


def solve(arguments):
    depth, seed, evaluations = arguments
    random = np.random.default_rng(seed)
    lower = max(0.12, 1.45 - 0.118 * (depth - 1) / 5)
    center = random.uniform(max(lower + 0.06, 1.20), 1.40)
    initial = np.clip(center + random.normal(0, 0.055, 6), lower + 0.001, 1.449)
    best = [0, None]
    calls = [0]

    def residual(knots):
        candidate = witness(depth, knots)
        record = assess(candidate)['nominal']
        calls[0] += 1
        if record['margin'] > best[0]:
            best[:] = [record['margin'], candidate]
        estimates = record['estimates']
        return [(estimates[1] - estimates[0]) / 0.008,
                (estimates[2] - estimates[1]) / 0.008,
                max(0, 0.185 - record['error']) / 0.025]

    result = least_squares(residual, initial, bounds=(lower, 1.45),
                           diff_step=0.0001, max_nfev=evaluations,
                           ftol=1e-6, xtol=1e-6, gtol=1e-6)
    candidate = best[1]
    records = assess(candidate, robust=True)
    return dict(witness=candidate, worst_margin=min(row['margin'] for row in records.values()),
                families=records, nominal_best=best[0], evaluations=calls[0], cost=float(result.cost))


def ranking(entry):
    margin = entry['worst_margin']
    if margin >= 1:
        return (1, -entry['witness']['depth'], margin)
    return (0, 0, margin)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--depths', type=int, nargs='+', default=[12, 18, 24, 30])
    parser.add_argument('--restarts', type=int, default=4)
    parser.add_argument('--evaluations', type=int, default=40)
    parser.add_argument('--seed', type=int, default=15119)
    options = parser.parse_args()
    best = json.loads((OUT / 'validation.json').read_text())
    start = time.monotonic()
    cases = [(depth, options.seed + 100 * restart + depth, options.evaluations)
             for restart in range(options.restarts) for depth in options.depths]
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(solve, case) for case in cases]
        for future in as_completed(futures):
            entry = future.result()
            print(json.dumps({key: value for key, value in entry.items() if key != 'families'}), flush=True)
            (OUT / ('short_depth_%s.json' % entry['witness']['depth'])).write_text(json.dumps(entry, indent=2) + '\n')
            if ranking(entry) > ranking(best):
                best = entry
                (OUT / 'validation.json').write_text(json.dumps(best, indent=2) + '\n')
                (OUT / 'witness.json').write_text(json.dumps(best['witness'], indent=2) + '\n')
                print(json.dumps(dict(improvement=True, depth=entry['witness']['depth'],
                                      margin=entry['worst_margin'], seconds=time.monotonic() - start)), flush=True)


if __name__ == '__main__':
    main()
