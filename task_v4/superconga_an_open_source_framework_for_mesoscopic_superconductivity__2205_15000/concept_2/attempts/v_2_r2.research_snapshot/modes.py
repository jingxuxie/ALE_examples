import argparse
import json
import time

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import least_squares

from optimize import Inverse, OUTPUT, binary, save_best


class Modes(Inverse):
    def __init__(self):
        super().__init__(stride=2)
        self.selected = np.array([142, 143, 144, 145])
        self.target_values = []
        self.target_weights = []
        for condition in range(3):
            arrays = np.load(OUTPUT / f'poles_{condition}.npz')
            poles = arrays['poles']
            indices = np.flatnonzero((poles.imag > 0.0199) & (poles.imag < 0.0201) & (np.abs(poles.real) < 0.3))
            indices = indices[np.argsort(poles[indices].real)]
            self.target_values.append(poles[indices].real)
            weights = 2 * np.pi * np.abs(arrays['residues'][indices]).T * self.scales[condition, :, 0][:, None]
            self.target_weights.append(weights)
        self.cached_modes = None
        self.mode_pattern = None

    def mode_evaluate(self, pattern):
        if self.mode_pattern is not None and np.array_equal(pattern, self.mode_pattern):
            return self.cached_modes
        amplitudes = np.ones(self.sites)
        amplitudes[self.indices] -= pattern
        residuals = []
        jacobians = []
        for condition, (base, pairing, pair_neighbors) in enumerate(zip(self.bases, self.pairings, self.pair_neighbors)):
            matrix = base.copy()
            matrix[self.indices, self.indices] += 6 * pattern
            matrix[self.indices + self.sites, self.indices + self.sites] -= 6 * pattern
            gap = pairing * amplitudes[:, None] * amplitudes[None, :]
            matrix[:self.sites, self.sites:] = gap
            matrix[self.sites:, :self.sites] = gap.conj().T
            values, vectors = eigh(matrix, check_finite=False, driver='evr', overwrite_a=True)
            chosen = vectors[:, self.selected]
            derivative = np.zeros((64, 288, 4), dtype=complex)
            coefficients = pair_neighbors * amplitudes[self.neighbors]
            derivative[np.arange(64), self.indices] = 6 * chosen[self.indices] - np.sum(coefficients[:, :, None] * chosen[self.neighbors + self.sites], axis=1)
            derivative[np.arange(64), self.indices + self.sites] = -6 * chosen[self.indices + self.sites] - np.sum(coefficients.conj()[:, :, None] * chosen[self.neighbors], axis=1)
            derivative[np.arange(64)[:, None], self.neighbors] -= coefficients[:, :, None] * chosen[self.indices + self.sites][:, None, :]
            derivative[np.arange(64)[:, None], self.neighbors + self.sites] -= coefficients.conj()[:, :, None] * chosen[self.indices][:, None, :]
            projected = (vectors.conj().T @ derivative.transpose(1, 0, 2).reshape(288, -1)).reshape(288, 64, 4)
            eigen_derivative = np.array([projected[index, :, position].real for position, index in enumerate(self.selected)])
            weight_derivative = np.zeros((8, 4, 64))
            for position, index in enumerate(self.selected):
                denominator = values[index] - values
                denominator[index] = np.inf
                vector_derivative = vectors[self.probes] @ (projected[:, :, position] / denominator[:, None])
                weight_derivative[:, position, :] = 2 * (chosen[self.probes, position].conj()[:, None] * vector_derivative).real
            weights = np.abs(chosen[self.probes]) ** 2
            weight_scale = 4 / self.scales[condition, :, 0]
            residual = np.concatenate([(values[self.selected][2:] - self.target_values[condition][2:]) / 0.15, ((weights - self.target_weights[condition]) * weight_scale[:, None]).ravel()])
            jacobian = np.concatenate([eigen_derivative[2:] / 0.15, (weight_derivative * weight_scale[:, None, None]).reshape(-1, 64)])
            residuals.append(residual)
            jacobians.append(jacobian)
        residual = np.concatenate(residuals) / np.sqrt(3)
        jacobian = np.concatenate(jacobians) / np.sqrt(3)
        self.mode_pattern = pattern.copy()
        self.cached_modes = residual, jacobian
        return residual, jacobian

    def fun(self, pattern):
        residual, unused = self.mode_evaluate(pattern)
        return np.concatenate([residual, self.regularization * pattern * (1 - pattern) / 8, [self.budget_weight * (pattern.sum() - 24) / 8]])

    def jac(self, pattern):
        unused, jacobian = self.mode_evaluate(pattern)
        return np.concatenate([jacobian, np.diag(self.regularization * (1 - 2 * pattern) / 8), np.ones((1, 64)) * self.budget_weight / 8])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', default='search')
    parser.add_argument('--starts', type=int, default=20)
    parser.add_argument('--seed', type=int, default=678)
    arguments = parser.parse_args()
    inverse = Modes()
    random = np.random.default_rng(arguments.seed)
    if arguments.mode == 'check':
        pattern = random.uniform(0.01, 0.99, 64)
        residual, jacobian = inverse.mode_evaluate(pattern)
        for index in [0, 27, 63]:
            changed = pattern.copy()
            changed[index] += 1e-6
            difference = (inverse.mode_evaluate(changed)[0] - residual) / 1e-6
            print(index, np.max(np.abs(difference - jacobian[:, index])), np.max(np.abs(difference)))
        return
    start = time.time()
    inverse.budget_weight = 2.0
    for trial in range(arguments.starts):
        if (OUTPUT / 'STOP').exists():
            break
        if trial % 4 == 0:
            pattern = np.asarray(json.loads((OUTPUT / 'design.json').read_text())['pattern'], dtype=float) * 0.98 + 0.01
        elif trial % 4 == 1:
            pattern = random.uniform(0, 0.2, 64)
        elif trial % 4 == 2:
            pattern = binary(random.random(64)) * 0.98 + 0.01
        else:
            continuous = sorted(OUTPUT.glob('continuous_*.npz'), key=lambda path: float(np.load(path)['error']))
            pattern = np.load(continuous[(trial // 4) % len(continuous)])['pattern'].copy()
        for stage, regularization in enumerate([0.15, 0.8, 3, 10]):
            inverse.regularization = regularization
            result = least_squares(inverse.fun, pattern, jac=inverse.jac, bounds=(0, 1), max_nfev=140, ftol=3e-6)
            pattern = result.x
            rounded = binary(pattern)
            raw = inverse.error(rounded)
            mode_error = np.linalg.norm(inverse.mode_evaluate(pattern)[0])
            print('MODES', trial, stage, 'time', round(time.time() - start, 1), 'mode', mode_error, 'binary', raw, 'sum', pattern.sum(), 'nfev', result.nfev, flush=True)
            save_best(inverse, rounded)
            np.savez(OUTPUT / f'mode_{arguments.seed}_{trial}_{stage}.npz', pattern=pattern, error=raw, mode_error=mode_error)


if __name__ == '__main__':
    main()
