import json
import numpy as np
from search import Database, OUTPUT, SPEC, FIELDS, canonical, rank_robust


def screen(database):
    generator = np.random.default_rng(20149503)
    training = json.loads((OUTPUT / 'perturbation_shortlists.json').read_text())
    selections = []
    jobs = []
    for bank in range(3):
        rows = [(order, values[0], values[1]) for (identity, order, scale, seed), values in database.data.items()
                if identity == bank and scale == 1 and seed is None]
        high = set()
        for lower in np.arange(0.38, 0.66, 0.04):
            bucket = [row for row in rows if lower <= row[2] < lower + 0.04]
            high.update(row[0] for row in sorted(bucket, key=lambda row: row[1])[:25])
        low = set(row[0] for row in sorted(rows, key=lambda row: row[2])[:90])
        low.update(row[0] for row in sorted([row for row in rows if row[2] < 0.26], key=lambda row: -row[1])[:40])
        parent_scores = []
        for order in training['banks'][bank]['high']:
            values = database.values(bank, order, training['seeds'])
            parent_scores.append((values[:, :, 0].mean() + max(0, 0.40 - values[:, :, 1].min()), order))
        parents = [order for score, order in sorted(parent_scores)[:8]]
        high_initial = len(high)
        while len(high) < high_initial + 200:
            order = list(parents[generator.integers(len(parents))])
            left, right = generator.choice(12, 2, replace=False)
            order[left], order[right] = order[right], order[left]
            high.add(canonical(order))
        low_initial = len(low)
        sorted_order = np.argsort(FIELDS[bank])
        while len(low) < low_initial + 200:
            order = np.empty(12, dtype=int)
            order[::2] = generator.permutation(sorted_order[:6])
            order[1::2] = generator.permutation(sorted_order[6:])
            if generator.random() < 0.3:
                left, right = generator.choice(12, 2, replace=False)
                order[left], order[right] = order[right], order[left]
            low.add(canonical(order))
        selections.append({'high': sorted(high), 'low': sorted(low)})
        jobs += [(bank, order, 1.0, seed) for order in high | low for seed in SPEC['public_seeds']]
        print('SCREEN BANK', bank + 1, len(high), len(low), flush=True)
    (OUTPUT / 'refine_screen.json').write_text(json.dumps(selections))
    database.run(jobs)


def families(database):
    selections = json.loads((OUTPUT / 'refine_screen.json').read_text())
    generator = np.random.default_rng(9215971)
    seeds = SPEC['public_seeds'] + generator.integers(100000, 2000000000, 3).tolist()
    chosen = []
    jobs = []
    for bank, selection in enumerate(selections):
        high_records, low_records = [], []
        for role, records in [('high', high_records), ('low', low_records)]:
            for order in selection[role]:
                values = database.values(bank, order, SPEC['public_seeds'], [1.0])[0]
                records.append((order, values[:, 0], values[:, 1]))
        pairs = []
        for high, high_r, high_f in high_records:
            for low, low_r, low_f in low_records:
                difference = np.abs(high_r - low_r)
                separation = high_f - low_f
                if separation.min() < 0.30:
                    continue
                score = (difference.mean() + 0.6 * difference.max()
                         + 0.5 * max(0, 0.34 - separation.min())
                         + 0.6 * abs(high_r.mean() - low_r.mean()))
                pairs.append((float(score), high, low))
        pairs.sort()
        highs, lows = set(), set()
        for score, high, low in pairs:
            high, low = tuple(high), tuple(low)
            if len(highs | {high}) <= 45 and len(lows | {low}) <= 55:
                highs.add(high)
                lows.add(low)
        chosen.append({'high': sorted(highs), 'low': sorted(lows)})
        print('FAMILIES BANK', bank + 1, len(highs), len(lows), 'top', pairs[:5], flush=True)
        jobs += [(bank, order, scale, seed) for order in highs | lows for scale in SPEC['scales'] for seed in seeds]
    (OUTPUT / 'refine_families.json').write_text(json.dumps({'banks': chosen, 'seeds': seeds}))
    database.run(jobs)
    rank_robust(database, seeds, chosen)


if __name__ == '__main__':
    database = Database()
    screen(database)
    families(database)
