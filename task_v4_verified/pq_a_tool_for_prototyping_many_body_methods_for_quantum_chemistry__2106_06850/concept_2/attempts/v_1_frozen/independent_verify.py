import os
import json
import itertools
import sys
from pathlib import Path

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import numpy as np
from scipy.linalg import expm
from scipy.optimize import root


def verify(filename):
    data = json.loads(Path(filename).read_text())
    assert set(data) == {'schema_version', 'orbital_energies', 'pair_matrix', 'amplitudes'}
    assert data['schema_version'] == 1
    epsilon = np.array([-1.2, -.9, -.5, .5, .9, 1.2])
    assert np.array_equal(data['orbital_energies'], epsilon)
    interaction = np.asarray(data['pair_matrix'])
    submitted = np.asarray(data['amplitudes'])
    assert interaction.shape == (15, 15) and submitted.shape == (18,)
    assert np.all(np.isfinite(interaction)) and np.all(np.isfinite(submitted))
    assert np.max(np.abs(interaction - interaction.T)) <= 1e-12
    assert np.max(np.abs(interaction)) <= 1.5
    assert np.linalg.norm(interaction) <= 7
    assert Path(filename).stat().st_size <= 65536

    annihilators = np.zeros((6, 64, 64))
    for orbital in range(6):
        for determinant in range(64):
            if determinant & (1 << orbital):
                lower = determinant & ((1 << orbital) - 1)
                annihilators[orbital, determinant ^ (1 << orbital), determinant] = (-1) ** lower.bit_count()
    creators = annihilators.transpose(0, 2, 1)
    sector = np.asarray([determinant for determinant in range(64) if determinant.bit_count() == 3])
    sector_index = np.ix_(sector, sector)
    reference_index = int(np.flatnonzero(sector == 7)[0])
    reference = np.eye(20)[:, reference_index]
    pairs = list(itertools.combinations(range(6), 2))
    tensor = np.zeros((6, 6, 6, 6))
    two_body = np.zeros((64, 64))
    for row, (first, second) in enumerate(pairs):
        for column, (third, fourth) in enumerate(pairs):
            value = interaction[row, column]
            tensor[first, second, third, fourth] = value
            tensor[second, first, third, fourth] = -value
            tensor[first, second, fourth, third] = -value
            tensor[second, first, fourth, third] = value
            two_body += value * creators[first] @ creators[second] @ annihilators[fourth] @ annihilators[third]
    contraction = sum(tensor[:, occupied, :, occupied] for occupied in range(3))
    one_operators_full = np.asarray([[creators[first] @ annihilators[second] for second in range(6)] for first in range(6)])
    one_operators = one_operators_full[:, :, sector[:, None], sector[None, :]]
    hzero_full = np.einsum('pq,pqij->ij', np.diag(epsilon), one_operators_full)
    perturbation_full = two_body - np.einsum('pq,pqij->ij', contraction, one_operators_full)
    hzero = hzero_full[sector_index]
    perturbation = perturbation_full[sector_index]
    one_integrals = np.diag(epsilon) - contraction
    fock_error = np.max(np.abs(one_integrals + contraction - np.diag(epsilon)))

    generators = []
    targets = []
    for occupied in range(3):
        for virtual in range(3, 6):
            full = creators[virtual] @ annihilators[occupied]
            projected = full[sector_index]
            target = np.argmax(np.abs(projected[:, reference_index]))
            projected = projected * projected[target, reference_index]
            generators.append(projected)
            targets.append(target)
    for occupied_pair in itertools.combinations(range(3), 2):
        for virtual_pair in itertools.combinations(range(3, 6), 2):
            occupied_first, occupied_second = occupied_pair
            virtual_first, virtual_second = virtual_pair
            full = creators[virtual_first] @ creators[virtual_second] @ annihilators[occupied_second] @ annihilators[occupied_first]
            projected = full[sector_index]
            target = np.argmax(np.abs(projected[:, reference_index]))
            projected = projected * projected[target, reference_index]
            generators.append(projected)
            targets.append(target)
    generators = np.asarray(generators)
    targets = np.asarray(targets)

    def equations(hamiltonian, amplitudes):
        cluster = np.einsum('a,aij->ij', amplitudes, generators)
        positive = expm(cluster)
        inverse = expm(-cluster)
        hbar = inverse @ hamiltonian @ positive
        commutators = hbar @ generators - generators @ hbar
        jacobian = commutators[:, targets, reference_index].T
        return hbar[targets, reference_index], jacobian, hbar, positive, inverse

    hamiltonian = hzero + perturbation
    residual, jacobian, hbar, positive, inverse = equations(hamiltonian, submitted)
    multipliers = np.linalg.solve(jacobian.T, -hbar[reference_index, targets])
    row = reference.copy()
    row[targets] = multipliers
    left = row @ inverse
    right = positive[:, reference_index]
    density = np.einsum('i,pqij,j->pq', left, one_operators, right)
    populations, orbitals = np.linalg.eigh((density + density.T) / 2)
    exact_values, exact_vectors = np.linalg.eigh(hamiltonian)
    exact_right = exact_vectors[:, 0]
    exact_density = np.einsum('i,pqij,j->pq', exact_right, one_operators, exact_right)
    normalized_right = right / np.linalg.norm(right)
    right_density = np.einsum('i,pqij,j->pq', normalized_right, one_operators, normalized_right)

    def curvature(rotations):
        blocks = np.empty((9, 9))
        for first in range(9):
            commutator_first = hamiltonian @ rotations[first] - rotations[first] @ hamiltonian
            for second in range(9):
                commutator_second = hamiltonian @ rotations[second] - rotations[second] @ hamiltonian
                double = commutator_first @ rotations[second] - rotations[second] @ commutator_first
                double += commutator_second @ rotations[first] - rotations[first] @ commutator_second
                blocks[first, second] = (double[reference_index, reference_index] / 2).real
        return blocks

    real_rotations = generators[:9] - generators[:9].transpose(0, 2, 1)
    imaginary_rotations = 1j * (generators[:9] + generators[:9].transpose(0, 2, 1))
    real_curvature = np.linalg.eigvalsh(curvature(real_rotations))
    imaginary_curvature = np.linalg.eigvalsh(curvature(imaginary_rotations))
    energy = hbar[reference_index, reference_index]
    diagnostics = {
        'cc_energy': float(energy),
        'fci_energy': float(exact_values[0]),
        'energy_error': float(abs(energy - exact_values[0])),
        'population_violation': float(max(-populations[0], populations[-1] - 1, 0)),
        'populations': populations.tolist(),
        'negative_population_orbital': orbitals[:, 0].tolist(),
        'negative_population': float(orbitals[:, 0] @ density @ orbitals[:, 0]),
        'exact_populations': np.linalg.eigvalsh(exact_density).tolist(),
        'right_populations': np.linalg.eigvalsh(right_density).tolist(),
        'cc_residual': float(np.max(np.abs(residual))),
        'lambda_residual': float(np.max(np.abs(jacobian.T @ multipliers + hbar[reference_index, targets]))),
        'amplitude_norm': float(np.linalg.norm(submitted)),
        'lambda_norm': float(np.linalg.norm(multipliers)),
        'jacobian_condition': float(np.linalg.cond(jacobian)),
        'eom_real_min': float(np.min(np.linalg.eigvals(jacobian).real)),
        'ground_overlap': float((exact_right @ right) ** 2 / (right @ right)),
        'reference_weight': float(exact_right[reference_index] ** 2),
        'fci_gap': float(exact_values[1] - exact_values[0]),
        'hf_real_min': float(real_curvature[0]),
        'hf_imaginary_min': float(imaginary_curvature[0]),
        'fock_error': float(fock_error),
        'hermiticity_error': float(np.max(np.abs(hamiltonian - hamiltonian.T))),
        'hf_gradient': float(np.max(np.abs(2 * hamiltonian[targets[:9], reference_index]))),
        'biorthogonal_norm': float(left @ right),
        'rdm_trace': float(np.trace(density)),
    }

    upper_limits = {'energy_error': 1e-4, 'cc_residual': 2e-9, 'lambda_residual': 2e-9, 'amplitude_norm': 1.25, 'lambda_norm': 1.5, 'jacobian_condition': 100, 'fock_error': 2e-10, 'hermiticity_error': 2e-10, 'hf_gradient': 2e-10}
    lower_limits = {'population_violation': .02, 'ground_overlap': .999, 'reference_weight': .45, 'fci_gap': .1, 'hf_real_min': .05, 'hf_imaginary_min': .05, 'eom_real_min': .05}
    failures = [key for key, limit in upper_limits.items() if diagnostics[key] > limit]
    failures += [key for key, limit in lower_limits.items() if diagnostics[key] < limit]
    assert abs(left @ right - 1) <= 2e-8
    assert abs(np.trace(density) - 3) <= 2e-8
    assert np.linalg.eigvalsh(exact_density)[0] >= -2e-9
    assert np.linalg.eigvalsh(exact_density)[-1] <= 1 + 2e-9
    assert np.linalg.eigvalsh(right_density)[0] >= -2e-9
    assert np.linalg.eigvalsh(right_density)[-1] <= 1 + 2e-9

    previous = np.zeros(18)
    history = []
    for step in range(65):
        coupling = step / 64
        current_hamiltonian = hzero + coupling * perturbation

        def combined(amplitudes):
            current_residual, current_jacobian, _, _, _ = equations(current_hamiltonian, amplitudes)
            return current_residual, current_jacobian

        answer = root(combined, previous, jac=True, method='hybr', options={'xtol': 2e-11, 'maxfev': 250})
        current_residual, current_jacobian, _, current_positive, _ = equations(current_hamiltonian, answer.x)
        exact_energies, exact_states = np.linalg.eigh(current_hamiltonian)
        current_right = current_positive[:, reference_index]
        row = {'coupling': coupling, 'residual': float(np.max(np.abs(current_residual))),
               'overlap': float((exact_states[:, 0] @ current_right) ** 2 / (current_right @ current_right)),
               'gap': float(exact_energies[1] - exact_energies[0]),
               'jacobian_singular_min': float(np.linalg.svd(current_jacobian, compute_uv=False)[-1]),
               'amplitude_step': float(np.linalg.norm(answer.x - previous))}
        history.append(row)
        if row['residual'] > 2e-9 or row['overlap'] < .995 or row['gap'] < .08 or row['jacobian_singular_min'] < .02 or row['amplitude_step'] > .25:
            failures.append('continuation_' + str(step))
        previous = answer.x
    endpoint_error = float(np.max(np.abs(previous - submitted)))
    if endpoint_error > 5e-7:
        failures.append('path_endpoint')
    diagnostics['path_endpoint_error'] = endpoint_error
    diagnostics['path_min_overlap'] = min(row['overlap'] for row in history)
    diagnostics['path_min_gap'] = min(row['gap'] for row in history)
    diagnostics['path_min_singular_value'] = min(row['jacobian_singular_min'] for row in history)
    diagnostics['path_max_amplitude_step'] = max(row['amplitude_step'] for row in history)
    diagnostics['path_max_residual'] = max(row['residual'] for row in history)
    diagnostics['path'] = history
    diagnostics['failures'] = failures
    diagnostics['passed'] = not failures
    return diagnostics


if __name__ == '__main__':
    report = verify(sys.argv[1] if len(sys.argv) > 1 else 'submission.json')
    Path('independent_validation.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({key: value for key, value in report.items() if key != 'path'}, indent=2, allow_nan=False))
    if not report['passed']:
        raise SystemExit(1)
