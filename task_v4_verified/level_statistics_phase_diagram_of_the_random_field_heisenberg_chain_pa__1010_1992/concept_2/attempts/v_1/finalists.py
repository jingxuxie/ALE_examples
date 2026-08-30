import concurrent.futures
import json

from search import ROOT, SPEC, evaluate, key, load_cache
from stress import summarize


cache = load_cache()
design = json.loads((ROOT / 'design.json').read_text())
layouts = {layout['id']: layout for layout in design['layouts']}
seeds = list(range(910000, 910020)) + list(range(20260828, 20260834)) + list(range(950000, 950040))
with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
    for bank in [0, 1, 2]:
        identity = SPEC['banks'][bank]['id']
        records = json.loads((ROOT / f'stress_{bank + 1}_910000_20.json').read_text())
        candidates = [record for record in records if record['public_passed']][:3]
        candidates.append(layouts[identity])
        orders = {tuple(pair[side]) for pair in candidates for side in ['high', 'low']}
        evaluate([key(bank, order, scale, seed) for order in orders for scale in SPEC['scales'] for seed in seeds], cache, pool)
        results = [summarize(bank, tuple(pair['high']), tuple(pair['low']), seeds, cache) for pair in candidates]
        results.sort(key=lambda result: (-(0.7 * result['mean_bootstrap_core_score'] + 0.3 * result['mean_bootstrap_worst_score']),
                                         -result['empirical_pass_probability']))
        best = results[0]
        print('FINALIST', identity, json.dumps(best), flush=True)
        layouts[identity]['high'] = best['high']
        layouts[identity]['low'] = best['low']
        (ROOT / f'finalists_{bank + 1}.json').write_text(json.dumps(results, indent=2) + '\n')
        (ROOT / 'design.json').write_text(json.dumps(design, indent=2) + '\n')
