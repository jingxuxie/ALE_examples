import argparse
import concurrent.futures
import json

from search import ROOT, SPEC, evaluate, key, load_cache, np, ranked_pairs


def summarize(bank, high, low, seeds, cache):
    public_differences = np.array([[abs(cache[key(bank, high, scale, seed)]['r'] - cache[key(bank, low, scale, seed)]['r'])
                                    for seed in SPEC['public_seeds']] for scale in SPEC['scales']])
    public_separations = np.array([[cache[key(bank, high, scale, seed)]['f'] - cache[key(bank, low, scale, seed)]['f']
                                   for seed in SPEC['public_seeds']] for scale in SPEC['scales']])
    public_passed = bool((public_differences.mean(axis=1) <= 0.02).all()
                         and public_differences.max() <= 0.045
                         and (public_separations.mean(axis=1) >= 0.28).all()
                         and public_separations.min() >= 0.24)
    differences = np.array([[abs(cache[key(bank, high, scale, seed)]['r'] - cache[key(bank, low, scale, seed)]['r'])
                             for seed in seeds] for scale in SPEC['scales']])
    separations = np.array([[cache[key(bank, high, scale, seed)]['f'] - cache[key(bank, low, scale, seed)]['f']
                            for seed in seeds] for scale in SPEC['scales']])
    generator = np.random.default_rng(9876123)
    samples = generator.integers(len(seeds), size=(20000, 5))
    sampled_differences = differences[:, samples]
    sampled_separations = separations[:, samples]
    passed = ((sampled_differences.mean(axis=2) <= 0.02)
              & (sampled_differences.max(axis=2) <= 0.045)
              & (sampled_separations.mean(axis=2) >= 0.28)
              & (sampled_separations.min(axis=2) >= 0.24))
    sampled_scores = np.minimum.reduce([
        0.02 / np.maximum(sampled_differences.mean(axis=2), 1e-12),
        0.045 / np.maximum(sampled_differences.max(axis=2), 1e-12),
        sampled_separations.mean(axis=2) / 0.28,
        sampled_separations.min(axis=2) / 0.24,
        np.ones_like(passed, dtype=float)])
    risk = max(float(np.max((differences.mean(axis=1) + 1.5 * differences.std(axis=1) / np.sqrt(5)) / 0.02)),
               float(np.max(differences) / 0.045),
               float(0.28 / np.min(separations.mean(axis=1))),
               float(0.24 / np.min(separations)))
    return {'bank': bank, 'high': list(high), 'low': list(low), 'risk': risk, 'public_passed': public_passed,
            'mean_bootstrap_core_score': float(sampled_scores.mean()),
            'mean_bootstrap_worst_score': float(sampled_scores.min(axis=0).mean()),
            'empirical_pass_probability': float(passed.all(axis=0).mean()),
            'families': [{'scale': scale, 'mean_abs_r_difference': float(differences[index].mean()),
                          'std_abs_r_difference': float(differences[index].std()),
                          'max_abs_r_difference': float(differences[index].max()),
                          'mean_f_separation': float(separations[index].mean()),
                          'min_f_separation': float(separations[index].min()),
                          'bootstrap_pass_probability': float(passed[index].mean())}
                         for index, scale in enumerate(SPEC['scales'])]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=60)
    parser.add_argument('--seed', type=int, default=910000)
    parser.add_argument('--pairs', type=int, default=4)
    parser.add_argument('--bank', type=int)
    parser.add_argument('--design-only', action='store_true')
    parser.add_argument('--include-training', action='store_true')
    args = parser.parse_args()
    cache = load_cache()
    seeds = list(range(args.seed, args.seed + args.count))
    if args.include_training:
        seeds += list(range(20260828, 20260834))
    existing = json.loads((ROOT / 'design.json').read_text())
    layouts = {layout['id']: layout for layout in existing['layouts']}
    all_results = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        for bank in ([args.bank - 1] if args.bank else [2, 1, 0]):
            identity = SPEC['banks'][bank]['id']
            if args.design_only:
                candidates = [layouts[identity]]
            else:
                candidates = []
                ranked = json.loads((ROOT / f'validated_pairs_{bank + 1}.json').read_text())
                for pair in ranked:
                    public_result = summarize(bank, tuple(pair['high']), tuple(pair['low']), SPEC['public_seeds'], cache)
                    if public_result['public_passed']:
                        candidates.append(pair)
                    if len(candidates) >= args.pairs:
                        break
                if len(candidates) < args.pairs:
                    chosen = {(tuple(pair['high']), tuple(pair['low'])) for pair in candidates}
                    for pair in ranked_pairs(bank, cache, SPEC['public_seeds']):
                        pair_key = (tuple(pair['high']), tuple(pair['low']))
                        if pair['loss'] <= 1 and pair_key not in chosen:
                            candidates.append(pair)
                            chosen.add(pair_key)
                        if len(candidates) >= args.pairs:
                            break
                candidates.append(layouts[identity])
            orders = {tuple(pair[side]) for pair in candidates for side in ['high', 'low']}
            evaluate([key(bank, order, scale, seed) for order in orders for scale in SPEC['scales'] for seed in seeds], cache, pool)
            pairs = [layouts[identity]] if args.design_only else ranked_pairs(bank, cache, seeds)
            results = [summarize(bank, tuple(pair['high']), tuple(pair['low']), seeds, cache)
                       for pair in pairs if args.design_only or pair['min_mean_df'] > 0.27]
            results.sort(key=lambda result: (not result['public_passed'], -result['empirical_pass_probability'], result['risk']))
            if not results:
                raise RuntimeError('No separated pair survives the stress sample')
            all_results[identity] = results[:30]
            best = results[0]
            print('ROBUST', identity, json.dumps(best), flush=True)
            layouts[identity] = {'id': identity, 'high': best['high'], 'low': best['low']}
            (ROOT / f'stress_{bank + 1}_{args.seed}_{args.count}.json').write_text(json.dumps(results[:30], indent=2) + '\n')
            (ROOT / 'design.json').write_text(json.dumps({'layouts': sorted(layouts.values(), key=lambda layout: layout['id'])}, indent=2) + '\n')


if __name__ == '__main__':
    main()
