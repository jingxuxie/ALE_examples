import json
import numpy as np
from search import Database, OUTPUT, SPEC, rank_robust


def quality(high_values, low_values, draws):
    difference = np.abs(high_values[:, :, 0] - low_values[:, :, 0])
    separation = high_values[:, :, 1] - low_values[:, :, 1]
    public_margins = np.array([0.02 / np.maximum(difference[:, :3].mean(axis=1), 1e-12),
                               0.045 / np.maximum(difference[:, :3].max(axis=1), 1e-12),
                               separation[:, :3].mean(axis=1) / 0.28,
                               separation[:, :3].min(axis=1) / 0.24])
    sampled_gap = difference[:, 3:][:, draws]
    sampled_separation = separation[:, 3:][:, draws]
    margins = np.array([0.02 / np.maximum(sampled_gap.mean(axis=2), 1e-12),
                        0.045 / np.maximum(sampled_gap.max(axis=2), 1e-12),
                        sampled_separation.mean(axis=2) / 0.28,
                        sampled_separation.min(axis=2) / 0.24])
    family_scores = np.minimum(margins.min(axis=0), 1)
    probability_pass = (family_scores.min(axis=0) >= 1).mean()
    utility = 0.6 * family_scores.mean() + 0.4 * family_scores.min(axis=0).mean() + 0.15 * probability_pass
    public_penalty = 2 * (public_margins.min() < 1) + 4 * max(0, 1 - public_margins.min())
    score = public_penalty - utility
    return {'score': float(score), 'public_pass': bool(public_margins.min() >= 1),
            'expected_family_score': family_scores.mean(axis=1).tolist(),
            'expected_worst_score': float(family_scores.min(axis=0).mean()),
            'probability_pass': float(probability_pass),
            'mean_gap': difference.mean(axis=1).tolist(),
            'max_gap': difference.max(axis=1).tolist(),
            'mean_separation': separation.mean(axis=1).tolist(),
            'min_separation': separation.min(axis=1).tolist()}


def final_rank(database, seeds, chosen):
    generator = np.random.default_rng(402982)
    draws = generator.integers(0, len(seeds) - 3, (3000, 5))
    all_ranked, layouts = [], []
    for bank, selection in enumerate(chosen):
        orders = {order for identity, order, scale, seed in database.data if identity == bank}
        complete = [order for order in orders
                    if all((bank, order, scale, seed) in database.data for scale in SPEC['scales'] for seed in seeds)]
        high_data = [(order, database.values(bank, order, seeds)) for order in complete]
        low_data = high_data
        ranked = []
        for high, high_values in high_data:
            for low, low_values in low_data:
                if (high_values[:, :, 1] - low_values[:, :, 1]).mean(axis=1).min() < 0.275:
                    continue
                result = quality(high_values, low_values, draws)
                result.update({'high': high, 'low': low})
                ranked.append(result)
        ranked.sort(key=lambda record: record['score'])
        all_ranked.append(ranked)
        print('ENRICHED BANK', bank + 1, json.dumps(ranked[:5]), flush=True)
        best = ranked[0]
        layouts.append({'id': SPEC['banks'][bank]['id'], 'high': best['high'], 'low': best['low']})
    (OUTPUT / 'robust_pairs.json').write_text(json.dumps(all_ranked, indent=2))
    (OUTPUT / 'design.json').write_text(json.dumps({'layouts': layouts}, indent=2) + '\n')


def main():
    database = Database()
    source = json.loads((OUTPUT / 'refine_families.json').read_text())
    rank_robust(database, source['seeds'], source['banks'])
    pairs = json.loads((OUTPUT / 'robust_pairs.json').read_text())
    generator = np.random.default_rng(20014975)
    seeds = source['seeds'] + generator.integers(100000, 2000000000, 12).tolist()
    chosen, jobs = [], []
    for bank, records in enumerate(pairs):
        highs, lows = set(), set()
        for record in records:
            high, low = tuple(record['high']), tuple(record['low'])
            if len(highs | {high}) <= 16 and len(lows | {low}) <= 24:
                highs.add(high)
                lows.add(low)
        chosen.append({'high': sorted(highs), 'low': sorted(lows)})
        jobs += [(bank, order, scale, seed) for order in highs | lows for scale in SPEC['scales'] for seed in seeds]
    (OUTPUT / 'final_training.json').write_text(json.dumps({'banks': chosen, 'seeds': seeds}))
    database.run(jobs)
    final_rank(database, seeds, chosen)


if __name__ == '__main__':
    main()
