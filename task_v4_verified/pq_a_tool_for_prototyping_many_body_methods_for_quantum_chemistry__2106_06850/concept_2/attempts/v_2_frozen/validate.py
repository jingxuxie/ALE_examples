import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np
from scipy.linalg import expm
from scipy.optimize import root


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else 'submission.json')
    data = json.loads(path.read_text())
    interaction = np.array(data['pair_matrix'])
    epsilon = np.array(data['orbital_energies'])
    submitted = np.array(data['amplitudes'])
    pairs = list(itertools.combinations(range(6), 2))
    annihilation = np.zeros((6, 64, 64))
    for orbital in range(6):
        for bits in range(64):
            if bits & (1 << orbital):
                annihilation[orbital, bits ^ (1 << orbital), bits] = (-1)**((bits & ((1 << orbital) - 1)).bit_count())
    creation = annihilation.transpose(0, 2, 1)
    sector = np.array([bits for bits in range(64) if bits.bit_count() == 3])
    projection = np.eye(64)[:, sector]
    reference = np.eye(20)[:, 0]
    onebody = np.array([[projection.T @ creation[first] @ annihilation[second] @ projection
                         for second in range(6)] for first in range(6)])
    tensor = np.zeros((6, 6, 6, 6))
    two_body = np.zeros((64, 64))
    for row, (first, second) in enumerate(pairs):
        for column, (third, fourth) in enumerate(pairs):
            value = interaction[row, column]
            tensor[first, second, third, fourth] = value
            tensor[second, first, third, fourth] = -value
            tensor[first, second, fourth, third] = -value
            tensor[second, first, fourth, third] = value
            two_body += value * creation[first] @ creation[second] @ annihilation[fourth] @ annihilation[third]
    one_electron = np.diag(epsilon) - sum(tensor[:, occupied, :, occupied] for occupied in range(3))
    hamiltonian = np.einsum('pq,pqij->ij', one_electron, onebody) + projection.T @ two_body @ projection
    base = np.einsum('pq,pqij->ij', np.diag(epsilon), onebody)
    generators = []
    targets = []
    for rank in (1, 2):
        for holes in itertools.combinations(range(3), rank):
            for particles in itertools.combinations(range(3, 6), rank):
                operator = np.eye(64)
                for occupied in holes:
                    operator = annihilation[occupied] @ operator
                for virtual in reversed(particles):
                    operator = creation[virtual] @ operator
                generator = projection.T @ operator @ projection
                target = np.argmax(np.abs(generator[:, 0]))
                generator *= generator[target, 0]
                generators.append(generator)
                targets.append(target)
    generators = np.array(generators)
    targets = np.array(targets)

    def equations(matrix, amplitudes):
        cluster = np.einsum('k,kij->ij', amplitudes, generators)
        positive = expm(cluster)
        negative = expm(-cluster)
        transformed = negative @ matrix @ positive
        column = transformed[:, 0]
        jacobian = transformed[np.ix_(targets, targets)] - np.einsum('kij,j->ik', generators, column)[targets]
        return column[targets], jacobian, transformed, positive, negative

    residual, jacobian, transformed, positive, negative = equations(hamiltonian, submitted)
    multipliers = np.linalg.solve(jacobian.T, -transformed[0, targets])
    row = reference.copy()
    row[targets] = multipliers
    left = row @ negative
    right = positive[:, 0]
    density = np.einsum('i,pqij,j->pq', left, onebody, right)
    occupations, orbitals = np.linalg.eigh((density + density.T) / 2)
    exact_energies, exact_states = np.linalg.eigh(hamiltonian)
    exact = exact_states[:, 0]
    normalized = right / np.linalg.norm(right)
    exact_density = np.einsum('i,pqij,j->pq', exact, onebody, exact)
    right_density = np.einsum('i,pqij,j->pq', normalized, onebody, normalized)
    hessians = []
    for imaginary in (False, True):
        rotations = [1j * (generator + generator.T) if imaginary else generator - generator.T for generator in generators[:9]]
        hessian = np.empty((9, 9))
        for row_index, row_rotation in enumerate(rotations):
            for column_index, column_rotation in enumerate(rotations):
                curvature = (hamiltonian @ (row_rotation @ column_rotation + column_rotation @ row_rotation) / 2
                             + (row_rotation @ column_rotation + column_rotation @ row_rotation) @ hamiltonian / 2
                             - row_rotation @ hamiltonian @ column_rotation - column_rotation @ hamiltonian @ row_rotation)
                hessian[row_index, column_index] = curvature[0, 0].real
        hessians.append(float(np.linalg.eigvalsh(hessian)[0]))
    report = {
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'artifact_bytes': path.stat().st_size,
        'pair_max': float(np.max(np.abs(interaction))),
        'pair_norm': float(np.linalg.norm(interaction)),
        'pair_symmetry': float(np.max(np.abs(interaction - interaction.T))),
        'hamiltonian_hermiticity': float(np.max(np.abs(hamiltonian - hamiltonian.T))),
        'fock_error': float(np.max(np.abs(one_electron + sum(tensor[:, occupied, :, occupied] for occupied in range(3)) - np.diag(epsilon)))),
        'reference_gradient': float(np.max(np.abs(hamiltonian[targets[:9], 0]))),
        'cc_residual': float(np.max(np.abs(residual))),
        'lambda_residual': float(np.max(np.abs(jacobian.T @ multipliers + transformed[0, targets]))),
        'amplitude_norm': float(np.linalg.norm(submitted)),
        'lambda_norm': float(np.linalg.norm(multipliers)),
        'cc_energy': float(transformed[0, 0]),
        'fci_energy': float(exact_energies[0]),
        'energy_error': float(abs(transformed[0, 0] - exact_energies[0])),
        'ground_overlap': float((exact @ normalized)**2),
        'reference_weight': float(exact[0]**2),
        'fci_gap': float(exact_energies[1] - exact_energies[0]),
        'hf_minima': hessians,
        'jacobian_condition': float(np.linalg.cond(jacobian)),
        'eom_real_min': float(np.min(np.linalg.eigvals(jacobian).real)),
        'biorthogonal_norm': float(left @ right),
        'density_trace': float(np.trace(density)),
        'rdm_dad': float(np.linalg.norm(density - density.T) / np.sqrt(3)),
        'occupations': occupations.tolist(),
        'occupation_violation': float(max(0, -occupations[0], occupations[-1] - 1)),
        'witness_orbital': orbitals[:, 0].tolist(),
        'orbital_population': float(orbitals[:, 0] @ density @ orbitals[:, 0]),
        'exact_occupations': np.linalg.eigvalsh(exact_density).tolist(),
        'right_occupations': np.linalg.eigvalsh(right_density).tolist(),
    }
    history = []
    previous = np.zeros(18)
    for coupling in np.linspace(0, 1, 65):
        matrix = base + coupling * (hamiltonian - base)
        answer = root(lambda amplitudes: equations(matrix, amplitudes)[:2], previous,
                      jac=True, method='hybr', options={'xtol': 2e-11, 'maxfev': 250})
        residual, jacobian, transformed, positive, negative = equations(matrix, answer.x)
        exact_values, exact_vectors = np.linalg.eigh(matrix)
        current_right = positive[:, 0]
        history.append({'coupling': float(coupling), 'solver_success': bool(answer.success),
                        'residual': float(np.max(np.abs(residual))),
                        'gap': float(exact_values[1] - exact_values[0]),
                        'overlap': float((exact_vectors[:, 0] @ current_right)**2 / (current_right @ current_right)),
                        'jacobian_singular_min': float(np.linalg.svd(jacobian, compute_uv=False)[-1]),
                        'amplitude_step': float(np.linalg.norm(answer.x - previous))})
        previous = answer.x
    report['path'] = {'overlap_min': min(row['overlap'] for row in history),
                      'gap_min': min(row['gap'] for row in history),
                      'jacobian_singular_min': min(row['jacobian_singular_min'] for row in history),
                      'amplitude_step_max': max(row['amplitude_step'] for row in history),
                      'residual_max': max(row['residual'] for row in history),
                      'endpoint_error': float(np.max(np.abs(previous - submitted))),
                      'history': history}
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
