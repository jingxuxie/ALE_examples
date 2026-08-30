import argparse
import json
import numpy as np
from search import Database, OUTPUT, SPEC


def summarize(difference, separation, generator):
    draws = generator.integers(0, difference.shape[1], (40000, 5))
    sampled_difference = difference[:, draws]
    sampled_separation = separation[:, draws]
    failures = ((sampled_difference.mean(axis=2) > 0.02)
                | (sampled_difference.max(axis=2) > 0.045)
                | (sampled_separation.mean(axis=2) < 0.28)
                | (sampled_separation.min(axis=2) < 0.24))
    margins = np.array([0.02 / np.maximum(sampled_difference.mean(axis=2), 1e-12),
                        0.045 / np.maximum(sampled_difference.max(axis=2), 1e-12),
                        sampled_separation.mean(axis=2) / 0.28,
                        sampled_separation.min(axis=2) / 0.24])
    scores = np.minimum(margins.min(axis=0), 1)
    return {
        'mean_abs_r_difference': difference.mean(axis=1).tolist(),
        'std_abs_r_difference': difference.std(axis=1).tolist(),
        'max_abs_r_difference': difference.max(axis=1).tolist(),
        'mean_f_separation': separation.mean(axis=1).tolist(),
        'min_f_separation': separation.min(axis=1).tolist(),
        'bootstrap_five_draw_failure_by_scale': failures.mean(axis=1).tolist(),
        'bootstrap_any_scale_failure': float(failures.any(axis=0).mean()),
        'expected_family_score': scores.mean(axis=1).tolist(),
        'expected_worst_score': float(scores.min(axis=0).mean()),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--draws', type=int, default=80)
    parser.add_argument('--seed', type=int, default=8302974)
    parser.add_argument('--candidates', type=int, default=1)
    parser.add_argument('--output', default='validation.json')
    parser.add_argument('--select', action='store_true')
    args = parser.parse_args()
    generator = np.random.default_rng(args.seed)
    seeds = generator.integers(100000, 2000000000, args.draws).tolist()
    database = Database()
    if args.candidates == 1:
        design = json.loads((OUTPUT / 'design.json').read_text())
        pairs = [[layout] for layout in design['layouts']]
    else:
        ranked = json.loads((OUTPUT / 'robust_pairs.json').read_text())
        pairs = []
        for records in ranked:
            def utility(record):
                return (0.6 * np.mean(record['expected_family_score'])
                        + 0.4 * record['expected_worst_score'] + 0.15 * record['probability_pass'])
            ordered = sorted(records, key=utility, reverse=True)
            selected = [record for record in ordered if record['public_pass']][:2]
            for record in ordered:
                if record not in selected and len(selected) < args.candidates:
                    selected.append(record)
            pairs.append(selected)
    jobs = [(bank, tuple(record[role]), scale, seed) for bank, records in enumerate(pairs)
            for record in records for role in ('high', 'low') for scale in SPEC['scales'] for seed in seeds]
    database.run(jobs)
    reports, layouts = [], []
    for bank, records in enumerate(pairs):
        scores = []
        for record in records:
            high = database.values(bank, record['high'], seeds)
            low = database.values(bank, record['low'], seeds)
            difference = np.abs(high[:, :, 0] - low[:, :, 0])
            separation = high[:, :, 1] - low[:, :, 1]
            summary = summarize(difference, separation, generator)
            summary.update({'high': record['high'], 'low': record['low'], 'bank': SPEC['banks'][bank]['id']})
            public_high = database.values(bank, record['high'], SPEC['public_seeds'])
            public_low = database.values(bank, record['low'], SPEC['public_seeds'])
            public_difference = np.abs(public_high[:, :, 0] - public_low[:, :, 0])
            public_separation = public_high[:, :, 1] - public_low[:, :, 1]
            public_margin = min(0.02 / max(public_difference.mean(axis=1).max(), 1e-12),
                                0.045 / max(public_difference.max(), 1e-12),
                                public_separation.mean(axis=1).min() / 0.28,
                                public_separation.min() / 0.24)
            summary['public_pass'] = bool(public_margin >= 1)
            score = (-0.6 * np.mean(summary['expected_family_score'])
                     - 0.4 * summary['expected_worst_score']
                     - 0.15 * (1 - summary['bootstrap_any_scale_failure'])
                     + 0.03 * max(0, 1 - public_margin))
            scores.append((score, summary))
        scores.sort(key=lambda item: item[0])
        reports.append([record for score, record in scores])
        print(json.dumps({'bank': bank + 1, 'results': reports[-1]}, indent=2), flush=True)
        best = scores[0][1]
        layouts.append({'id': SPEC['banks'][bank]['id'], 'high': best['high'], 'low': best['low']})
    (OUTPUT / args.output).write_text(json.dumps({'seeds': seeds, 'reports': reports}, indent=2) + '\n')
    if args.select:
        (OUTPUT / 'design.json').write_text(json.dumps({'layouts': layouts}, indent=2) + '\n')


if __name__ == '__main__':
    main()
