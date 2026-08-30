import argparse
import itertools
import json
import time
from pathlib import Path

import numpy as np
from scipy.linalg import expm
from scipy.optimize import root


def check(path):
    started = time.monotonic()
    data = json.loads(Path(path).read_text())
    assert set(data) == {'schema_version', 'orbital_energies', 'pair_matrix', 'amplitudes'}
    assert data['schema_version'] == 1
    assert data['orbital_energies'] == [-1.2, -0.9, -0.5, 0.5, 0.9, 1.2]
    assert Path(path).stat().st_size <= 65536
    pair_matrix = np.asarray(data['pair_matrix'])
    amplitudes = np.asarray(data['amplitudes'])
    assert pair_matrix.shape == (15, 15) and amplitudes.shape == (18,)
    assert np.isfinite(pair_matrix).all() and np.isfinite(amplitudes).all()
    pairs = list(itertools.combinations(range(6), 2))
    sector = np.array([bits for bits in range(64) if bits.bit_count() == 3])
    reference = int(np.flatnonzero(sector == 7)[0])
    annihilators = np.zeros((6, 64, 64))
    for orbital in range(6):
        for bits in range(64):
            if bits & (1 << orbital):
                sign = (-1) ** ((bits % (1 << orbital)).bit_count())
                annihilators[orbital, bits ^ (1 << orbital), bits] = sign
    creators = annihilators.transpose(0, 2, 1)
    one_full = creators[:, None] @ annihilators[None, :]
    one = one_full[:, :, sector[:, None], sector]
    tensor = np.zeros((6, 6, 6, 6))
    full_hamiltonian = np.zeros((64, 64))
    for row, (first, second) in enumerate(pairs):
        for column, (third, fourth) in enumerate(pairs):
            value = pair_matrix[row, column]
            tensor[first, second, third, fourth] = value
            tensor[second, first, third, fourth] = -value
            tensor[first, second, fourth, third] = -value
            tensor[second, first, fourth, third] = value
            full_hamiltonian += value * creators[first] @ creators[second] @ annihilators[fourth] @ annihilators[third]
    one_body = np.diag(data['orbital_energies']) - sum(tensor[:, occupied, :, occupied] for occupied in range(3))
    full_hamiltonian += np.einsum('pq,pqij->ij', one_body, one_full)
    hamiltonian = full_hamiltonian[np.ix_(sector, sector)]
    base = np.einsum('p,pii->i', np.array(data['orbital_energies']), one[np.arange(6), np.arange(6)])
    base = np.diag(base)
    generators = []
    targets = []
    for rank in (1, 2):
        for holes in itertools.combinations(range(3), rank):
            for particles in itertools.combinations(range(3, 6), rank):
                operator = np.eye(64)
                for occupied in holes:
                    operator = annihilators[occupied] @ operator
                for virtual in particles[::-1]:
                    operator = creators[virtual] @ operator
                operator = operator[np.ix_(sector, sector)]
                target = int(np.argmax(np.abs(operator[:, reference])))
                operator *= operator[target, reference]
                generators.append(operator)
                targets.append(target)
    generators = np.array(generators)
    targets = np.array(targets)

    def equations(matrix, cluster_amplitudes):
        cluster = np.einsum('m,mij->ij', cluster_amplitudes, generators)
        positive = expm(cluster)
        negative = expm(-cluster)
        transformed = negative @ matrix @ positive
        commutators = transformed @ generators - generators @ transformed
        residual = transformed[targets, reference]
        jacobian = commutators[:, targets, reference].T
        return residual, jacobian, transformed, positive, negative, commutators[:, reference, reference]

    residual, jacobian, transformed, positive, negative, gradient = equations(hamiltonian, amplitudes)
    multipliers = np.linalg.solve(jacobian.T, -gradient)
    right = positive[:, reference]
    left_seed = np.eye(20)[reference].copy()
    left_seed[targets] = multipliers
    left = left_seed @ negative
    density = np.einsum('i,pqij,j->pq', left, one, right)
    occupations, orbitals = np.linalg.eigh((density + density.T) / 2)
    energies, exact_states = np.linalg.eigh(hamiltonian)
    ground = exact_states[:, 0]
    exact_density = np.einsum('i,pqij,j->pq', ground, one, ground)
    right_density = np.einsum('i,pqij,j->pq', right, one, right) / (right @ right)
    curvatures = []
    for rotation_generators in (generators[:9] - generators[:9].transpose(0, 2, 1),
                                1j * (generators[:9] + generators[:9].transpose(0, 2, 1))):
        hessian = np.zeros((9, 9))
        commutators = hamiltonian @ rotation_generators - rotation_generators @ hamiltonian
        for row in range(9):
            for column in range(9):
                double_commutator = (commutators[row] @ rotation_generators[column]
                                     - rotation_generators[column] @ commutators[row]
                                     + commutators[column] @ rotation_generators[row]
                                     - rotation_generators[row] @ commutators[column]) / 2
                hessian[row, column] = double_commutator[reference, reference].real
        curvatures.append(float(np.linalg.eigvalsh(hessian)[0]))
    eom = np.linalg.eigvals(jacobian)
    orbital = orbitals[:, -1] if occupations[-1] - 1 > -occupations[0] else orbitals[:, 0]
    population_operator = np.einsum('p,q,pqij->ij', orbital, orbital, one)

    def solve_cc(matrix, initial):
        def combined(cluster_amplitudes):
            values = equations(matrix, cluster_amplitudes)
            return values[0], values[1]
        solution = root(combined, initial, jac=True, method='hybr', options={'xtol': 2e-11, 'maxfev': 250})
        values = equations(matrix, solution.x)
        assert np.max(np.abs(values[0])) <= 2e-9
        return solution.x, values

    finite_step = 1e-6
    energy_plus = solve_cc(hamiltonian + finite_step * population_operator, amplitudes)[1][2][reference, reference]
    energy_minus = solve_cc(hamiltonian - finite_step * population_operator, amplitudes)[1][2][reference, reference]
    history = []
    previous = np.zeros(18)
    for coupling in np.linspace(0, 1, 65):
        matrix = base + coupling * (hamiltonian - base)
        solved, values = solve_cc(matrix, previous)
        spectrum, vectors = np.linalg.eigh(matrix)
        state = values[3][:, reference]
        history.append({'coupling': float(coupling), 'residual': float(np.max(np.abs(values[0]))),
                        'gap': float(spectrum[1] - spectrum[0]),
                        'overlap': float((vectors[:, 0] @ state) ** 2 / (state @ state)),
                        'amplitude_step': float(np.linalg.norm(solved - previous)),
                        'jacobian_singular_min': float(np.linalg.svd(values[1], compute_uv=False)[-1])})
        previous = solved
    fock = one_body + sum(tensor[:, occupied, :, occupied] for occupied in range(3))
    report = dict(cc_energy=float(transformed[reference, reference]), fci_energy=float(energies[0]),
                  energy_error=float(abs(transformed[reference, reference] - energies[0])),
                  ground_overlap=float((ground @ right) ** 2 / (right @ right)),
                  reference_weight=float(ground[reference] ** 2), fci_gap=float(energies[1] - energies[0]),
                  cc_residual=float(np.max(np.abs(residual))),
                  lambda_residual=float(np.max(np.abs(jacobian.T @ multipliers + gradient))),
                  amplitude_norm=float(np.linalg.norm(amplitudes)), lambda_norm=float(np.linalg.norm(multipliers)),
                  pair_entry_max=float(np.max(np.abs(pair_matrix))), pair_norm=float(np.linalg.norm(pair_matrix)),
                  pair_symmetry=float(np.max(np.abs(pair_matrix - pair_matrix.T))),
                  hf_real_min=curvatures[0], hf_imaginary_min=curvatures[1],
                  jacobian_condition=float(np.linalg.cond(jacobian)), eom_real_min=float(np.min(eom.real)),
                  fock_error=float(np.max(np.abs(fock - np.diag(data['orbital_energies'])))),
                  hermiticity_error=float(np.max(np.abs(hamiltonian - hamiltonian.T))),
                  reference_gradient=float(np.max(np.abs(hamiltonian[targets[:9], reference]))),
                  biorthogonal_norm=float(left @ right), rdm_trace=float(np.trace(density)),
                  occupation_violation=float(max(0, -occupations[0], occupations[-1] - 1)),
                  occupations=occupations.tolist(), exact_occupations=np.linalg.eigvalsh(exact_density).tolist(),
                  right_occupations=np.linalg.eigvalsh(right_density).tolist(),
                  population_orbital=orbital.tolist(), population=float(orbital @ density @ orbital),
                  exact_population=float(orbital @ exact_density @ orbital),
                  right_population=float(orbital @ right_density @ orbital),
                  finite_difference_population=float((energy_plus - energy_minus) / (2 * finite_step)),
                  path_overlap_min=min(item['overlap'] for item in history),
                  path_gap_min=min(item['gap'] for item in history),
                  path_amplitude_step_max=max(item['amplitude_step'] for item in history),
                  path_jacobian_singular_min=min(item['jacobian_singular_min'] for item in history),
                  path_residual_max=max(item['residual'] for item in history),
                  path_endpoint_error=float(np.max(np.abs(previous - amplitudes))),
                  runtime_seconds=time.monotonic() - started)
    upper = dict(energy_error=0.0001, cc_residual=2e-9, lambda_residual=2e-9,
                 amplitude_norm=1.25, lambda_norm=1.5, pair_entry_max=1.5, pair_norm=7,
                 pair_symmetry=1e-12, jacobian_condition=100, fock_error=2e-10,
                 hermiticity_error=2e-10, reference_gradient=2e-10, path_amplitude_step_max=0.25,
                 path_residual_max=2e-9, path_endpoint_error=5e-7)
    lower = dict(ground_overlap=0.999, reference_weight=0.45, fci_gap=0.1,
                 hf_real_min=0.05, hf_imaginary_min=0.05, eom_real_min=0.05,
                 occupation_violation=0.02, path_overlap_min=0.995,
                 path_gap_min=0.08, path_jacobian_singular_min=0.02)
    failures = [key for key, bound in upper.items() if report[key] > bound]
    failures += [key for key, bound in lower.items() if report[key] < bound]
    if abs(report['biorthogonal_norm'] - 1) > 2e-8 or abs(report['rdm_trace'] - 3) > 2e-8:
        failures.append('normalization')
    for name in ('exact_occupations', 'right_occupations'):
        if min(report[name]) < -2e-9 or max(report[name]) > 1 + 2e-9:
            failures.append(name)
    report['failures'] = failures
    report['passed'] = not failures
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('artifact')
    parser.add_argument('--output', default='independent_report.json')
    args = parser.parse_args()
    result = check(args.artifact)
    Path(args.output).write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps(result, indent=2, allow_nan=False))
