import argparse
import concurrent.futures
import itertools
import json

from search import FIELDS, ROOT, SPEC, canonical, evaluate, key, load_cache, np, ranked_pairs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bank', type=int, required=True)
    parser.add_argument('--count', type=int, default=576)
    args = parser.parse_args()
    bank = args.bank - 1
    cache = load_cache()
    sorted_order = np.argsort(FIELDS[bank]).tolist()
    candidates = set()
    for lower in itertools.permutations(sorted_order[2:6]):
        for upper in itertools.permutations(sorted_order[6:10]):
            candidates.add(canonical([sorted_order[0], *lower, sorted_order[1], sorted_order[10], *upper, sorted_order[11]]))
    if len(candidates) > args.count:
        ordered_candidates = sorted(candidates)
        selected_indices = np.random.default_rng(88712).choice(len(ordered_candidates), args.count, replace=False)
        candidates = {ordered_candidates[index] for index in selected_indices}
    public = SPEC['public_seeds']
    seeds = public + list(range(20260828, 20260834))
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        evaluate([key(bank, order, 1.0, seed) for order in candidates for seed in public], cache, pool)
        records = []
        for order in candidates:
            ratios = np.array([cache[key(bank, order, 1.0, seed)]['r'] for seed in public])
            fraction = np.mean([cache[key(bank, order, 1.0, seed)]['f'] for seed in public])
            if fraction >= [0.43, 0.37, 0.33][bank]:
                records.append((abs(float(ratios.mean()) - 0.398) + 0.3 * float(ratios.std()), order, float(fraction)))
        selected = {record[1] for record in sorted(records)[:min(100, args.count // 2)]}
        print('BLOCK CANDIDATES', bank + 1, len(records), sorted(records)[:10], flush=True)
        evaluate([key(bank, order, scale, seed) for order in selected for scale in SPEC['scales'] for seed in public], cache, pool)
        pairs = ranked_pairs(bank, cache, public)
        selected = {tuple(pair[side]) for pair in pairs[:150] for side in ['high', 'low']}
        evaluate([key(bank, order, scale, seed) for order in selected for scale in SPEC['scales'] for seed in seeds], cache, pool)
        pairs = ranked_pairs(bank, cache, seeds)
        print('BLOCK TRAINING', bank + 1, json.dumps(pairs[:12]), flush=True)
        (ROOT / f'validated_pairs_{bank + 1}.json').write_text(json.dumps(pairs[:200], indent=2) + '\n')
        design = json.loads((ROOT / 'design.json').read_text())
        for layout in design['layouts']:
            if layout['id'] == SPEC['banks'][bank]['id']:
                layout['high'] = pairs[0]['high']
                layout['low'] = pairs[0]['low']
        (ROOT / 'design.json').write_text(json.dumps(design, indent=2) + '\n')


if __name__ == '__main__':
    main()
