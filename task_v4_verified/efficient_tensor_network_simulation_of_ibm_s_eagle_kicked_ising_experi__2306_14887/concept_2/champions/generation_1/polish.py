import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import numpy as np
from scipy.optimize import least_squares
from search import OUT, assess, witness
from shorten import ranking


class Found(Exception):
    pass


def solve(arguments):
    candidate, step, restart, evaluations = arguments
    random = np.random.default_rng(830001 + restart)
    center = np.asarray(candidate['knots'])
    initial = np.clip(center + random.normal(0, 0.0005 * restart, 6), 0.12, 1.45)
    best = [None]
    calls = [0]

    def residual(knots):
        current = witness(candidate['depth'], knots)
        records = assess(current, robust=True)
        margin = min(row['margin'] for row in records.values())
        entry = dict(witness=current, worst_margin=margin, families=records)
        calls[0] += 1
        if best[0] is None or margin > best[0]['worst_margin']:
            best[0] = entry
        if margin >= 1.03:
            raise Found()
        values = []
        for record in records.values():
            estimates = record['estimates']
            values.extend([max(0, abs(estimates[1] - estimates[0]) - 0.0065) / 0.008,
                           max(0, abs(estimates[2] - estimates[1]) - 0.0065) / 0.008,
                           max(0, 0.158 - record['error']) / 0.03])
        return values

    try:
        least_squares(residual, initial,
                      bounds=(np.maximum(0.12, center - 0.025), np.minimum(1.45, center + 0.025)),
                      diff_step=step, max_nfev=evaluations, ftol=1e-7, xtol=1e-7, gtol=1e-7)
    except Found:
        pass
    best[0]['evaluations'] = calls[0]
    best[0]['difference_step'] = step
    return best[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--depth', type=int, default=24)
    parser.add_argument('--evaluations', type=int, default=30)
    options = parser.parse_args()
    entries = json.loads((OUT / 'refine_best.json').read_text())
    entries = [entry for entry in entries if entry['witness']['depth'] == options.depth]
    if not entries:
        raise SystemExit('no suitable anchor')
    candidate = max(entries, key=lambda entry: entry['worst_margin'])['witness']
    best = json.loads((OUT / 'validation.json').read_text())
    arguments = [(candidate, step, restart, options.evaluations)
                 for restart, step in enumerate([0.0001, 0.0005, 0.001, 0.002])]
    with ProcessPoolExecutor(max_workers=4) as pool:
        for entry in pool.map(solve, arguments):
            print(json.dumps({key: value for key, value in entry.items() if key != 'families'}), flush=True)
            (OUT / ('polish_%s.json' % entry['difference_step'])).write_text(json.dumps(entry, indent=2) + '\n')
            if ranking(entry) > ranking(best):
                best = entry
                (OUT / 'validation.json').write_text(json.dumps(best, indent=2) + '\n')
                (OUT / 'witness.json').write_text(json.dumps(best['witness'], indent=2) + '\n')


if __name__ == '__main__':
    main()
