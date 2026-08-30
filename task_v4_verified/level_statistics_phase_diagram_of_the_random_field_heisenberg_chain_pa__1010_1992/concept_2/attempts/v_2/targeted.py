import json
import numpy as np
from search import Database, OUTPUT, SPEC, FIELDS, canonical
from enrich import final_rank


def main():
    database = Database()
    source = json.loads((OUTPUT / 'final_training.json').read_text())
    seeds = source['seeds']
    parents, candidates, jobs = [], [], []
    for bank, selection in enumerate(source['banks']):
        scored = []
        for high in selection['high']:
            values = database.values(bank, high, seeds)
            scored.append((values[:, :, 0].mean() + 2 * max(0, 0.43 - values[:, :, 1].min()), tuple(high)))
        selected = [high for score, high in sorted(scored)[:8]]
        sorted_order = np.argsort(FIELDS[bank])
        selected += [canonical(sorted_order), canonical(sorted_order[[0, 2, 4, 6, 8, 10, 11, 9, 7, 5, 3, 1]])]
        parents.append(list(dict.fromkeys(selected)))
        jobs += [(bank, high, scale, seed) for high in parents[-1] for scale in SPEC['scales'] for seed in seeds]
        records = []
        for high in parents[-1]:
            for start in range(12):
                for length in range(2, 11):
                    order = list(high[start:] + high[:start])
                    order[:length] = reversed(order[:length])
                    low = canonical(order)
                    records.append((high, low))
                    jobs.append((bank, low, 1.0, None))
        candidates.append(sorted(set(records)))
    database.run(jobs)
    filtered, jobs = [], []
    for bank, records in enumerate(candidates):
        keep = []
        for high, low in records:
            high_values = database.data[(bank, high, 1.0, None)]
            low_values = database.data[(bank, low, 1.0, None)]
            if high_values[1] - low_values[1] < 0.285 or abs(high_values[0] - low_values[0]) > 0.065:
                continue
            keep.append((high, low))
            jobs += [(bank, low, 1.0, seed) for seed in SPEC['public_seeds']]
        filtered.append(keep)
        print('TWO-OPT BANK', bank + 1, 'central candidates', len(keep), flush=True)
    database.run(jobs)
    public_candidates, jobs = [], []
    for bank, records in enumerate(filtered):
        keep = []
        for high, low in records:
            high_values = database.values(bank, high, SPEC['public_seeds'], [1.0])[0]
            low_values = database.values(bank, low, SPEC['public_seeds'], [1.0])[0]
            difference = np.abs(high_values[:, 0] - low_values[:, 0])
            separation = high_values[:, 1] - low_values[:, 1]
            if difference.mean() > 0.03 or separation.mean() < 0.295 or separation.min() < 0.265:
                continue
            keep.append((high, low))
            jobs += [(bank, low, scale, seed) for scale in SPEC['scales'] for seed in SPEC['public_seeds']]
        public_candidates.append(keep)
        print('TWO-OPT BANK', bank + 1, 'public candidates', len(keep), flush=True)
    database.run(jobs)
    previous = json.loads((OUTPUT / 'robust_pairs.json').read_text())
    chosen, jobs = [], []
    for bank, records in enumerate(public_candidates):
        ranked = []
        for high, low in records:
            high_values = database.values(bank, high, SPEC['public_seeds'])
            low_values = database.values(bank, low, SPEC['public_seeds'])
            gap = np.abs(high_values[:, :, 0] - low_values[:, :, 0])
            separation = high_values[:, :, 1] - low_values[:, :, 1]
            score = (gap.mean(axis=1).max() + 0.2 * gap.max()
                     + 2 * max(0, 0.285 - separation.mean(axis=1).min()))
            ranked.append((float(score), high, low))
        highs, lows = set(), set()
        for score, high, low in sorted(ranked):
            if len(lows | {low}) <= 12:
                highs.add(high)
                lows.add(low)
        for record in previous[bank][:5]:
            highs.add(tuple(record['high']))
            lows.add(tuple(record['low']))
        chosen.append({'high': sorted(highs), 'low': sorted(lows)})
        jobs += [(bank, order, scale, seed) for order in highs | lows for scale in SPEC['scales'] for seed in seeds]
    database.run(jobs)
    (OUTPUT / 'targeted_training.json').write_text(json.dumps({'banks': chosen, 'seeds': seeds}))
    final_rank(database, seeds, chosen)


if __name__ == '__main__':
    from low_search import main as improve_low
    improve_low()
    main()
