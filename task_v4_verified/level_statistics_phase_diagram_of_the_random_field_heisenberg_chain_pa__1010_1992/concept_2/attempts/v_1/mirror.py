import concurrent.futures
import json

from search import FIELDS, ROOT, SPEC, canonical, evaluate, key, load_cache, np
from stress import summarize


def main():
    cache = load_cache()
    design = json.loads((ROOT / 'design.json').read_text())
    layouts = {layout['id']: layout for layout in design['layouts']}
    seeds = list(range(910000, 910020)) + list(range(20260828, 20260834))
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        for bank in [1, 0, 2]:
            identity = SPEC['banks'][bank]['id']
            layout = layouts[identity]
            sorted_order = np.argsort(FIELDS[bank]).tolist()
            mapping = dict(zip(sorted_order, reversed(sorted_order)))
            highs = [tuple(layout['high']), canonical([mapping[index] for index in layout['high']])]
            lows = [tuple(layout['low']), canonical([mapping[index] for index in layout['low']])]
            evaluate([key(bank, order, scale, seed) for order in set(highs + lows)
                      for scale in SPEC['scales'] for seed in seeds + SPEC['public_seeds']], cache, pool)
            results = [summarize(bank, high, low, seeds, cache) for high in highs for low in lows]
            results = [result for result in results if result['public_passed']]
            results.sort(key=lambda result: (-result['empirical_pass_probability'], result['risk']))
            best = results[0]
            print('MIRROR', identity, json.dumps(best), flush=True)
            layout['high'] = best['high']
            layout['low'] = best['low']
            (ROOT / f'mirror_{bank + 1}.json').write_text(json.dumps(results, indent=2) + '\n')
            (ROOT / 'design.json').write_text(json.dumps(design, indent=2) + '\n')


if __name__ == '__main__':
    main()
