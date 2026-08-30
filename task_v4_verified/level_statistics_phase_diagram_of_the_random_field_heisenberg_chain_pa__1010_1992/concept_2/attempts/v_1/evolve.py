import argparse
import concurrent.futures
import json

from search import FIELDS, ROOT, SPEC, canonical, evaluate, key, load_cache, np, ranked_pairs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bank', type=int, required=True)
    parser.add_argument('--seed', type=int, default=662812)
    parser.add_argument('--count', type=int, default=900)
    args = parser.parse_args()
    bank = args.bank - 1
    cache = load_cache()
    generator = np.random.default_rng(args.seed)
    public = SPEC['public_seeds']
    seeds = public + list(range(20260828, 20260834))
    orders = {tuple(record['order']) for record in cache.values() if record['bank'] == bank}
    summaries = []
    for order in orders:
        if not all(key(bank, order, scale, seed) in cache for scale in SPEC['scales'] for seed in public):
            continue
        ratios = np.array([cache[key(bank, order, scale, seed)]['r'] for scale in SPEC['scales'] for seed in public])
        fractions = np.array([cache[key(bank, order, scale, seed)]['f'] for scale in SPEC['scales'] for seed in public])
        summaries.append((order, float(ratios.mean()), float(ratios.std()), float(fractions.mean())))
    high_min = [0.43, 0.38, 0.34][bank]
    low_max = [0.19, 0.15, 0.12][bank]
    high_parents = sorted([record for record in summaries if record[3] > high_min], key=lambda record: record[1] + 0.5 * record[2])[:20]
    low_parents = sorted([record for record in summaries if record[3] < low_max], key=lambda record: abs(record[1] - 0.408) + 0.5 * record[2])[:20]
    candidates = set()
    while len(candidates) < args.count:
        parents = high_parents if generator.random() < 0.65 else low_parents
        order = list(parents[generator.integers(len(parents))][0])
        clustered = generator.random() < 0.5
        if clustered:
            sizes = [[6, 6], [4, 4, 4], [3, 3, 3, 3], [5, 4, 3], [5, 5, 2]][generator.integers(5)]
            sorted_order = np.argsort(FIELDS[bank])
            blocks = np.split(sorted_order, np.cumsum(sizes)[:-1])
            blocks = [generator.permutation(block).tolist() for block in blocks]
            order = sum([blocks[index] for index in generator.permutation(len(blocks))], [])
        for _ in range(0 if clustered else (1 if generator.random() < 0.75 else 2)):
            first, second = map(int, generator.choice(12, 2, replace=False))
            if generator.random() < 0.3:
                first, second = sorted([first, second])
                order[first:second + 1] = order[first:second + 1][::-1]
            else:
                order[first], order[second] = order[second], order[first]
        order = canonical(order)
        if order not in orders:
            candidates.add(order)
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        evaluate([key(bank, order) for order in candidates], cache, pool)
        filtered = [order for order in candidates if cache[key(bank, order)]['f'] > high_min or cache[key(bank, order)]['f'] < low_max]
        evaluate([key(bank, order, 1.0, seed) for order in filtered for seed in public], cache, pool)
        summarized = []
        for order in filtered:
            ratios = np.array([cache[key(bank, order, 1.0, seed)]['r'] for seed in public])
            fractions = np.array([cache[key(bank, order, 1.0, seed)]['f'] for seed in public])
            summarized.append((order, float(ratios.mean()), float(ratios.std()), float(fractions.mean())))
        high = sorted([record for record in summarized if record[3] > high_min], key=lambda record: abs(record[1] - 0.405) + 0.5 * record[2])[:90]
        low = sorted([record for record in summarized if record[3] < low_max], key=lambda record: abs(record[1] - 0.405) + 0.5 * record[2])[:90]
        selected = {record[0] for record in high + low}
        evaluate([key(bank, order, scale, seed) for order in selected for scale in SPEC['scales'] for seed in public], cache, pool)
        pairs = ranked_pairs(bank, cache, public)
        print('EVOLVED PUBLIC', bank + 1, json.dumps(pairs[:8]), flush=True)
        selected = {tuple(pair[side]) for pair in pairs[:100] for side in ['high', 'low']}
        evaluate([key(bank, order, scale, seed) for order in selected for scale in SPEC['scales'] for seed in seeds], cache, pool)
        pairs = ranked_pairs(bank, cache, seeds)
        print('EVOLVED TRAINING', bank + 1, json.dumps(pairs[:12]), flush=True)
        (ROOT / f'validated_pairs_{bank + 1}.json').write_text(json.dumps(pairs[:200], indent=2) + '\n')
        design = json.loads((ROOT / 'design.json').read_text())
        for layout in design['layouts']:
            if layout['id'] == SPEC['banks'][bank]['id']:
                layout['high'] = pairs[0]['high']
                layout['low'] = pairs[0]['low']
        (ROOT / 'design.json').write_text(json.dumps(design, indent=2) + '\n')


if __name__ == '__main__':
    main()
