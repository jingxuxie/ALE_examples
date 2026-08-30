import itertools
import json
import numpy as np
from search import Database, OUTPUT


def main():
    database = Database()
    training = json.loads((OUTPUT / 'final_training.json').read_text())
    selection = json.loads((OUTPUT / 'selection_validation.json').read_text())
    seeds = training['seeds'][1:] + selection['seeds']
    current = json.loads((OUTPUT / 'design.json').read_text())
    candidates = selection['reports']
    extra = OUTPUT / 'bank1_validation.json'
    if extra.exists():
        candidates[0] += json.loads(extra.read_text())
    generator = np.random.default_rng(5739146)
    draws = generator.integers(0, len(seeds), (10000, 5))
    banks = []
    for bank, records in enumerate(candidates):
        records.append(current['layouts'][bank])
        seen, assessed = set(), []
        for record in records:
            identity = tuple(record['high']), tuple(record['low'])
            if identity in seen:
                continue
            seen.add(identity)
            try:
                high = database.values(bank, identity[0], seeds)
                low = database.values(bank, identity[1], seeds)
            except KeyError:
                continue
            gap = np.abs(high[:, :, 0] - low[:, :, 0])
            separation = high[:, :, 1] - low[:, :, 1]
            if separation.mean(axis=1).min() < 0.28 or separation.min() < 0.24:
                continue
            sampled_gap = gap[:, draws]
            sampled_separation = separation[:, draws]
            margins = np.array([0.02 / np.maximum(sampled_gap.mean(axis=2), 1e-12),
                                0.045 / np.maximum(sampled_gap.max(axis=2), 1e-12),
                                sampled_separation.mean(axis=2) / 0.28,
                                sampled_separation.min(axis=2) / 0.24])
            scores = np.minimum(margins.min(axis=0), 1)
            assessed.append({'high': identity[0], 'low': identity[1],
                             'mean': scores.mean(axis=0), 'worst': scores.min(axis=0),
                             'mean_gap': gap.mean(axis=1).tolist(),
                             'mean_separation': separation.mean(axis=1).tolist()})
        banks.append(assessed)
    ranked = []
    for indices in itertools.product(*(range(len(bank)) for bank in banks)):
        records = [banks[bank][index] for bank, index in enumerate(indices)]
        mean_score = np.mean([record['mean'] for record in records], axis=0)
        worst_score = np.min([record['worst'] for record in records], axis=0)
        pass_probability = float((worst_score >= 1).mean())
        utility = 0.6 * mean_score.mean() + 0.4 * worst_score.mean() + 0.15 * pass_probability
        ranked.append({'utility': float(utility), 'indices': indices,
                       'expected_core_score': float(100 * mean_score.mean()),
                       'expected_worst_score': float(100 * worst_score.mean()),
                       'all_family_pass_probability': pass_probability})
    ranked.sort(key=lambda record: -record['utility'])
    best = ranked[0]
    layouts = []
    for bank, index in enumerate(best['indices']):
        selected = banks[bank][index]
        layouts.append({'id': current['layouts'][bank]['id'], 'high': selected['high'], 'low': selected['low']})
    (OUTPUT / 'design.json').write_text(json.dumps({'layouts': layouts}, indent=2) + '\n')
    (OUTPUT / 'joint_report.json').write_text(json.dumps({'draws': len(seeds), 'best': best,
        'candidate_counts': [len(bank) for bank in banks], 'top_combinations': ranked[:10]}, indent=2) + '\n')
    print(json.dumps(best, indent=2), flush=True)


if __name__ == '__main__':
    main()
