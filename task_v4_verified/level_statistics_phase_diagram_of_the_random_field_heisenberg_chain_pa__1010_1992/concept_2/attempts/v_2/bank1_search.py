import json
import numpy as np
from search import Database, OUTPUT, SPEC, canonical
from enrich import final_rank
from validate import summarize


def utility(record):
    return (0.6 * np.mean(record['expected_family_score'])
            + 0.4 * record['expected_worst_score'] + 0.15 * record['probability_pass'])


def main():
    database = Database()
    training = json.loads((OUTPUT / 'final_training.json').read_text())
    seeds = training['seeds']
    previous_design = json.loads((OUTPUT / 'design.json').read_text())
    previous = json.loads((OUTPUT / 'robust_pairs.json').read_text())
    parents = []
    for record in sorted(previous[0], key=utility, reverse=True):
        order = tuple(record['high'])
        if order not in parents:
            parents.append(order)
        if len(parents) == 6:
            break
    generator = np.random.default_rng(8310961)
    candidates = set(parents)
    while len(candidates) < 180:
        order = list(parents[generator.integers(len(parents))])
        left, right = sorted(generator.choice(12, 2, replace=False))
        if generator.random() < 0.7:
            order[left], order[right] = order[right], order[left]
        else:
            order[left:right + 1] = reversed(order[left:right + 1])
        candidates.add(canonical(order))
    small_seeds = seeds[3:6]
    database.run([(0, order, 1.0, seed) for order in candidates for seed in small_seeds])
    lows = {tuple(record['low']) for record in previous[0]}
    lows = [order for order in lows if all((0, order, scale, seed) in database.data
            for scale in SPEC['scales'] for seed in seeds)]
    central_lows = [(order, database.values(0, order, small_seeds, [1.0])[0]) for order in lows]
    ranking = []
    for high in candidates:
        values = database.values(0, high, small_seeds, [1.0])[0]
        scores = []
        for low, low_values in central_lows:
            gap = np.abs(values[:, 0] - low_values[:, 0])
            separation = values[:, 1] - low_values[:, 1]
            scores.append(gap.mean() + 0.4 * gap.max() + 2 * max(0, 0.30 - separation.min()))
        ranking.append((min(scores), high))
    selected = [high for score, high in sorted(ranking)[:24]]
    middle_seeds = seeds[:6]
    database.run([(0, high, scale, seed) for high in selected for scale in SPEC['scales'] for seed in middle_seeds])
    ranking = []
    for high in selected:
        values = database.values(0, high, middle_seeds)
        scores = []
        for low in lows:
            low_values = database.values(0, low, middle_seeds)
            gap = np.abs(values[:, :, 0] - low_values[:, :, 0])
            separation = values[:, :, 1] - low_values[:, :, 1]
            scores.append(gap.mean(axis=1).max() + 0.2 * gap.max()
                          + 2 * max(0, 0.285 - separation.mean(axis=1).min())
                          + 2 * max(0, 0.25 - separation.min()))
        ranking.append((min(scores), high))
    selected = [high for score, high in sorted(ranking)[:8]]
    database.run([(0, high, scale, seed) for high in selected for scale in SPEC['scales'] for seed in seeds])
    final_rank(database, seeds, training['banks'])
    ranked = json.loads((OUTPUT / 'robust_pairs.json').read_text())[0]
    selected_pairs = sorted(ranked, key=utility, reverse=True)[:3] + [previous_design['layouts'][0]]
    test_seeds = np.random.default_rng(151298074).integers(100000, 2000000000, 40).tolist()
    database.run([(0, tuple(record[role]), scale, seed) for record in selected_pairs for role in ['high', 'low']
                  for scale in SPEC['scales'] for seed in test_seeds])
    reports = []
    for record in selected_pairs:
        high = database.values(0, record['high'], test_seeds)
        low = database.values(0, record['low'], test_seeds)
        summary = summarize(np.abs(high[:, :, 0] - low[:, :, 0]), high[:, :, 1] - low[:, :, 1], generator)
        score = (0.6 * np.mean(summary['expected_family_score']) + 0.4 * summary['expected_worst_score']
                 + 0.15 * (1 - summary['bootstrap_any_scale_failure']))
        summary.update({'utility': float(score), 'high': record['high'], 'low': record['low']})
        reports.append(summary)
    reports.sort(key=lambda record: -record['utility'])
    best = reports[0]
    previous_design['layouts'][0] = {'id': SPEC['banks'][0]['id'], 'high': best['high'], 'low': best['low']}
    (OUTPUT / 'design.json').write_text(json.dumps(previous_design, indent=2) + '\n')
    (OUTPUT / 'bank1_validation.json').write_text(json.dumps(reports, indent=2) + '\n')
    print('BANK 1 REFINEMENT', json.dumps(reports, indent=2), flush=True)


if __name__ == '__main__':
    main()
