import json
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from search import Database, OUTPUT, SPEC, canonical, evaluate
from enrich import final_rank


def anneal(job):
    bank, starts, seed, count = job
    generator = np.random.default_rng(seed)
    current = tuple(starts[0])
    initial = evaluate((bank, current, 1.0, None))
    current_value = initial[5]
    best, best_value = current, current_value
    results = [initial]
    seen = {current: current_value}
    for iteration in range(count):
        if iteration % 80 == 0:
            current = best if generator.random() < 0.6 else tuple(starts[generator.integers(len(starts))])
            if current not in seen:
                record = evaluate((bank, current, 1.0, None))
                seen[current] = record[5]
                results.append(record)
            current_value = seen[current]
        order = list(current)
        left, right = generator.choice(12, 2, replace=False)
        order[left], order[right] = order[right], order[left]
        proposed = canonical(order)
        if proposed not in seen:
            record = evaluate((bank, proposed, 1.0, None))
            seen[proposed] = record[5]
            results.append(record)
        value = seen[proposed]
        temperature = 0.003 + 0.007 * (1 - (iteration % 80) / 80)
        if value < current_value or generator.random() < np.exp(min(0, (current_value - value) / temperature)):
            current, current_value = proposed, value
        if value < best_value:
            best, best_value = proposed, value
    return bank, best, best_value, results


def main():
    database = Database()
    starts = []
    for bank in range(3):
        records = [(values[1], order) for (identity, order, scale, seed), values in database.data.items()
                   if identity == bank and scale == 1 and seed is None]
        starts.append([order for value, order in sorted(records)[:5]])
    jobs = [(0, starts[0], 490103, 250), (0, starts[0], 492817, 250),
            (1, starts[1], 831995, 200), (2, starts[2], 912819, 200)]
    with ProcessPoolExecutor(max_workers=4) as pool, database.path.open('a', buffering=1) as stream:
        for bank, best, best_value, results in pool.map(anneal, jobs):
            for record in results:
                key = database.key(record[:4])
                if key not in database.data:
                    database.data[key] = record[4:]
                    stream.write(json.dumps(record) + '\n')
            print('LOW SEARCH', bank + 1, best_value, best, flush=True)
    low_orders, jobs = [], []
    for bank in range(3):
        records = [(values[1], order) for (identity, order, scale, seed), values in database.data.items()
                   if identity == bank and scale == 1 and seed is None]
        low_orders.append([order for value, order in sorted(records)[:12]])
        jobs += [(bank, order, 1.0, seed) for order in low_orders[-1] for seed in SPEC['public_seeds']]
    database.run(jobs)
    source = json.loads((OUTPUT / 'refine_screen.json').read_text())
    training = json.loads((OUTPUT / 'final_training.json').read_text())
    seeds = training['seeds']
    previous = json.loads((OUTPUT / 'robust_pairs.json').read_text())
    chosen, jobs = [], []
    for bank in range(3):
        pairs = []
        for high in source[bank]['high']:
            high_values = database.values(bank, high, SPEC['public_seeds'], [1.0])[0]
            for low in low_orders[bank]:
                low_values = database.values(bank, low, SPEC['public_seeds'], [1.0])[0]
                gap = np.abs(high_values[:, 0] - low_values[:, 0])
                separation = high_values[:, 1] - low_values[:, 1]
                if separation.mean() < 0.29 or separation.min() < 0.27:
                    continue
                score = gap.mean() + 0.5 * gap.max() + max(0, 0.31 - separation.min())
                pairs.append((float(score), tuple(high), tuple(low)))
        highs, lows = set(), set()
        for score, high, low in sorted(pairs):
            if len(highs | {high}) <= 10 and len(lows | {low}) <= 6:
                highs.add(high)
                lows.add(low)
        for record in previous[bank][:5]:
            highs.add(tuple(record['high']))
            lows.add(tuple(record['low']))
        chosen.append({'high': sorted(highs), 'low': sorted(lows)})
        jobs += [(bank, order, scale, seed) for order in highs | lows for scale in SPEC['scales'] for seed in seeds]
    database.run(jobs)
    (OUTPUT / 'low_training.json').write_text(json.dumps({'banks': chosen, 'seeds': seeds}))
    final_rank(database, seeds, chosen)


if __name__ == '__main__':
    main()
