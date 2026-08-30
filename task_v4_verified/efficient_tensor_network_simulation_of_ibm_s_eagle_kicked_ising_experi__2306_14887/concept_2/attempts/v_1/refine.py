import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import time
import numpy as np
from search import OUT, assess, witness
from shorten import ranking


def evaluate(candidate):
    records = assess(candidate)
    if records['nominal']['margin'] > 0.98:
        records = assess(candidate, robust=True)
    return candidate, records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trials', type=int, default=500)
    parser.add_argument('--seed', type=int, default=230614887)
    parser.add_argument('--depth', type=int, default=0)
    parser.add_argument('--center', type=float, default=1.34)
    parser.add_argument('--knots', type=float, nargs=6)
    parser.add_argument('--scale', type=float)
    options = parser.parse_args()
    random = np.random.default_rng(options.seed)
    start = time.monotonic()
    best = json.loads((OUT / 'validation.json').read_text())
    previous_path = OUT / 'refine_best.json'
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else []
    best = max([best] + previous, key=ranking)
    (OUT / 'validation.json').write_text(json.dumps(best, indent=2) + '\n')
    (OUT / 'witness.json').write_text(json.dumps(best['witness'], indent=2) + '\n')
    top = []
    candidates = []
    for trial in range(options.trials):
        if options.depth:
            depth, center = options.depth, options.center
        else:
            depth, center = [(48, 1.34), (36, 1.30), (43, 1.42), (24, 1.35)][trial % 4]
        scale = random.choice([0.005, 0.015, 0.035, 0.07])
        if options.scale:
            scale = options.scale * random.choice([0.2, 0.5, 1.0, 2.0])
        if options.knots:
            center = np.asarray(options.knots)
        knots = np.clip(center + random.normal(0, scale, 6), 0.12, 1.45)
        candidates.append(witness(depth, knots))
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(evaluate, candidate) for candidate in candidates]
        for count, future in enumerate(as_completed(futures), 1):
            candidate, records = future.result()
            margin = min(record['margin'] for record in records.values())
            entry = dict(witness=candidate, worst_margin=margin, families=records)
            if len(records) == 5:
                top.append(entry)
                top.sort(key=ranking, reverse=True)
                top = top[:2]
                (OUT / 'refine_best.json').write_text(json.dumps(top, indent=2) + '\n')
                if ranking(entry) > ranking(best):
                    best = entry
                    (OUT / 'validation.json').write_text(json.dumps(best, indent=2) + '\n')
                    (OUT / 'witness.json').write_text(json.dumps(candidate, indent=2) + '\n')
                    print(json.dumps(dict(completed=count, seconds=time.monotonic() - start,
                                          worst_margin=margin, witness=candidate)), flush=True)
            if count % 50 == 0:
                print(json.dumps(dict(completed=count, seconds=time.monotonic() - start,
                                      best_margin=best['worst_margin'])), flush=True)


if __name__ == '__main__':
    main()
