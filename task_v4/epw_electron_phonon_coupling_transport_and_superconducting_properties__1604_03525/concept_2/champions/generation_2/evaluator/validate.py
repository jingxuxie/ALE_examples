import json
from pathlib import Path
import sys
import numpy as np
from scipy.linalg import eigh


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'participant' / 'workspace'))
from physics import laplacian, observables, score, validate


def main():
    checks = []
    hidden = ROOT / 'evaluator' / 'hidden'
    for item in json.loads((hidden / 'manifest.json').read_text()):
        with np.load(hidden / item['path'], allow_pickle=False) as archive:
            catalogue = dict(archive)
        source = catalogue['source']
        target = catalogue['target']
        state_count = len(catalogue['velocities'])
        for coefficients in catalogue['mixing']:
            weights = catalogue['channels'] @ coefficients
            matrix = laplacian(state_count, source, target, weights)
            degree, conductivity, dissipation = observables(matrix, catalogue['velocities'], catalogue['probes'])
            eigenvalues, eigenvectors = eigh(matrix)
            pseudoinverse_response = eigenvectors[:, 1:] @ ((eigenvectors[:, 1:].T @ catalogue['velocities']) / eigenvalues[1:, None])
            independent_conductivity = catalogue['velocities'].T @ pseudoinverse_response / state_count
            differences = catalogue['probes'][source] - catalogue['probes'][target]
            independent_dissipation = np.sum(weights[:, None] * differences ** 2, axis=0) / state_count
            assert np.max(np.abs(matrix.sum(axis=1))) < 1e-9
            assert eigenvalues[1] > 1e-7 and eigenvalues[0] > -1e-9
            assert np.allclose(independent_conductivity, conductivity, atol=1e-10, rtol=1e-9)
            assert np.allclose(independent_dissipation, dissipation, atol=1e-10, rtol=1e-10)
            assert np.all(degree > 0)
        expanded = dict(catalogue, budget=np.array(len(source)))
        truth = score(expanded, np.arange(len(source)), np.ones(len(source)))
        assert truth['score'] > 99.99999
        bad_outputs = [(np.arange(2), np.zeros(2)), (np.array([0, 0]), np.ones(2)),
                       (np.array([0]), np.array([np.nan])), (np.array([-1]), np.ones(1)),
                       (np.arange(len(source)), np.ones(len(source)))]
        for indices, multipliers in bad_outputs:
            try:
                validate(catalogue, indices, multipliers)
            except ValueError:
                pass
            else:
                raise AssertionError('invalid output accepted')
        checks.append({'case': item['name'], 'independent_eigen_and_edge_checks': True,
                       'identity_score': truth['score'], 'invalid_output_checks': len(bad_outputs)})
    report = {'valid': True, 'scope': 'independent Laplacian nullspace, PSD, inverse response, edge energy, and parser checks',
              'checks': checks, 'achievability_note': 'Identity uses all edges and does not establish budgeted achievability.'}
    (ROOT / 'adversary' / 'evaluator_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'valid': True, 'cases_checked': len(checks)}))


if __name__ == '__main__':
    main()
