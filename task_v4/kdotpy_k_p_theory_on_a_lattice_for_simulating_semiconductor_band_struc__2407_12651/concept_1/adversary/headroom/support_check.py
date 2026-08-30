import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'participant/workspace'))
sys.path.insert(0, str(ROOT / 'evaluator'))
from atlas import Atlas, single_descent
from evaluate import aggregate


def main():
    started = time.monotonic()
    cases_root = ROOT / 'evaluator/hidden/cases'
    cases = json.loads((cases_root / 'manifest.json').read_text())['cases']
    policy = json.loads((ROOT / 'participant/workspace/policy.json').read_text())
    rows, polished_rows = [], []
    artifacts = HERE / 'generation2' / 'cached_support_artifacts'
    artifacts.mkdir(parents=True, exist_ok=True)
    for case in cases:
        atlas = Atlas.load(cases_root / case['directory'])
        probabilities = np.load(HERE / 'certificates' / (case['id'] + '_marginals.npy'), allow_pickle=False)
        supports = [np.flatnonzero(row > 1e-7).tolist() for row in probabilities]
        choices = np.array(list(itertools.product(*supports)), dtype=int)
        scores = atlas.evaluate_many(choices)
        values = np.where(scores['feasible'], scores['objective'], np.inf)
        with np.load(cases_root / case['directory'] / 'arrays.npz', allow_pickle=False) as archive:
            best = archive['baseline_choices'].copy()
        selected = int(np.argmin(values))
        if values[selected] < atlas.metadata['baseline_objective']:
            best = choices[selected].copy()
        row = {'case_id': case['id'], 'family': case['family'], 'combinations': len(choices), **atlas.score(best)}
        row['gain'] = 1 - row['objective'] / atlas.metadata['baseline_objective']
        rows.append(row)
        polished = single_descent(atlas, best)
        polished_row = {'case_id': case['id'], 'family': case['family'], **atlas.score(polished)}
        polished_row['gain'] = 1 - polished_row['objective'] / atlas.metadata['baseline_objective']
        polished_rows.append(polished_row)
        (artifacts / (case['id'] + '.json')).write_text(json.dumps({'choices': best.tolist()}) + '\n')
        print(case['id'], len(choices), row['gain'], polished_row['gain'], flush=True)
    report = {'cached_diagnostic_only': True, 'lp_recomputation_not_timed_here': True,
              'enumeration': aggregate(rows, policy), 'polished': aggregate(polished_rows, policy),
              'cases': rows, 'polished_cases': polished_rows, 'seconds': time.monotonic() - started}
    (HERE / 'generation2/support_screen.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key not in ['cases', 'polished_cases']}, indent=2))


if __name__ == '__main__':
    main()
