import argparse
import time

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import least_squares

from invert import Model, OUT, save_binary


class FeatureModel(Model):
    def __init__(self):
        super().__init__()
        data = np.load(OUT / 'poles.npz')
        self.poles = data['poles']
        self.weights = data['weights']
        self.weight_scales = np.maximum(np.sqrt(np.mean(self.weights ** 2, axis=2, keepdims=True)), .0005)
        self.selected = np.arange(self.sites - 9, self.sites + 9)

    def calculate(self, pattern, jacobian=True):
        normal = np.zeros(self.sites)
        normal[self.candidates] = pattern
        amplitude = 1 - normal
        values = []
        derivatives = []
        indices = np.arange(self.sites)
        for condition, (base, pairing, gaps) in enumerate(zip(self.base, self.pair, self.gaps)):
            hopping = base.copy()
            hopping[indices, indices] += self.config['pin_potential'] * normal
            paired = pairing * amplitude[:, None] * amplitude[None, :]
            matrix = np.block([[hopping, paired], [paired.conj().T, -hopping.conj()]])
            eigenvalues, eigenvectors = eigh(matrix, check_finite=False, driver='evr', overwrite_a=True)
            selected_values = eigenvalues[self.selected]
            selected_vectors = eigenvectors[:, self.selected]
            probe_vectors = selected_vectors[self.probes]
            weights = np.abs(probe_vectors[:, 1:-1]) ** 2
            residual_weights = ((weights - self.weights[condition]) / self.weight_scales[condition]).flatten() / np.sqrt(weights.size)
            residual_poles = (selected_values[9:] - self.poles[condition]) / .03 / np.sqrt(9)
            values.append(np.concatenate([residual_weights, residual_poles]))
            if not jacobian:
                continue
            denominators = selected_values[:, None] - eigenvalues[None, :]
            denominators[np.arange(18), self.selected] = np.inf
            factors = 1 / denominators
            forward = selected_vectors.T[None, :, :]
            backward_weights = (eigenvectors[self.probes, None, :] * factors[None, :, :]) @ eigenvectors.conj().T
            backward = np.concatenate([backward_weights, forward.conj()], axis=0)
            electron = self.candidates
            hole = electron + self.sites
            derivative = self.config['pin_potential'] * (backward[:, :, electron] * forward[:, :, electron] - backward[:, :, hole] * forward[:, :, hole])
            for neighbor_index in range(8):
                neighbor = self.neighbors[:, neighbor_index]
                gap = gaps[:, neighbor_index] * amplitude[neighbor]
                neighbor_hole = neighbor + self.sites
                derivative -= gap[None, None, :] * (backward[:, :, electron] * forward[:, :, neighbor_hole] + backward[:, :, neighbor] * forward[:, :, hole])
                derivative -= gap.conj()[None, None, :] * (backward[:, :, neighbor_hole] * forward[:, :, electron] + backward[:, :, hole] * forward[:, :, neighbor])
            weight_derivative = 2 * np.real(probe_vectors.conj()[:, 1:-1, None] * derivative[:8, 1:-1])
            weight_derivative = (weight_derivative / self.weight_scales[condition, :, :, None]).reshape(-1, len(pattern)) / np.sqrt(weights.size)
            pole_derivative = np.real(derivative[8, 9:, :]) / .03 / np.sqrt(9)
            derivatives.append(np.vstack([weight_derivative, pole_derivative]))
        self.calls += 1
        return np.concatenate(values) / np.sqrt(3), np.concatenate(derivatives) / np.sqrt(3) if jacobian else None

    def objective(self, pattern, binary=0, budget=3):
        if self.last_pattern is None or not np.array_equal(pattern, self.last_pattern):
            self.last_output, self.last_derivative = self.calculate(pattern)
            self.last_pattern = pattern.copy()
        residual = self.last_output
        derivative = self.last_derivative
        if binary:
            residual = np.concatenate([residual, np.sqrt(binary / len(pattern)) * pattern * (1 - pattern)])
            derivative = np.vstack([derivative, np.diag(np.sqrt(binary / len(pattern)) * (1 - 2 * pattern))])
        if budget:
            residual = np.append(residual, np.sqrt(budget) * (pattern.sum() - self.config['normal_site_count']) / len(pattern))
            derivative = np.vstack([derivative, np.full(len(pattern), np.sqrt(budget) / len(pattern))])
        return residual, derivative


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--max-nfev', type=int, default=150)
    parser.add_argument('--start')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--binary', type=float, nargs='+', default=[0, .01, .1, 1, 10, 100])
    parser.add_argument('--budget', type=float, default=300)
    parser.add_argument('--method', default='trf')
    parser.add_argument('--jac-scale', action='store_true')
    parser.add_argument('--lower', type=float, default=0)
    parser.add_argument('--upper', type=float, default=1)
    arguments = parser.parse_args()
    model = FeatureModel()
    rng = np.random.default_rng(arguments.seed)
    pattern = np.clip(.375 + rng.normal(0, .15, len(model.candidates)), .001, .999)
    if arguments.start:
        pattern = np.load(arguments.start)
    if arguments.check:
        start = time.time()
        output, derivative = model.calculate(pattern)
        print('TIME', time.time() - start, flush=True)
        for candidate in [0, 25, 64, 131]:
            changed = pattern.copy()
            changed[candidate] += 1e-6
            changed_output, _ = model.calculate(changed, False)
            print('JAC ERROR', candidate, np.max(np.abs((changed_output - output) / 1e-6 - derivative[:, candidate])))
        return
    start = time.time()
    for stage, binary in enumerate(arguments.binary):
        iteration = [0]
        def objective(values):
            residual, derivative = model.objective(values, binary=binary, budget=arguments.budget)
            iteration[0] += 1
            if iteration[0] % 10 == 1:
                print('ITER', arguments.seed, stage, iteration[0], 'loss', np.linalg.norm(residual), 'sum', values.sum(), 'gray', np.mean(values * (1 - values)), 'time', round(time.time() - start, 2), flush=True)
            return residual
        def jacobian(values):
            return model.objective(values, binary=binary, budget=arguments.budget)[1]
        result = least_squares(objective, pattern, jac=jacobian, bounds=(arguments.lower, arguments.upper), max_nfev=arguments.max_nfev, ftol=1e-7, xtol=1e-9, gtol=1e-7, method=arguments.method, x_scale='jac' if arguments.jac_scale else 1.0)
        pattern = result.x
        np.save(OUT / f'feature_{arguments.seed}_{stage}.npy', pattern)
        print('STAGE', arguments.seed, stage, result.message, 'loss', np.linalg.norm(result.fun), flush=True)
        save_binary(model, pattern, f'feature_binary_{arguments.seed}_{stage}')


if __name__ == '__main__':
    main()
