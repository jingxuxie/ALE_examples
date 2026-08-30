import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import itertools
import json
import sys
from pathlib import Path

import numpy as np
from scipy.linalg import expm
from scipy.optimize import root


def verify(filename):
    artifact = json.loads(Path(filename).read_text())
    interaction = np.asarray(artifact['pair_matrix'])
    amplitudes = np.asarray(artifact['amplitudes'])
    energies = np.asarray(artifact['orbital_energies'])
    pairs = list(itertools.combinations(range(6), 2))
    annihilators = np.zeros((6, 64, 64))
    for orbital in range(6):
        for determinant in range(64):
            if determinant & (1 << orbital):
                sign = (-1) ** ((determinant & ((1 << orbital) - 1)).bit_count())
                annihilators[orbital, determinant ^ (1 << orbital), determinant] = sign
    creators = annihilators.transpose(0, 2, 1)
    sector = np.array([determinant for determinant in range(64) if determinant.bit_count() == 3])
    reference = np.flatnonzero(sector == 7)[0]
    ref = np.eye(20)[:, reference]

    def project(matrix):
        return matrix[np.ix_(sector, sector)]

    one = np.array([[project(creators[left] @ annihilators[right]) for right in range(6)] for left in range(6)])
    two = np.array([[project(creators[first] @ creators[second] @ annihilators[fourth] @ annihilators[third]) for third, fourth in pairs] for first, second in pairs])
    tensor = np.zeros((6, 6, 6, 6))
    for row, (first, second) in enumerate(pairs):
        for column, (third, fourth) in enumerate(pairs):
            tensor[first, second, third, fourth] = interaction[row, column]
            tensor[second, first, third, fourth] = -interaction[row, column]
            tensor[first, second, fourth, third] = -interaction[row, column]
            tensor[second, first, fourth, third] = interaction[row, column]
    contraction = sum(tensor[:, occupied, :, occupied] for occupied in range(3))
    one_body = np.diag(energies) - contraction
    hamiltonian = np.einsum('pq,pqij->ij', one_body, one) + np.einsum('pq,pqij->ij', interaction, two)
    base = np.einsum('pq,pqij->ij', np.diag(energies), one)
    generators = []
    targets = []
    for rank in (1, 2):
        for holes in itertools.combinations(range(3), rank):
            for particles in itertools.combinations(range(3, 6), rank):
                generator = np.eye(64)
                for occupied in holes:
                    generator = annihilators[occupied] @ generator
                for virtual in particles[::-1]:
                    generator = creators[virtual] @ generator
                generator = project(generator)
                target = np.argmax(abs(generator[:, reference]))
                generator *= generator[target, reference]
                generators.append(generator)
                targets.append(target)
    generators = np.asarray(generators)
    targets = np.asarray(targets)

    def equations(matrix, parameters):
        cluster = np.einsum('k,kij->ij', parameters, generators)
        positive, negative = expm(cluster), expm(-cluster)
        transformed = negative @ matrix @ positive
        commutators = transformed[:, targets] - np.einsum('kij,j->ik', generators, transformed[:, reference])
        return transformed[targets, reference], commutators[targets], transformed, positive, negative

    residual, jacobian, transformed, positive, negative = equations(hamiltonian, amplitudes)
    gradient = transformed[reference, targets]
    multipliers = np.linalg.solve(jacobian.T, -gradient)
    bra = ref.copy()
    bra[targets] = multipliers
    left, right = bra @ negative, positive[:, reference]
    density = np.einsum('i,pqij,j->pq', left, one, right)
    occupations, orbitals = np.linalg.eigh((density + density.T) / 2)
    exact_energies, exact_vectors = np.linalg.eigh(hamiltonian)
    exact_density = np.einsum('i,pqij,j->pq', exact_vectors[:, 0], one, exact_vectors[:, 0])
    right_density = np.einsum('i,pqij,j->pq', right, one, right) / (right @ right)
    curvatures = []
    for rotations in (generators[:9] - generators[:9].transpose(0, 2, 1), 1j * (generators[:9] + generators[:9].transpose(0, 2, 1))):
        hessian = np.zeros((9, 9))
        for row in range(9):
            for column in range(9):
                first = hamiltonian @ rotations[row] - rotations[row] @ hamiltonian
                second = hamiltonian @ rotations[column] - rotations[column] @ hamiltonian
                derivative = (first @ rotations[column] - rotations[column] @ first + second @ rotations[row] - rotations[row] @ second) / 2
                hessian[row, column] = derivative[reference, reference].real
        curvatures.append(float(np.linalg.eigvalsh(hessian)[0]))
    report = {
        'pair_entry_max': float(np.max(abs(interaction))),
        'pair_frobenius': float(np.linalg.norm(interaction)),
        'pair_symmetry_error': float(np.max(abs(interaction-interaction.T))),
        'canonical_fock_error': float(np.max(abs(one_body+contraction-np.diag(energies)))),
        'hamiltonian_hermiticity_error': float(np.max(abs(hamiltonian-hamiltonian.T))),
        'reference_gradient_error': float(np.max(abs(hamiltonian[targets[:9], reference]))),
        'cc_residual': float(np.max(abs(residual))),
        'lambda_residual': float(np.max(abs(jacobian.T @ multipliers + gradient))),
        'amplitude_norm': float(np.linalg.norm(amplitudes)),
        'lambda_norm': float(np.linalg.norm(multipliers)),
        'cc_energy': float(transformed[reference, reference]),
        'fci_energy': float(exact_energies[0]),
        'energy_error': float(abs(transformed[reference, reference]-exact_energies[0])),
        'ground_overlap': float((exact_vectors[:, 0] @ right)**2 / (right @ right)),
        'reference_weight': float(exact_vectors[reference, 0]**2),
        'fci_gap': float(exact_energies[1]-exact_energies[0]),
        'hf_real_min': curvatures[0], 'hf_imaginary_min': curvatures[1],
        'jacobian_condition': float(np.linalg.cond(jacobian)),
        'eom_real_min': float(np.linalg.eigvals(jacobian).real.min()),
        'biorthogonal_norm': float(left @ right),
        'density': density.tolist(),
        'rdm_trace': float(np.trace(density)),
        'rdm_dad': float(np.linalg.norm(density-density.T)/np.sqrt(3)),
        'occupations': occupations.tolist(),
        'occupation_violation': float(max(0, -occupations[0], occupations[-1]-1)),
        'minimum_population_orbital': orbitals[:, 0].tolist(),
        'maximum_population_orbital': orbitals[:, -1].tolist(),
        'exact_occupations': np.linalg.eigvalsh(exact_density).tolist(),
        'right_occupations': np.linalg.eigvalsh(right_density).tolist(),
    }
    previous = np.zeros(18)
    history = []
    for coupling in np.linspace(0, 1, 65):
        matrix = base + coupling * (hamiltonian-base)

        def combined(parameters):
            answer = equations(matrix, parameters)
            return answer[0], answer[1]

        answer = root(combined, previous, jac=True, method='hybr', options={'xtol': 2e-11, 'maxfev': 250})
        residual, jacobian, _, positive, _ = equations(matrix, answer.x)
        path_energies, path_vectors = np.linalg.eigh(matrix)
        state = positive[:, reference]
        history.append({'coupling': float(coupling), 'residual': float(np.max(abs(residual))),
                        'gap': float(path_energies[1]-path_energies[0]),
                        'overlap': float((path_vectors[:, 0] @ state)**2/(state @ state)),
                        'amplitude_step': float(np.linalg.norm(answer.x-previous)),
                        'jacobian_singular_min': float(np.linalg.svd(jacobian, compute_uv=False)[-1])})
        previous = answer.x
    report['path'] = history
    report['path_endpoint_error'] = float(np.max(abs(previous-amplitudes)))
    destination = Path(filename).with_suffix('.independent.json')
    destination.write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({key: value for key, value in report.items() if key not in ('density', 'path')}, indent=2))


if __name__ == '__main__':
    verify(sys.argv[1])
