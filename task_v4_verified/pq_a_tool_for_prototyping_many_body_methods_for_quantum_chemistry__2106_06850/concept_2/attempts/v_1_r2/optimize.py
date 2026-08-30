import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh, eig, solve, svd
from scipy.optimize import minimize

from oracle import DeterminantCC, random_pair_matrix
from api import CONSTRAINTS, artifact, endpoint_failures, check_continuation


class Search:
    def __init__(self, mode='low'):
        self.oracle = DeterminantCC()
        self.mode = mode
        self.rows, self.cols = np.triu_indices(15)
        self.weights = np.where(self.rows == self.cols, 1.0, 2.0)
        self.epsilon = CONSTRAINTS['orbital_energies']
        self.base = self.oracle.hamiltonian(self.epsilon, np.zeros((15, 15)))[0]
        self.basis = []
        for index in range(120):
            vector = np.zeros(120)
            vector[index] = 1
            self.basis.append(self.oracle.hamiltonian(self.epsilon, self.unpack(vector))[0] - self.base)
        self.basis = np.array(self.basis)
        self.hf_base = np.array(self.oracle.hf_stability(self.base))
        self.hf_basis = np.array([self.oracle.hf_stability(matrix) for matrix in self.basis])
        self.last_x = None
        self.initial = np.zeros(18)
        self.evaluations = 0
        self.started = time.monotonic()
        self.best = -np.inf
        self.iterations = 0
        self.prefix = 'candidate'
        self.objective_scale = 1000.0
        self.radius = 2.98

    def unpack(self, vector):
        matrix = np.zeros((15, 15))
        matrix[self.rows, self.cols] = vector
        matrix[self.cols, self.rows] = vector
        return matrix

    def evaluate(self, vector):
        if self.last_x is not None and np.array_equal(vector, self.last_x):
            return self.values
        oracle = self.oracle
        reference = oracle.reference
        targets = oracle.targets
        matrix = self.base + np.einsum('k,kij->ij', vector, self.basis)
        result = oracle.solve(matrix, self.initial, tolerance=2e-11, max_evaluations=250)
        if not result.converged:
            result = oracle.solve(matrix, tolerance=2e-11, max_evaluations=250)
        self.initial = result.amplitudes.copy()
        positive, inverse = oracle.exponentials(result.amplitudes)
        transformed = result.hbar
        jacobian = result.jacobian
        right = result.right
        multipliers, left, _ = oracle.lambda_state(result)
        fixed_derivative = inverse @ self.basis @ positive
        amplitude_derivative = solve(jacobian, -fixed_derivative[:, targets, reference].T).T
        cluster_derivative = (amplitude_derivative @ oracle.generator_flat).reshape(120, 20, 20)
        transformed_derivative = fixed_derivative + transformed @ cluster_derivative - cluster_derivative @ transformed
        jacobian_derivative = transformed_derivative[:, targets[:, None], targets]
        jacobian_derivative -= np.einsum('nij,kj->kin', oracle.generators[:, targets, :], transformed_derivative[:, :, reference])
        gradient_derivative = transformed_derivative[:, reference, targets]
        multiplier_derivative = solve(jacobian.T, -(gradient_derivative + np.einsum('kin,i->kn', jacobian_derivative, multipliers)).T).T
        right_derivative = np.einsum('kij,j->ki', cluster_derivative, right)
        left_derivative = multiplier_derivative @ inverse[targets, :] - np.einsum('i,kij->kj', left, cluster_derivative)
        density = oracle.rdm(left, right)
        occupations, orbitals = eigh((density + density.T) / 2)
        orbital = orbitals[:, 0 if self.mode == 'low' else -1]
        operator = np.einsum('p,q,pqij->ij', orbital, orbital, oracle.one)
        population_derivative = left_derivative @ operator @ right + right_derivative @ operator.T @ left
        if self.mode == 'low':
            objective = occupations[0]
            objective_derivative = population_derivative
        else:
            objective = 1 - occupations[-1]
            objective_derivative = -population_derivative
        if self.mode == 'singles':
            objective = -np.sum(result.amplitudes[:9] ** 2)
            objective_derivative = -2 * amplitude_derivative[:, :9] @ result.amplitudes[:9]
        if self.mode == 'triple':
            right_norm = right @ right
            objective = -right[-1] ** 2 / right_norm
            objective_derivative = (-2 * right[-1] * right_derivative[:, -1] / right_norm
                                    - 2 * objective * (right_derivative @ right) / right_norm)
        energies, states = eigh(matrix)
        ground = states[:, 0]
        hground = self.basis @ ground
        exact_energy_derivative = hground @ ground
        cc_energy_derivative = transformed_derivative[:, reference, reference]
        error = result.energy - energies[0]
        error_derivative = cc_energy_derivative - exact_energy_derivative
        ground_derivative = ((hground @ states[:, 1:]) / (energies[0] - energies[1:])) @ states[:, 1:].T
        norm = right @ right
        overlap_amplitude = ground @ right
        overlap = overlap_amplitude ** 2 / norm
        overlap_derivative = (2 * overlap_amplitude / norm * (ground_derivative @ right + right_derivative @ ground)
                              - 2 * overlap / norm * (right_derivative @ right))
        reference_weight = ground[reference] ** 2
        reference_derivative = 2 * ground[reference] * ground_derivative[:, reference]
        gap = energies[1] - energies[0]
        gap_derivative = (self.basis @ states[:, 1]) @ states[:, 1] - exact_energy_derivative
        hf_matrices = self.hf_base + np.einsum('k,kbij->bij', vector, self.hf_basis)
        hf_values = []
        hf_derivatives = []
        for block in range(2):
            curvature, rotations = eigh(hf_matrices[block])
            hf_values.append(curvature[0])
            hf_derivatives.append((self.hf_basis[:, block] @ rotations[:, 0]) @ rotations[:, 0])
        left_singular, singular, right_singular = svd(jacobian)
        largest_derivative = np.einsum('i,kij,j->k', left_singular[:, 0], jacobian_derivative, right_singular[0])
        smallest_derivative = np.einsum('i,kij,j->k', left_singular[:, -1], jacobian_derivative, right_singular[-1])
        condition = singular[0] / singular[-1]
        condition_derivative = largest_derivative / singular[-1] - condition * smallest_derivative / singular[-1]
        eom, eom_vectors = eig(jacobian)
        eom_index = np.argmin(eom.real)
        eom_left = np.linalg.inv(eom_vectors)[eom_index]
        eom_derivative = np.einsum('i,kij,j->k', eom_left, jacobian_derivative, eom_vectors[:, eom_index]).real
        amplitude_norm = np.linalg.norm(result.amplitudes)
        lambda_norm = np.linalg.norm(multipliers)
        pair_norm = np.sqrt(self.weights @ vector ** 2)
        margins = np.array([
            100 * (0.000095 - error), 100 * (0.000095 + error),
            100 * (overlap - 0.99905), reference_weight - 0.455,
            gap - 0.105, hf_values[0] - 0.055, hf_values[1] - 0.055,
            (95 - condition) / 20, 1.48 - lambda_norm,
            1.24 - amplitude_norm, eom[eom_index].real - 0.055,
            6.95 - pair_norm,
        ])
        constraint_derivative = np.array([
            -100 * error_derivative, 100 * error_derivative,
            100 * overlap_derivative, reference_derivative,
            gap_derivative, hf_derivatives[0], hf_derivatives[1],
            -condition_derivative / 20,
            -multiplier_derivative @ multipliers / max(lambda_norm, 1e-30),
            -amplitude_derivative @ result.amplitudes / max(amplitude_norm, 1e-30),
            eom_derivative, -self.weights * vector / max(pair_norm, 1e-30),
        ])
        self.last_x = vector.copy()
        self.evaluations += 1
        self.result = result
        self.matrix = matrix
        self.values = (objective, objective_derivative, margins, constraint_derivative)
        self.info = dict(violation=float(max(-occupations[0], occupations[-1] - 1)), objective=float(objective), error=float(error), overlap=float(overlap),
                         reference=float(reference_weight), gap=float(gap), hf=[float(value) for value in hf_values],
                         condition=float(condition), lambda_norm=float(lambda_norm), amplitude_norm=float(amplitude_norm),
                         pair_norm=float(pair_norm), eom_min=float(eom[eom_index].real), residual=result.residual)
        return self.values

    def callback(self, vector):
        objective, _, margins, _ = self.evaluate(vector)
        self.iterations += 1
        if self.iterations % 10 == 0:
            print(json.dumps(dict(iteration=self.iterations, evaluations=self.evaluations,
                                  seconds=time.monotonic() - self.started, min_margin=float(margins.min()), **self.info)), flush=True)
        if margins.min() > -1e-8 and self.result.residual < 1e-9 and -objective > self.best:
            self.best = -objective
            Path(self.prefix + '.json').write_text(json.dumps(artifact(self.unpack(vector), self.result.amplitudes)))
            Path(self.prefix + '.info.json').write_text(json.dumps(self.info, indent=2))
            if self.info['violation'] >= 0.0202:
                path = check_continuation(self.unpack(vector), self.result.amplitudes, self.oracle)
                Path(self.prefix + '.path.json').write_text(json.dumps(path, indent=2))
                print('TARGET', self.best, 'PATH', path['passed'], flush=True)
                if path['passed']:
                    Path('submission.json').write_text(json.dumps(artifact(self.unpack(vector), self.result.amplitudes), indent=2))
                    raise StopIteration('Successful witness')

    def run(self, vector, iterations=400):
        return minimize(lambda value: self.objective_scale * self.evaluate(value)[0], vector,
                        jac=lambda value: self.objective_scale * self.evaluate(value)[1], method='SLSQP',
                        bounds=[(max(-1.49, value - self.radius), min(1.49, value + self.radius)) for value in vector],
                        constraints={'type': 'ineq', 'fun': lambda value: self.evaluate(value)[2],
                                     'jac': lambda value: self.evaluate(value)[3]},
                        callback=self.callback, options={'maxiter': iterations, 'ftol': 1e-11, 'disp': True})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=101)
    parser.add_argument('--mode', default='low')
    parser.add_argument('--start')
    parser.add_argument('--iterations', type=int, default=500)
    parser.add_argument('--strength', type=float, default=0.2)
    parser.add_argument('--objective-scale', type=float, default=1000.0)
    parser.add_argument('--radius', type=float, default=2.98)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    search = Search(args.mode)
    search.objective_scale = args.objective_scale
    search.radius = args.radius
    search.prefix = f'candidate_{args.seed}_{args.mode}'
    rng = np.random.default_rng(args.seed)
    if args.start:
        data = json.loads(Path(args.start).read_text())
        vector = np.array(data['pair_matrix'])[search.rows, search.cols]
        search.initial = np.array(data['amplitudes'])
    else:
        vector = random_pair_matrix(rng, args.strength)[search.rows, search.cols]
    if args.check:
        values = search.evaluate(vector)
        direction = rng.normal(size=120)
        direction /= np.linalg.norm(direction)
        plus = search.evaluate(vector + 1e-5 * direction)
        minus = search.evaluate(vector - 1e-5 * direction)
        print('objective derivative', values[1] @ direction, (plus[0] - minus[0]) / 2e-5)
        print('constraint derivatives', np.stack((values[3] @ direction, (plus[2] - minus[2]) / 2e-5), axis=1))
        print(search.info)
    else:
        try:
            answer = search.run(vector, args.iterations)
            search.callback(answer.x)
            Path(search.prefix + '.last.json').write_text(json.dumps(artifact(search.unpack(answer.x), search.result.amplitudes)))
            print(answer.message, search.info, flush=True)
        except StopIteration as success:
            print(str(success), flush=True)


if __name__ == '__main__':
    main()
