import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import argparse
import concurrent.futures
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parent
PARTICIPANT = ROOT.parent.parent / 'participant'
sys.path.insert(0, str(PARTICIPANT / 'workspace'))
from physics import observables

SPEC = json.loads((PARTICIPANT / 'input/spec.json').read_text())
FIELDS = [np.array(bank['fields']) for bank in SPEC['banks']]


def canonical(order):
    order = list(map(int, order))
    start = order.index(0)
    forward = order[start:] + order[:start]
    backward = [forward[0]] + forward[:0:-1]
    return tuple(min(forward, backward))


def compute(task):
    bank, order, scale, seed = task
    noise = np.zeros(12) if seed is None else np.random.default_rng(seed).uniform(-0.02, 0.02, 12)
    result = observables((scale * FIELDS[bank] + noise)[list(order)])
    return {'bank': bank, 'order': list(order), 'scale': scale, 'seed': seed,
            'r': result['r'], 'f': result['f']}


def key(bank, order, scale=1.0, seed=None):
    return (bank, tuple(order), scale, seed)


def load_cache():
    cache = {}
    path = ROOT / 'observations.jsonl'
    if path.exists():
        for line in path.read_text().splitlines():
            record = json.loads(line)
            cache[key(record['bank'], record['order'], record['scale'], record['seed'])] = record
    return cache


def evaluate(tasks, cache, pool):
    tasks = list(dict.fromkeys(tasks))
    missing = [task for task in tasks if task not in cache]
    started = time.time()
    print('evaluating', len(missing), 'new observations', flush=True)
    with (ROOT / 'observations.jsonl').open('a', buffering=1) as output:
        for count, record in enumerate(pool.map(compute, missing, chunksize=1), 1):
            cache[key(record['bank'], record['order'], record['scale'], record['seed'])] = record
            output.write(json.dumps(record) + '\n')
            if count % 100 == 0:
                print('progress', count, '/', len(missing), 'seconds', round(time.time() - started, 1), flush=True)


def generate(bank, count, rng):
    sorted_order = np.argsort(FIELDS[bank])
    saw = sorted_order[[0, 2, 4, 6, 8, 10, 11, 9, 7, 5, 3, 1]]
    candidates = {canonical(sorted_order), canonical(saw)}
    while len(candidates) < count:
        category = rng.integers(10)
        if category < 5:
            order = (sorted_order if category < 3 else saw).copy()
            for _ in range(rng.integers(1, 6)):
                first, second = rng.choice(12, 2, replace=False)
                if rng.random() < 0.45:
                    first, second = sorted([first, second])
                    order[first:second + 1] = order[first:second + 1][::-1]
                else:
                    order[first], order[second] = order[second], order[first]
        elif category == 5:
            order = sorted_order[np.argsort(np.arange(12) + rng.normal(0, rng.uniform(0.7, 3.5), 12))]
        elif category < 8:
            order = rng.permutation(12)
        else:
            lower = rng.permutation(sorted_order[:6])
            upper = rng.permutation(sorted_order[6:])
            order = np.column_stack([lower, upper]).ravel()
        candidates.add(canonical(order))
    return list(candidates)


