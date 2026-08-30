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


def support_fringe(atlas, probabilities, baseline):
    supports = [np.flatnonzero(row > 1e-7).tolist() for row in probabilities]
    core = np.array(list(itertools.product(*supports)), dtype=int)
    mutable = np.array([vertex for vertex in range(atlas.vertices) if vertex not in atlas.anchors])
    moving = np.repeat(mutable, atlas.candidates)
    alternatives = np.tile(np.arange(atlas.candidates), len(mutable))
    best = baseline.copy()
    value = atlas.score(best)['objective']
    evaluated = 0
    for selection in core:
        for first in range(0, len(moving), 128):
            vertices = moving[first:first + 128]
            candidates = alternatives[first:first + 128]
            neighbors = np.tile(selection, (len(vertices), 1))
            neighbors[np.arange(len(vertices)), vertices] = candidates
            results = atlas.evaluate_many(neighbors)
            values = np.where(results['feasible'], results['objective'], np.inf)
            selected = int(np.argmin(values))
            if values[selected] < value:
                best, value = neighbors[selected].copy(), float(values[selected])
            evaluated += len(neighbors)
    return single_descent(atlas, best), evaluated


def main():
    started = time.monotonic()
    cases_root = ROOT / 'evaluator/hidden/cases'
    cases = json.loads((cases_root / 'manifest.json').read_text())['cases']
    policy = json.loads((ROOT / 'participant/workspace/policy.json').read_text())
    rows = []
    destination = HERE / 'generation2' / 'cached_fringe_artifacts'
    destination.mkdir(parents=True, exist_ok=True)
    for case in cases:
        case_started = time.monotonic()
        atlas = Atlas.load(cases_root / case['directory'])
        probabilities = np.load(HERE / 'certificates' / (case['id'] + '_marginals.npy'), allow_pickle=False)
        with np.load(cases_root / case['directory'] / 'arrays.npz', allow_pickle=False) as archive:
            baseline = archive['baseline_choices']
        choices, count = support_fringe(atlas, probabilities, baseline)
        row = {'case_id': case['id'], 'family': case['family'], 'enumerated_candidates': count,
               'seconds_excluding_lp': time.monotonic() - case_started, **atlas.score(choices)}
        row['gain'] = 1 - row['objective'] / atlas.metadata['baseline_objective']
        rows.append(row)
        (destination / (case['id'] + '.json')).write_text(json.dumps({'choices': choices.tolist()}) + '\n')
        print(case['id'], row['gain'], row['seconds_excluding_lp'], flush=True)
    report = {'cached_diagnostic_only': True, 'lp_recomputation_not_timed_here': True,
              'summary': aggregate(rows, policy), 'cases': rows, 'seconds': time.monotonic() - started}
    (HERE / 'generation2/fringe_screen.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['summary'], indent=2))


if __name__ == '__main__':
    main()
