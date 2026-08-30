import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eig
from scipy.optimize import minimize

ASSETS = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/pq_a_tool_for_prototyping_many_body_methods_for_quantum_chemistry__2106_06850/concept_2/participant/workspace')
sys.path.insert(0, str(ASSETS))
from oracle import DeterminantCC, CCResult
from api import CONSTRAINTS, artifact, endpoint_failures, check_continuation


class Search:
    def __init__(self, direct=False):
        self.direct = direct
        self.parameter_count = 156 if direct else 120
        self.oracle = DeterminantCC()
        self.indices = np.triu_indices(15)
        self.weights = np.where(self.indices[0] == self.indices[1], 1., 2.)
        self.base = self.oracle.hamiltonian(CONSTRAINTS['orbital_energies'], np.zeros((15, 15)))[0]
        self.basis = []
        for coordinate in range(120):
            unit = np.zeros(120)
            unit[coordinate] = 1.
            self.basis.append(self.oracle.hamiltonian(np.zeros(6), self.matrix(unit))[0])
        self.basis = np.array(self.basis)
        self.hf_basis = np.array([self.oracle.hf_stability(matrix) for matrix in self.basis])
        if direct:
            self.basis = np.concatenate((self.basis, np.zeros((36, 20, 20))))
            self.hf_basis = np.concatenate((self.hf_basis, np.zeros((36, 2, 9, 9))))
        self.cached_x = None
        self.calls = 0

    def matrix(self, coordinates):
        matrix = np.zeros((15, 15))
        matrix[self.indices] = coordinates[:120]
        matrix[(self.indices[1], self.indices[0])] = coordinates[:120]
        return matrix

    def evaluate(self, coordinates):
        if self.cached_x is not None and np.array_equal(coordinates, self.cached_x):
            return self.values, self.derivatives
        oracle = self.oracle
        targets = oracle.targets
        reference = oracle.reference
        hamiltonian = self.base + np.einsum('k,kij->ij', coordinates, self.basis)
        energies, vectors = np.linalg.eigh(hamiltonian)
        ground = vectors[:, 0]
        initial = ground[targets] / ground[reference]
        single_cluster = (initial[:9] @ oracle.generator_flat[:9]).reshape(20, 20)
        initial[9:] -= (single_cluster @ single_cluster[:, reference])[targets[9:]] / 2
        if self.direct:
            residual, jacobian, hbar, positive, negative = oracle.equations(hamiltonian, coordinates[120:138])
            result = CCResult(coordinates[120:138], hbar[reference, reference], np.max(abs(residual)), jacobian, hbar, positive[:, reference], negative, np.max(abs(residual)) < 1e-8)
        else:
            result = oracle.solve(hamiltonian, initial, tolerance=2e-11)
        residual, jacobian, hbar, positive, negative = oracle.equations(hamiltonian, result.amplitudes)
        fixed_hbar_derivative = negative @ self.basis @ positive
        if self.direct:
            amplitude_derivative = np.zeros((156, 18))
            amplitude_derivative[120:138] = np.eye(18)
        else:
            amplitude_derivative = -np.linalg.solve(jacobian, fixed_hbar_derivative[:, targets, reference].T).T
        cluster_derivative = (amplitude_derivative @ oracle.generator_flat).reshape(self.parameter_count, 20, 20)
        hbar_derivative = fixed_hbar_derivative + hbar @ cluster_derivative - cluster_derivative @ hbar
        jacobian_derivative = hbar_derivative[:, targets[:, None], targets]
        jacobian_derivative -= np.einsum('aij,kj->kia', oracle.generators[:, targets, :], hbar_derivative[:, :, reference])
        if self.direct:
            multipliers = coordinates[138:156]
            left_row = oracle.ref.copy()
            left_row[targets] = multipliers
            left = left_row @ negative
        else:
            multipliers, left, lambda_residual = oracle.lambda_state(result)
        lambda_rhs = hbar_derivative[:, reference, targets] + np.einsum('kij,i->kj', jacobian_derivative, multipliers)
        if self.direct:
            lambda_derivative = np.zeros((156, 18))
            lambda_derivative[138:156] = np.eye(18)
        else:
            lambda_derivative = -np.linalg.solve(jacobian.T, lambda_rhs.T).T
        self.stationarity = np.concatenate((residual, hbar[reference, targets] + jacobian.T @ multipliers))
        self.stationarity_derivative = np.concatenate((hbar_derivative[:, targets, reference], lambda_rhs + lambda_derivative @ jacobian), axis=1).T
        right = result.right
        right_derivative = (positive @ cluster_derivative[:, :, reference].T).T
        left_derivative = lambda_derivative @ negative[targets] - np.einsum('i,kij->kj', left, cluster_derivative)
        operators = oracle.one.reshape(36, 20, 20)
        operator_right = operators @ right
        operator_left = np.einsum('i,pij->pj', left, operators)
        density = (operator_right @ left).reshape(6, 6)
        density_derivative = (left_derivative @ operator_right.T + right_derivative @ operator_left.T).reshape(self.parameter_count, 6, 6)
        occupations, natural = np.linalg.eigh((density + density.T) / 2)
        antisymmetric = density - density.T
        dad = np.linalg.norm(antisymmetric) / np.sqrt(3.)
        dad_derivative = np.einsum('ij,kij->k', antisymmetric, density_derivative - density_derivative.transpose(0, 2, 1)) / max(3 * dad, 1e-30)
        exact_derivative = np.einsum('i,kij,j->k', ground, self.basis, ground)
        ground_derivative = np.einsum('ia,kij,j->ka', vectors[:, 1:], self.basis, ground) / (energies[0] - energies[1:])
        ground_derivative = ground_derivative @ vectors[:, 1:].T
        right_norm = right @ right
        overlap = ground @ right
        fidelity = overlap ** 2 / right_norm
        fidelity_derivative = 2 * overlap / right_norm * (ground_derivative @ right + right_derivative @ ground)
        fidelity_derivative -= 2 * overlap ** 2 / right_norm ** 2 * (right_derivative @ right)
        hf_matrices = oracle.hf_stability(hamiltonian)
        hf_values = []
        hf_derivatives = []
        for block in range(2):
            eigenvalues, eigenvectors = np.linalg.eigh(hf_matrices[block])
            hf_values.append(eigenvalues[0])
            hf_derivatives.append(np.einsum('i,kij,j->k', eigenvectors[:, 0], self.hf_basis[:, block], eigenvectors[:, 0]))
        singular_left, singular, singular_right = np.linalg.svd(jacobian)
        singular_max_derivative = np.einsum('i,kij,j->k', singular_left[:, 0], jacobian_derivative, singular_right[0])
        singular_min_derivative = np.einsum('i,kij,j->k', singular_left[:, -1], jacobian_derivative, singular_right[-1])
        condition = singular[0] / singular[-1]
        condition_derivative = (singular_max_derivative - condition * singular_min_derivative) / singular[-1]
        eom, eom_left, eom_right = eig(jacobian, left=True, right=True)
        lowest = np.argmin(eom.real)
        eom_derivative = (np.einsum('i,kij,j->k', eom_left[:, lowest].conj(), jacobian_derivative, eom_right[:, lowest]) / np.vdot(eom_left[:, lowest], eom_right[:, lowest])).real
        lambda_norm = np.linalg.norm(multipliers)
        amplitude_norm = np.linalg.norm(result.amplitudes)
        pair_norm = np.sqrt(np.dot(self.weights, coordinates[:120] ** 2))
        pair_derivative = np.zeros(self.parameter_count)
        pair_derivative[:120] = self.weights * coordinates[:120] / max(pair_norm, 1e-30)
        values = np.array([
            occupations[0], occupations[-1], result.energy - energies[0], fidelity,
            ground[reference] ** 2, energies[1] - energies[0], *hf_values,
            condition, lambda_norm, amplitude_norm, dad, pair_norm, eom[lowest].real,
            hbar[-1, reference],
        ])
        derivatives = np.array([
            np.einsum('i,kij,j->k', natural[:, 0], density_derivative, natural[:, 0]),
            np.einsum('i,kij,j->k', natural[:, -1], density_derivative, natural[:, -1]),
            hbar_derivative[:, reference, reference] - exact_derivative,
            fidelity_derivative,
            2 * ground[reference] * ground_derivative[:, reference],
            np.einsum('i,kij,j->k', vectors[:, 1], self.basis, vectors[:, 1]) - exact_derivative,
            *hf_derivatives,
            condition_derivative,
            lambda_derivative @ multipliers / max(lambda_norm, 1e-30),
            amplitude_derivative @ result.amplitudes / max(amplitude_norm, 1e-30),
            dad_derivative,
            pair_derivative,
            eom_derivative,
            hbar_derivative[:, -1, reference],
        ])
        self.cached_x = np.array(coordinates)
        self.values, self.derivatives = values, derivatives
        self.result = result
        self.hamiltonian = hamiltonian
        self.calls += 1
        return values, derivatives

    def constraints(self, coordinates, dad_limit=.00095, energy_limit=.000095, overlap_limit=.99905):
        values, derivatives = self.evaluate(coordinates)
        selected = np.array([2, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])
        direction = np.array([1, -1, 1, 1, 1, 1, 1, -1, -1, -1, -1, -1, 1])
        offset = np.array([energy_limit, energy_limit, -overlap_limit, -.451, -.101, -.051, -.051, 99., 1.49, 1.24, dad_limit, 6.99, -.051])
        scale = np.array([10, 10, 10, 1, 1, 1, 1, .01, 1, 1, 1, 1, 1])
        return (values[selected] * direction + offset) * scale, derivatives[selected] * (direction * scale)[:, None]

    def save(self, coordinates, path):
        self.evaluate(coordinates)
        Path(path).write_text(json.dumps(artifact(self.matrix(coordinates), self.result.amplitudes), indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--restarts', type=int, default=20)
    parser.add_argument('--iterations', type=int, default=350)
    parser.add_argument('--start')
    parser.add_argument('--dad', type=float, default=.00095)
    parser.add_argument('--energy', type=float, default=.000095)
    parser.add_argument('--overlap', type=float, default=.99905)
    parser.add_argument('--scale', type=float, default=1.)
    parser.add_argument('--gradient-test', action='store_true')
    parser.add_argument('--output', default='submission.json')
    args = parser.parse_args()
    search = Search()
    rng = np.random.default_rng(args.seed)
    started = time.monotonic()
    if args.gradient_test:
        coordinates = rng.normal(size=120) * .15
        values, derivative = search.evaluate(coordinates)
        direction = rng.normal(size=120)
        direction /= np.linalg.norm(direction)
        epsilon = 1e-5
        difference = (search.evaluate(coordinates + epsilon * direction)[0] - search.evaluate(coordinates - epsilon * direction)[0]) / (2 * epsilon)
        print(np.array([difference, derivative @ direction, difference - derivative @ direction]).T, flush=True)
        print('seconds', time.monotonic() - started, flush=True)
        return
    best = -np.inf
    best_margin = -np.inf
    for restart in range(args.restarts):
        if args.start:
            coordinates = np.asarray(json.loads(Path(args.start).read_text())['pair_matrix'])[search.indices]
            if restart:
                coordinates += rng.normal(size=120) * .02 * restart
        else:
            coordinates = rng.normal(size=120) * rng.uniform(.12, .4)
        objective_index = restart % 2
        objective_sign = 1 if objective_index == 0 else -1
        iterations = 0

        def objective(point):
            values, derivative = search.evaluate(point)
            return args.scale * objective_sign * values[objective_index], args.scale * objective_sign * derivative[objective_index]

        def constraint(point):
            return search.constraints(point, args.dad, args.energy, args.overlap)

        def callback(point):
            nonlocal iterations, best, best_margin
            iterations += 1
            values, _ = search.evaluate(point)
            violation = max(-values[0], values[1] - 1)
            margin = np.min(constraint(point)[0])
            if iterations % 20 == 0:
                print(json.dumps({'restart': restart, 'iter': iterations, 'delta': violation, 'margin': margin, 'energy': values[2], 'dad': values[11], 'fidelity': values[3], 'time': time.monotonic() - started}), flush=True)
            if margin > -1e-8 and violation > best:
                best = violation
                search.save(point, args.output)
                print('BEST', best, 'restart', restart, 'iteration', iterations, flush=True)
            if violation > .018 and margin > best_margin:
                best_margin = margin
                search.save(point, 'promising_' + str(args.seed) + '.json')

        answer = minimize(objective, coordinates, jac=True, method='SLSQP',
                          bounds=[(-1.499, 1.499)] * 120,
                          constraints={'type': 'ineq', 'fun': lambda point: constraint(point)[0], 'jac': lambda point: constraint(point)[1]},
                          callback=callback, options={'maxiter': args.iterations, 'ftol': 2e-12, 'disp': False})
        values, _ = search.evaluate(answer.x)
        print('DONE', restart, answer.message, 'values', values.tolist(), 'time', time.monotonic() - started, flush=True)
        search.save(answer.x, f'last_{args.seed}_{restart}.json')
        if best >= .02005:
            data = json.loads(Path(args.output).read_text())
            interaction = np.asarray(data['pair_matrix'])
            diagnostics, result = __import__('api').screen(interaction, data['amplitudes'], search.oracle)
            continuation = check_continuation(interaction, result.amplitudes, search.oracle)
            Path(args.output).with_suffix('.diagnostics.json').write_text(json.dumps({'endpoint': diagnostics, 'continuation': continuation}, indent=2))
            print('VERIFIED', diagnostics['failures'], continuation['passed'], diagnostics['occupation_violation'], flush=True)
            if not diagnostics['failures'] and continuation['passed']:
                break


if __name__ == '__main__':
    main()
