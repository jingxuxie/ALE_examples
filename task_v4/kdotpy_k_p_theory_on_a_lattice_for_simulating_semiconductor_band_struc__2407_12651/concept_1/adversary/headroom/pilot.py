import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
sys.path.insert(0, str(HERE / 'submission'))
from atlas import Atlas
from relaxation import embed, formulate, relaxation


def main():
    started = time.monotonic()
    atlas = Atlas.load(ROOT / 'evaluator' / 'hidden' / 'cases' / 'gap_hotspots_0')
    with np.load(ROOT / 'evaluator' / 'hidden' / 'cases' / 'gap_hotspots_0' / 'arrays.npz', allow_pickle=False) as archive:
        baseline = archive['baseline_choices']
    formulation = formulate(atlas)
    vector = embed(atlas, formulation, baseline)
    consistency = float(np.max(np.abs(formulation['equalities'] @ vector - formulation['equality_rhs'])))
    inequality_error = float(np.max(formulation['inequalities'] @ vector - formulation['inequality_rhs']))
    objective_error = float(abs(formulation['objective'] @ vector - atlas.score(baseline)['objective']))
    assert consistency < 1e-10 and inequality_error < 1e-8 and objective_error < 1e-10
    probabilities, report = relaxation(atlas, seconds=25)
    output = {'embedding_consistency_error': consistency, 'embedding_inequality_error': inequality_error,
              'embedding_objective_error': objective_error, 'relaxation': report,
              'elapsed_seconds': time.monotonic() - started}
    if probabilities is not None:
        output['rounded_score'] = atlas.score(probabilities.argmax(axis=1))
    (HERE / 'pilot.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(output, indent=2), flush=True)


if __name__ == '__main__':
    main()
