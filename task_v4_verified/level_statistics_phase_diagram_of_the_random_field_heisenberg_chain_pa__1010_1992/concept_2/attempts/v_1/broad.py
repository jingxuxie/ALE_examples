import argparse
import concurrent.futures
import json

from search import ROOT, SPEC, evaluate, key, load_cache, np, ranked_pairs


def select(bank, cache):
    records = [record for record in cache.values() if record['bank'] == bank and record['scale'] == 1 and record['seed'] is None]
    selected = set()
    lower = [0.40, 0.34, 0.31][bank]
    upper = [0.72, 0.66, 0.59][bank]
    for first, last, bins, per_bin in [(lower, upper, 12, 8), (0.06, 0.34, 12, 10)]:
        edges = np.linspace(first, last, bins + 1)
        for left, right in zip(edges[:-1], edges[1:]):
            candidates = [record for record in records if left <= record['f'] < right]
            candidates.sort(key=lambda record: abs(record['r'] - 0.41))
            selected.update(tuple(record['order']) for record in candidates[:per_bin])
    return selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bank', type=int)
    parser.add_argument('--pairs', type=int, default=70)
    args = parser.parse_args()
    cache = load_cache()
    layouts = {layout['id']: layout for layout in json.loads((ROOT / 'design.json').read_text())['layouts']}
    seeds = [None, 74032, 51067, 20260828]
    expanded_seeds = seeds + list(range(20260829, 20260834))
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        for bank in ([args.bank - 1] if args.bank else [0, 1, 2]):
            orders = select(bank, cache)
            print('BROAD', bank + 1, 'orders', len(orders), flush=True)
            evaluate([key(bank, order, scale, seed) for order in orders for scale in SPEC['scales'] for seed in seeds], cache, pool)
            pairs = ranked_pairs(bank, cache, seeds)
            print('BROAD INITIAL', bank + 1, json.dumps(pairs[:5]), flush=True)
            selected = {tuple(pair[side]) for pair in pairs[:args.pairs] for side in ['high', 'low']}
            evaluate([key(bank, order, scale, seed) for order in selected for scale in SPEC['scales'] for seed in expanded_seeds], cache, pool)
            pairs = ranked_pairs(bank, cache, expanded_seeds)
            print('BROAD VALIDATED', bank + 1, json.dumps(pairs[:8]), flush=True)
            (ROOT / f'validated_pairs_{bank + 1}.json').write_text(json.dumps(pairs[:200], indent=2) + '\n')
            best = pairs[0]
            identity = SPEC['banks'][bank]['id']
            layouts[identity] = {'id': identity, 'high': best['high'], 'low': best['low']}
            (ROOT / 'design.json').write_text(json.dumps({'layouts': list(layouts.values())}, indent=2) + '\n')


if __name__ == '__main__':
    main()
