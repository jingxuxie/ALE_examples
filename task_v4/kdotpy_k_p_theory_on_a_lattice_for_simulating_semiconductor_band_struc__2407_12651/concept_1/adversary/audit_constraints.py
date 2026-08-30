import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
from atlas import Atlas


def main():
    base = ROOT / 'evaluator' / 'hidden' / 'cases'
    random = np.random.default_rng(931341)
    rows = []
    for case in json.loads((base / 'manifest.json').read_text())['cases']:
        atlas = Atlas.load(base / case['directory'])
        selections = random.integers(0, atlas.candidates, size=(512, atlas.vertices))
        for vertex, choice in atlas.anchors.items():
            selections[:, vertex] = choice
        scores = atlas.evaluate_many(selections)
        rows.append({'case_id': case['id'], 'samples': len(selections),
                     'budget_feasible': int(np.count_nonzero(scores['cost'] <= atlas.budget)),
                     'topology_feasible': int(np.count_nonzero(scores['topology_error'] <= atlas.chern_tolerance)),
                     'jointly_feasible': int(np.count_nonzero(scores['feasible'])),
                     'nonzero_target_chern': atlas.targets.tolist()})
    destination = ROOT / 'adversary' / 'constraint_audit.json'
    destination.write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