def ranked_pairs(bank, cache, seeds):
    orders = sorted({record['order'] and tuple(record['order']) for record in cache.values() if record['bank'] == bank})
    complete = [order for order in orders if all(key(bank, order, scale, seed) in cache for scale in SPEC['scales'] for seed in seeds)]
    if not complete:
        return []
    ratios = np.array([[[cache[key(bank, order, scale, seed)]['r'] for seed in seeds] for scale in SPEC['scales']] for order in complete])
    fractions = np.array([[[cache[key(bank, order, scale, seed)]['f'] for seed in seeds] for scale in SPEC['scales']] for order in complete])
    pairs = []
    for high_index, high in enumerate(complete):
        difference = np.abs(ratios[high_index] - ratios)
        separation = fractions[high_index] - fractions
        mean_difference = difference.mean(axis=2).max(axis=1)
        max_difference = difference.max(axis=(1, 2))
        mean_separation = separation.mean(axis=2).min(axis=1)
        min_separation = separation.min(axis=(1, 2))
        loss = np.maximum.reduce([mean_difference / 0.02, max_difference / 0.045,
                                  0.28 / np.maximum(mean_separation, 1e-6),
                                  0.24 / np.maximum(min_separation, 1e-6)])
        loss[(mean_separation < 0.285) | (min_separation < 0.245)] = np.inf
        for low_index in np.argsort(loss)[:8]:
            if not np.isfinite(loss[low_index]):
                continue
            pairs.append({'bank': bank, 'high': list(high), 'low': list(complete[low_index]),
                          'loss': float(loss[low_index]), 'max_mean_dr': float(mean_difference[low_index]),
                          'max_dr': float(max_difference[low_index]), 'min_mean_df': float(mean_separation[low_index]),
                          'min_df': float(min_separation[low_index])})
    return sorted(pairs, key=lambda pair: pair['loss'])


def screen(args, cache, pool):
    rng = np.random.default_rng(args.seed)
    for bank in [2, 1, 0]:
        candidates = generate(bank, args.count, rng)
        evaluate([key(bank, order) for order in candidates], cache, pool)
        records = [cache[key(bank, order)] for order in candidates]
        best_high = sorted(records, key=lambda record: -(record['f'] - 2.5 * max(0, record['r'] - 0.41)))[:12]
        best_low = sorted(records, key=lambda record: record['f'] + 2 * abs(record['r'] - 0.42))[:12]
        print('BANK', bank + 1, 'HIGH', best_high, 'LOW', best_low, flush=True)


def expand(args, cache, pool):
    for bank in [2, 1, 0]:
        records = [record for record in cache.values() if record['bank'] == bank and record['scale'] == 1 and record['seed'] is None]
        selected = set()
        for center in np.linspace(0.36, 0.49, 14):
            nearby = sorted(records, key=lambda record: -(record['f'] - 4 * abs(record['r'] - center)))[:args.count]
            selected.update(tuple(record['order']) for record in nearby)
            nearby = sorted(records, key=lambda record: record['f'] + 4 * abs(record['r'] - center))[:args.count]
            selected.update(tuple(record['order']) for record in nearby)
        evaluate([key(bank, order, scale) for order in selected for scale in SPEC['scales']], cache, pool)
        pairs = ranked_pairs(bank, cache, [None])
        (ROOT / f'pairs_{bank + 1}.json').write_text(json.dumps(pairs[:200], indent=2) + '\n')
        print('BANK', bank + 1, 'TOP PAIRS', json.dumps(pairs[:8]), flush=True)


def validate(args, cache, pool):
    seeds = [None, 74032, 51067] + list(range(args.seed, args.seed + args.count))
    layouts = []
    for bank in [2, 1, 0]:
        pairs = ranked_pairs(bank, cache, [None])
        selected = set()
        for pair in pairs[:args.pairs]:
            selected.add(tuple(pair['high']))
            selected.add(tuple(pair['low']))
        evaluate([key(bank, order, scale, seed) for order in selected for scale in SPEC['scales'] for seed in seeds], cache, pool)
        pairs = ranked_pairs(bank, cache, seeds)
        (ROOT / f'validated_pairs_{bank + 1}.json').write_text(json.dumps(pairs[:200], indent=2) + '\n')
        print('VALIDATED BANK', bank + 1, json.dumps(pairs[:8]), flush=True)
        best = pairs[0]
        layouts.append({'id': SPEC['banks'][bank]['id'], 'high': best['high'], 'low': best['low']})
    (ROOT / 'design.json').write_text(json.dumps({'layouts': sorted(layouts, key=lambda layout: layout['id'])}, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['screen', 'expand', 'validate'])
    parser.add_argument('--count', type=int, default=600)
    parser.add_argument('--seed', type=int, default=20260828)
    parser.add_argument('--pairs', type=int, default=10)
    args = parser.parse_args()
    cache = load_cache()
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        globals()[args.mode](args, cache, pool)


if __name__ == '__main__':
    main()
