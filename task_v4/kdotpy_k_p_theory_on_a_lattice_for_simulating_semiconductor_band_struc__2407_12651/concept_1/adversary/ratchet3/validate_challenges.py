import argparse
import io
import json
import sys
import time
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'participant/workspace'))
sys.path.insert(0, str(ROOT / 'adversary'))
sys.path.insert(0, str(ROOT / 'adversary/headroom/submission'))
from atlas import Atlas
from relaxation import embed, formulate
from test_atlas import AtlasTests, independent_score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    arguments = parser.parse_args()
    arguments.output.resolve().relative_to(ROOT / 'adversary/ratchet3')
    started = time.monotonic()
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AtlasTests))
    assert result.wasSuccessful(), stream.getvalue()
    random = np.random.default_rng(121539)
    rows = []
    for case in json.loads((arguments.cases / 'manifest.json').read_text())['cases']:
        directory = arguments.cases / case['directory']
        metadata = json.loads((directory / 'case.json').read_text())
        with np.load(directory / 'arrays.npz', allow_pickle=False) as archive:
            arrays = {name: archive[name] for name in archive.files}
        atlas = Atlas(metadata, arrays)
        assert atlas.candidates == 4 and atlas.rank == 2 and atlas.scenarios == 4
        maximum_error = 0.0
        for choices in [atlas.seed, arrays['baseline_choices'], random.integers(0, 4, atlas.vertices)]:
            expected, feasible, chern = independent_score(metadata, arrays, choices)
            score = atlas.score(choices)
            maximum_error = max(maximum_error, abs(expected - score['objective']))
            assert maximum_error < 1e-9 and feasible == score['feasible']
            np.testing.assert_allclose(chern, score['chern'], atol=1e-9)
        transforms = 3 * np.eye(2) + 0.2 * (random.normal(size=arrays['frames'].shape[:3] + (2, 2)) + 1j * random.normal(size=arrays['frames'].shape[:3] + (2, 2)))
        transformed = Atlas(metadata, dict(arrays, frames=arrays['frames'] @ transforms))
        original_score = atlas.score(arrays['baseline_choices'])
        gauge_score = transformed.score(arrays['baseline_choices'])
        assert abs(gauge_score['objective'] - original_score['objective']) < 1e-10
        assert gauge_score['feasible'] == original_score['feasible']
        formulation = formulate(atlas)
        embedding = embed(atlas, formulation, arrays['baseline_choices'])
        equality_error = float(np.max(np.abs(formulation['equalities'] @ embedding - formulation['equality_rhs'])))
        inequality_error = float(np.max(formulation['inequalities'] @ embedding - formulation['inequality_rhs']))
        assert equality_error < 1e-9 and inequality_error < 1e-8
        assert np.min(embedding) >= 0 and np.max(embedding - formulation['upper']) < 1e-9
        assert abs(np.dot(formulation['objective'], embedding) - original_score['objective']) < 1e-9
        rows.append({'case_id': case['id'], 'passed': True, 'independent_objective_error': maximum_error,
                     'gauge_objective_error': abs(gauge_score['objective'] - original_score['objective']),
                     'baseline_lp_equality_error': equality_error, 'baseline_lp_inequality_error': inequality_error})
    report = {'passed': True, 'existing_tests_passed': result.testsRun, 'independent_small_enumeration': 64,
              'rows': rows, 'runtime_seconds': time.monotonic() - started,
              'checks': ['independent Wilson-loop scorer', 'arbitrary nonsingular candidate frame changes',
                         'four candidates, four scenarios, rank two', 'valid baseline LP embeddings',
                         'original common ambient unitary and exhaustive-enumeration regression tests']}
    arguments.output.write_text(json.dumps(report, indent=2) + '\n')
    arguments.output.with_suffix('.log').write_text(stream.getvalue())
    print(json.dumps({'passed': True, 'cases': len(rows), 'seconds': report['runtime_seconds']}))


if __name__ == '__main__':
    main()
