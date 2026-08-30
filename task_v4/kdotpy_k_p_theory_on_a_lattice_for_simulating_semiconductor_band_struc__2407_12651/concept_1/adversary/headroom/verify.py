from fractions import Fraction
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
sys.path.insert(0, str(HERE / 'submission'))
from atlas import Atlas
from relaxation import embed, formulate
from certificate import exact_box_dual


def read_certificate(path):
    with np.load(path, allow_pickle=False) as archive:
        saved = {name: archive[name] for name in archive.files}
    formulation = {name: saved[name] for name in ['objective', 'upper', 'equality_rhs', 'inequality_rhs']}
    for name in ['equalities', 'inequalities']:
        formulation[name] = coo_matrix((saved[name + '_data'], (saved[name + '_row'], saved[name + '_column'])),
                                       shape=tuple(saved[name + '_shape'])).tocsr()
    return formulation, saved['equality_dual'], saved['inequality_dual']


def independent_fraction_bound(formulation, equality_dual, inequality_dual):
    cache = {}

    def rational(value):
        value = float(value)
        if value not in cache:
            cache[value] = Fraction.from_float(value)
        return cache[value]

    reduced = [rational(value) for value in formulation['objective']]
    constant = Fraction(0)
    for matrix, rhs, dual in [(formulation['equalities'], formulation['equality_rhs'], equality_dual),
                             (formulation['inequalities'], formulation['inequality_rhs'], np.minimum(inequality_dual, 0))]:
        multipliers = [rational(value) for value in dual]
        constant += sum((rational(value) * multiplier for value, multiplier in zip(rhs, multipliers)), Fraction(0))
        entries = matrix.tocoo()
        for row, column, value in zip(entries.row, entries.col, entries.data):
            reduced[column] -= rational(value) * multipliers[row]
    return constant + sum((min(value, Fraction(0)) * rational(upper) for value, upper in zip(reduced, formulation['upper'])), Fraction(0))


def main():
    started = time.monotonic()
    report = json.loads((HERE / 'bounds.json').read_text())
    frozen_path = ROOT / 'frozen_manifest.json'
    frozen = json.loads(frozen_path.read_text())
    for filename, expected in frozen['sha256'].items():
        assert hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() == expected
    random = np.random.default_rng(514190)
    rows = []
    for case in report['cases']:
        directory = ROOT / 'evaluator' / 'hidden' / 'cases' / case['case_id']
        atlas = Atlas.load(directory)
        saved, equality_dual, inequality_dual = read_certificate(HERE / case['certificate'])
        rebuilt = formulate(atlas)
        for name in ['objective', 'upper', 'equality_rhs', 'inequality_rhs']:
            np.testing.assert_array_equal(saved[name], rebuilt[name])
        for name in ['equalities', 'inequalities']:
            assert (saved[name] != rebuilt[name]).nnz == 0
        certificate = exact_box_dual(saved, equality_dual, inequality_dual)
        assert certificate['exact_lp_bound_numerator'] == case['exact_lp_bound_numerator']
        assert certificate['exact_lp_bound_denominator'] == case['exact_lp_bound_denominator']
        maximum_equality_error, maximum_objective_error = 0.0, 0.0
        for trial in range(16):
            choices = random.integers(0, atlas.candidates, atlas.vertices)
            for vertex, choice in atlas.anchors.items():
                choices[vertex] = choice
            vector = embed(atlas, rebuilt, choices)
            maximum_equality_error = max(maximum_equality_error, float(np.max(np.abs(rebuilt['equalities'] @ vector - rebuilt['equality_rhs']))))
            maximum_objective_error = max(maximum_objective_error, abs(float(rebuilt['objective'] @ vector) - atlas.score(choices)['objective']))
        assert maximum_equality_error < 1e-10 and maximum_objective_error < 1e-9
        fraction_verified = None
        if case['family'] == 'anisotropic_warping':
            independent = independent_fraction_bound(saved, equality_dual, inequality_dual)
            expected = Fraction(int(case['exact_lp_bound_numerator']), int(case['exact_lp_bound_denominator']))
            assert independent == expected
            fraction_verified = True
        rows.append({'case_id': case['case_id'], 'rebuilt_model_identical': True, 'exact_certificate_verified': True,
                     'independent_fraction_crosscheck': fraction_verified,
                     'random_embedding_tests': 16, 'maximum_equality_error': maximum_equality_error,
                     'maximum_objective_error': maximum_objective_error})
    result = {'passed': True, 'cases': rows, 'frozen_files_unchanged': len(frozen['sha256']),
              'frozen_manifest_sha256': hashlib.sha256(frozen_path.read_bytes()).hexdigest(),
              'elapsed_seconds': time.monotonic() - started,
              'caveat': 'Exact certificates are for the reconstructed floating-coefficient LP; a 1e-9 downward guard covers scorer accumulation differences observed in validation, but this is not an interval proof of every floating-point primitive.'}
    (HERE / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    status = {'status': 'frozen_targets_excluded_by_verified_relaxation_bounds',
              'passing_implementation_found': False, 'fresh_agents_launched': 0, 'fresh_attempts_inspected': False,
              'frozen_files_changed': False, 'required_overall_gain': 0.12, 'required_worst_family_gain': 0.08,
              'overall_gain_upper_bound': report['overall_upper_gain_bound'],
              'worst_family_gain_upper_bound': report['worst_family_upper_gain_bound'],
              'family_gain_upper_bounds': report['family_upper_gain_bounds'],
              'numerical_seconds': json.loads((HERE / 'pilot.json').read_text())['elapsed_seconds'] + report['elapsed_seconds'] + result['elapsed_seconds'],
              'solver_replay': 'Not run: no passing candidate was found, and the resource-unconstrained relaxation already excludes the thresholds.',
              'conservative_conclusion': 'Strong independently checked evidence of invalid frozen acceptance targets, not evidence of solver hardness. Keep the package unchanged while the fresh run is active; review target validity before interpreting its outcome.',
              'formal_scope': result['caveat'], 'evidence': ['bounds.json', 'verification.json', 'certificates/']}
    (HERE / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status, indent=2), flush=True)


if __name__ == '__main__':
    main()
