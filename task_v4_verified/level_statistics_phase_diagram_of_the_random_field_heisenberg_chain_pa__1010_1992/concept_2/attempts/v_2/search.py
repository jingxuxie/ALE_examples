import os
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
             'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import sys
import time
import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/level_statistics_phase_diagram_of_the_random_field_heisenberg_chain_pa__1010_1992/concept_2/participant')
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'workspace'))
from physics import observables

SPEC = json.loads((ROOT / 'input/spec.json').read_text())
FIELDS = [np.array(bank['fields']) for bank in SPEC['banks']]


def canonical(order):
    order = list(map(int, order))
    position = order.index(0)
    forward = tuple(order[position:] + order[:position])
    backward = (0,) + tuple(reversed(forward[1:]))
    return min(forward, backward)


def evaluate(job):
    bank, order, scale, seed = job
    noise = np.zeros(12) if seed is None else np.random.default_rng(seed).uniform(-0.02, 0.02, 12)
    with threadpool_limits(1):
        result = observables((scale * FIELDS[bank] + noise)[list(order)])
    return [bank, list(order), scale, seed, result['r'], result['f']]


class Database:
    def __init__(self):
        self.path = OUTPUT / 'observations.jsonl'
        self.data = {}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                record = json.loads(line)
                self.data[self.key(record[:4])] = record[4:]

    @staticmethod
    def key(job):
        bank, order, scale, seed = job
        return bank, tuple(order), scale, seed

    def run(self, jobs):
        pending = list(dict.fromkeys(self.key(job) for job in jobs if self.key(job) not in self.data))
        started = time.monotonic()
        print('Evaluating', len(pending), 'new observables;', len(self.data), 'cached', flush=True)
        with ProcessPoolExecutor(max_workers=4) as pool, self.path.open('a', buffering=1) as stream:
            for count, record in enumerate(pool.map(evaluate, pending, chunksize=1), 1):
                self.data[self.key(record[:4])] = record[4:]
                stream.write(json.dumps(record) + '\n')
                if count % 100 == 0:
                    print('Progress', count, '/', len(pending), 'seconds', round(time.monotonic() - started, 1), flush=True)

    def values(self, bank, order, seeds=(None,), scales=(0.96, 1.0, 1.04)):
        return np.array([[self.data[(bank, tuple(order), scale, seed)] for seed in seeds] for scale in scales])


def candidates(bank, count=1000):
    generator = np.random.default_rng(6500 + bank)
    sorted_order = np.argsort(FIELDS[bank])
    triangle = sorted_order[[0, 2, 4, 6, 8, 10, 11, 9, 7, 5, 3, 1]]
    patterns = {canonical(sorted_order), canonical(triangle)}
    for base in (sorted_order, triangle):
        for left in range(12):
            for right in range(left + 1, 12):
                order = base.copy()
                order[left], order[right] = order[right], order[left]
                patterns.add(canonical(order))
    while len(patterns) < count:
        choice = generator.integers(5)
        if choice == 0:
            order = generator.permutation(12)
        elif choice == 1:
            order = sorted_order[np.argsort(np.arange(12) + generator.normal(0, generator.uniform(0.7, 4), 12))]
        else:
            order = (sorted_order if choice == 2 else triangle).copy()
            for swap in range(generator.integers(1, 5)):
                left, right = generator.choice(12, 2, replace=False)
                order[left], order[right] = order[right], order[left]
        patterns.add(canonical(order))
    return sorted(patterns)


def scan(database, count):
    jobs = [(bank, order, 1.0, None) for bank in range(3) for order in candidates(bank, count)]
    database.run(jobs)
    for bank in range(3):
        rows = [(values[1], values[0], order) for (identity, order, scale, seed), values in database.data.items()
                if identity == bank and scale == 1 and seed is None and values[0] < 0.445]
        print('BANK', bank + 1, 'BEST HIGH', sorted(rows, reverse=True)[:15], flush=True)


