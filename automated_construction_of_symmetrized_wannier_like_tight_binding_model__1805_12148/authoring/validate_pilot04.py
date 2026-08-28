import importlib.util
import json
import pathlib
import time

import numpy as np
from scipy.linalg import eigh


ROOT = pathlib.Path(__file__).resolve().parents[1]
PILOT = ROOT / 'pilots/04_effective_physics'
BASE = PILOT / 'private/reference/base'
specification = importlib.util.spec_from_file_location('reference_upstream', PILOT / 'private/reference/upstream.py')
upstream = importlib.util.module_from_spec(specification)
specification.loader.exec_module(upstream)


def polynomial(reference, vector):
    return reference['H0'] + np.einsum('ija,a->ij', reference['H1'], vector) + np.einsum('ijab,a,b->ij', reference['H2'], vector, vector) + np.einsum('ijabc,a,b,c->ij', reference['H3'], vector, vector, vector)


def exact_effective(case, vector):
    hamiltonian = np.diag(case['energy']).astype(complex)
    hamiltonian += (2 * 3.809982208629016 / 0.52917721067) * np.einsum('a,aij->ij', vector, case['momentum'])
    hamiltonian += 3.809982208629016 * np.dot(vector, vector) * np.eye(len(hamiltonian))
    energies, vectors = eigh(hamiltonian, check_finite=False)
    selected = case['target']
    overlap = vectors[np.ix_(selected, selected)]
    left, singular, right = np.linalg.svd(overlap)
    polar = left @ right
    return (polar * energies[selected]) @ polar.conj().T


def main():
    rows = []
    for input_path in sorted(BASE.glob('*_input.npz')):
        name = input_path.name.replace('_input.npz', '')
        reference_path = BASE / (name + '_reference.npz')
        if not reference_path.exists():
            continue
        case = dict(np.load(input_path))
        reference = dict(np.load(reference_path))
        started = time.monotonic()
        direction = np.array([0.31, -0.53, 0.79])
        direction /= np.linalg.norm(direction)
        differences = []
        for magnitude in [0.002, 0.001, 0.0005]:
            vector = magnitude * direction
            difference = np.linalg.norm(exact_effective(case, vector) - polynomial(reference, vector))
            differences.append({'q_norm': magnitude, 'matrix_error_ev': float(difference)})
        item = {'material': name, 'bands': len(case['energy']), 'target': case['target'].tolist(), 'gauge_residual': upstream.gauge_residual(case, reference['U']), 'exact_spectral_checks': differences, 'error_ratios': [differences[index]['matrix_error_ev'] / max(differences[index + 1]['matrix_error_ev'], 1e-16) for index in range(2)], 'seconds': time.monotonic() - started}
        if name == 'bulk_bi2se3':
            zeeman = upstream.rotate_basis(reference['G'], reference['U'])[:, :, 2]
            expected = np.sort(np.array([-7.8904 - 13.0138, 7.8904 + 13.0138, -7.8904 + 13.0138, 7.8904 - 13.0138]) / 2)
            actual = np.linalg.eigvalsh(zeeman)
            item['author_printed_zeeman_eigenvalues'] = expected.tolist()
            item['raw_reference_zeeman_eigenvalues'] = actual.tolist()
            item['author_printed_max_difference'] = float(np.max(np.abs(expected - actual)))
        rows.append(item)
        print(json.dumps(item), flush=True)
    output = ROOT / 'authoring/pilot04_independent_validation.json'
    output.write_text(json.dumps({'source': 'independent finite-q full-space diagonalization and polar-gauge reduction, plus upstream printed g-factors', 'materials': rows}, indent=2))


if __name__ == '__main__':
    main()