def profiles(database):
    selections = []
    jobs = []
    for bank in range(3):
        rows = [(tuple(order), values[0], values[1]) for (identity, order, scale, seed), values in database.data.items()
                if identity == bank and scale == 1 and seed is None]
        high, low = set(), set()
        edges = [0.35, 0.385, 0.40, 0.415, 0.43, 0.445, 0.46]
        for lower, upper in zip(edges[:-1], edges[1:]):
            bucket = [row for row in rows if lower <= row[1] < upper]
            high.update(row[0] for row in sorted(bucket, key=lambda row: -row[2])[:20] if row[2] > 0.36)
            low.update(row[0] for row in sorted(bucket, key=lambda row: row[2])[:25])
        high, low = sorted(high), sorted(low)
        print('Shortlist bank', bank + 1, 'high', len(high), 'low', len(low), flush=True)
        selections.append({'high': high, 'low': low})
        jobs += [(bank, order, scale, None) for order in set(high + low) for scale in SPEC['scales']]
    database.run(jobs)
    (OUTPUT / 'shortlists.json').write_text(json.dumps(selections))
    pairs = []
    for bank, selection in enumerate(selections):
        ranked = []
        for high in selection['high']:
            high_values = database.values(bank, high)[:, 0]
            for low in selection['low']:
                low_values = database.values(bank, low)[:, 0]
                difference = np.abs(high_values[:, 0] - low_values[:, 0])
                separation = high_values[:, 1] - low_values[:, 1]
                if separation.min() < 0.295:
                    continue
                score = difference.mean() + 0.7 * difference.max() + 2 * max(0.0, 0.33 - separation.min()) - 0.015 * min(separation.min(), 0.45)
                ranked.append({'score': float(score), 'high': high, 'low': low,
                               'gap': difference.tolist(), 'separation': separation.tolist()})
        ranked.sort(key=lambda record: record['score'])
        print('PAIRS BANK', bank + 1, 'COUNT', len(ranked), 'TOP', ranked[:8], flush=True)
        pairs.append(ranked)
    (OUTPUT / 'profile_pairs.json').write_text(json.dumps(pairs))


def perturbations(database):
    profiles_data = json.loads((OUTPUT / 'profile_pairs.json').read_text())
    generator = np.random.default_rng(941584)
    seeds = SPEC['public_seeds'] + generator.integers(100000, 100000000, 12).tolist()
    chosen = []
    jobs = []
    for bank, pairs in enumerate(profiles_data):
        highs, lows = set(), set()
        for pair in pairs:
            high, low = tuple(pair['high']), tuple(pair['low'])
            if len(highs | {high}) <= 18 and len(lows | {low}) <= 28:
                highs.add(high)
                lows.add(low)
            if len(highs) == 18 and len(lows) == 28:
                break
        chosen.append({'high': sorted(highs), 'low': sorted(lows)})
        print('Perturbation shortlist bank', bank + 1, len(highs), len(lows), flush=True)
        jobs += [(bank, order, scale, seed) for order in highs | lows for scale in SPEC['scales'] for seed in seeds]
    database.run(jobs)
    (OUTPUT / 'perturbation_shortlists.json').write_text(json.dumps({'seeds': seeds, 'banks': chosen}))
    rank_robust(database, seeds, chosen)


def rank_robust(database, seeds, chosen):
    all_ranked, layouts = [], []
    for bank, selection in enumerate(chosen):
        ranked = []
        for high in selection['high']:
            high_values = database.values(bank, high, seeds)
            for low in selection['low']:
                low_values = database.values(bank, low, seeds)
                difference = np.abs(high_values[:, :, 0] - low_values[:, :, 0])
                separation = high_values[:, :, 1] - low_values[:, :, 1]
                mean_gap = difference.mean(axis=1)
                upper_gap = mean_gap + 1.2 * difference.std(axis=1) / np.sqrt(5)
                score = (max(upper_gap) + 0.2 * difference.max()
                         + 3 * max(0, 0.295 - separation.mean(axis=1).min())
                         + 3 * max(0, 0.26 - separation.min())
                         - 0.01 * min(separation.min(), 0.33))
                ranked.append({'score': float(score), 'high': high, 'low': low,
                               'mean_gap': mean_gap.tolist(), 'max_gap': difference.max(axis=1).tolist(),
                               'mean_separation': separation.mean(axis=1).tolist(),
                               'min_separation': separation.min(axis=1).tolist()})
        ranked.sort(key=lambda record: record['score'])
        print('ROBUST BANK', bank + 1, 'TOP', ranked[:10], flush=True)
        all_ranked.append(ranked)
        best = ranked[0]
        layouts.append({'id': SPEC['banks'][bank]['id'], 'high': best['high'], 'low': best['low']})
    (OUTPUT / 'robust_pairs.json').write_text(json.dumps(all_ranked, indent=2))
    (OUTPUT / 'design.json').write_text(json.dumps({'layouts': layouts}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['scan', 'profiles', 'perturbations'])
    parser.add_argument('--count', type=int, default=1000)
    args = parser.parse_args()
    database = Database()
    if args.stage == 'scan':
        scan(database, args.count)
    elif args.stage == 'profiles':
        profiles(database)
    elif args.stage == 'perturbations':
        perturbations(database)
