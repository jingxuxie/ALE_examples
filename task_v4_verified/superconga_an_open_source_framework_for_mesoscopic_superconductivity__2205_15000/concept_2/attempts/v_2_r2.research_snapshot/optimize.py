import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import least_squares

PARTICIPANT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/superconga_an_open_source_framework_for_mesoscopic_superconductivity__2205_15000/concept_2/participant')
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(PARTICIPANT / 'workspace'))
from spectral import load_problem, hamiltonian, response, discrepancies, validate_design


class Inverse:
    def __init__(self, stride=1, conditions=None):
        self.config, target = load_problem(PARTICIPANT / 'input')
        self.full_target = target
        self.conditions = conditions or list(range(len(self.config['conditions'])))
        self.target = target[self.conditions, :, ::stride]
        self.scales = np.maximum(np.sqrt(np.mean(target[self.conditions] ** 2, axis=2, keepdims=True)), 0.02)
        self.energies = np.asarray(self.config['energies'])[::stride]
        self.sites = self.config['width'] * self.config['height']
        self.indices = np.array([row * self.config['width'] + column for column, row in self.config['candidates']])
        self.probes = np.array([row * self.config['width'] + column for column, row in self.config['probes']])
        self.bases = [hamiltonian(self.config, np.zeros(64), self.config['conditions'][condition]) for condition in self.conditions]
        self.pairings = [matrix[:self.sites, self.sites:].copy() for matrix in self.bases]
        self.neighbors = np.array([[neighbor for neighbor in np.flatnonzero(self.pairings[0][site])] for site in self.indices])
        self.pair_neighbors = [pairing[self.indices[:, None], self.neighbors] for pairing in self.pairings]
        self.cached_pattern = None
        self.regularization = 0.0
        self.budget_weight = 0.0
        self.smoothing = 0.0
        self.loss = 'linear'
        self.calls = 0
        self.start = time.time()

    def evaluate(self, pattern, jacobian=True):
        if self.cached_pattern is not None and np.array_equal(pattern, self.cached_pattern) and (not jacobian or self.cached_jacobian is not None):
            return self.cached_response, self.cached_jacobian
        amplitudes = np.ones(self.sites)
        amplitudes[self.indices] -= pattern
        output = []
        derivatives = []
        for base, pairing, pair_neighbors in zip(self.bases, self.pairings, self.pair_neighbors):
            matrix = base.copy()
            matrix[self.indices, self.indices] += self.config['pin_potential'] * pattern
            matrix[self.indices + self.sites, self.indices + self.sites] -= self.config['pin_potential'] * pattern
            gap = pairing * amplitudes[:, None] * amplitudes[None, :]
            matrix[:self.sites, self.sites:] = gap
            matrix[self.sites:, :self.sites] = gap.conj().T
            eigenvalues, eigenvectors = eigh(matrix, check_finite=False, driver='evr', overwrite_a=True)
            denominators = 1.0 / (self.energies[:, None] + 1j * self.config['broadening'] - eigenvalues[None, :])
            probe_vectors = eigenvectors[self.probes]
            output.append((np.abs(probe_vectors) ** 2) @ (-denominators.imag.T / np.pi))
            if not jacobian:
                continue
            left = ((denominators[:, None, :] * probe_vectors[None, :, :]).reshape(-1, 2 * self.sites) @ eigenvectors.conj().T)
            right = ((denominators[:, None, :] * probe_vectors.conj()[None, :, :]).reshape(-1, 2 * self.sites) @ eigenvectors.T)
            electron_left = left[:, self.indices]
            hole_left = left[:, self.indices + self.sites]
            electron_right = right[:, self.indices]
            hole_right = right[:, self.indices + self.sites]
            pair_derivative = pair_neighbors * amplitudes[self.neighbors]
            gradient = self.config['pin_potential'] * (electron_left * electron_right - hole_left * hole_right)
            gradient -= electron_left * np.sum(right[:, self.neighbors + self.sites] * pair_derivative, axis=2)
            gradient -= hole_right * np.sum(left[:, self.neighbors] * pair_derivative, axis=2)
            gradient -= hole_left * np.sum(right[:, self.neighbors] * pair_derivative.conj(), axis=2)
            gradient -= electron_right * np.sum(left[:, self.neighbors + self.sites] * pair_derivative.conj(), axis=2)
            derivatives.append((-gradient.imag / np.pi).reshape(len(self.energies), len(self.probes), -1).transpose(1, 0, 2))
        self.cached_pattern = pattern.copy()
        self.cached_response = np.asarray(output)
        self.cached_jacobian = np.asarray(derivatives) if jacobian else None
        self.calls += 1
        return self.cached_response, self.cached_jacobian

    def residual(self, observed):
        if self.loss == 'log':
            residual = np.log(observed / self.scales + 0.05) - np.log(self.target / self.scales + 0.05)
        elif self.loss == 'sqrt':
            residual = 2 * (np.sqrt(observed / self.scales + 0.05) - np.sqrt(self.target / self.scales + 0.05))
        else:
            residual = (observed - self.target) / self.scales
        if self.smoothing:
            residual = gaussian_filter1d(residual, self.smoothing, axis=2)
        return residual

    def fun(self, pattern):
        observed, unused = self.evaluate(pattern)
        residual = self.residual(observed)
        residual = residual.ravel() / np.sqrt(self.target.size)
        if self.regularization:
            residual = np.concatenate([residual, self.regularization * pattern * (1 - pattern) / 8])
        if self.budget_weight:
            residual = np.concatenate([residual, [self.budget_weight * (pattern.sum() - 24) / 8]])
        return residual

    def jac(self, pattern):
        observed, gradient = self.evaluate(pattern)
        jacobian = gradient / self.scales[..., None]
        if self.loss == 'log':
            jacobian /= (observed / self.scales + 0.05)[..., None]
        elif self.loss == 'sqrt':
            jacobian /= np.sqrt(observed / self.scales + 0.05)[..., None]
        if self.smoothing:
            jacobian = gaussian_filter1d(jacobian, self.smoothing, axis=2)
        jacobian = jacobian.reshape(-1, 64) / np.sqrt(self.target.size)
        if self.regularization:
            jacobian = np.concatenate([jacobian, np.diag(self.regularization * (1 - 2 * pattern) / 8)], axis=0)
        if self.budget_weight:
            jacobian = np.concatenate([jacobian, np.ones((1, 64)) * self.budget_weight / 8], axis=0)
        return jacobian

    def error(self, pattern):
        observed, unused = self.evaluate(pattern, jacobian=False)
        residual = self.residual(observed)
        return np.sqrt(np.mean(residual ** 2))


def binary(pattern):
    result = np.zeros(64)
    result[np.argsort(pattern)[-24:]] = 1
    return result


def save_best(inverse, pattern, name='design.json'):
    try:
        validate_design(inverse.config, pattern)
    except ValueError:
        return False
    error = discrepancies(inverse.config, response(inverse.config, pattern), inverse.full_target)['relative_rmse']
    path = OUTPUT / name
    old_error = float('inf')
    if path.exists():
        old_pattern = np.asarray(json.loads(path.read_text())['pattern'])
        old_error = discrepancies(inverse.config, response(inverse.config, old_pattern), inverse.full_target)['relative_rmse']
    if error < old_error:
        path.write_text(json.dumps({'pattern': pattern.astype(int).tolist()}) + '\n')
        print('BEST', error, np.flatnonzero(pattern).tolist(), flush=True)
        return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', default='check')
    parser.add_argument('--starts', type=int, default=10)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--nfev', type=int, default=120)
    parser.add_argument('--stride', type=int, default=2)
    parser.add_argument('--budget', type=float, default=0.2)
    parser.add_argument('--regularization', type=float, default=0.0)
    parser.add_argument('--smoothing', type=float, default=0.0)
    parser.add_argument('--loss', default='linear')
    arguments = parser.parse_args()
    inverse = Inverse(stride=arguments.stride)
    random = np.random.default_rng(arguments.seed)
    if arguments.mode == 'check':
        pattern = random.uniform(0.01, 0.99, 64)
        start = time.time()
        observed, jacobian = inverse.evaluate(pattern)
        print('analytic time', time.time() - start)
        actual = response(inverse.config, pattern)[:, :, ::arguments.stride]
        print('response error', np.max(np.abs(observed - actual)))
        for index in [0, 27, 63]:
            changed = pattern.copy()
            changed[index] += 1e-5
            numerical = (inverse.evaluate(changed, False)[0] - observed) / 1e-5
            print('derivative', index, np.max(np.abs(numerical - jacobian[..., index])), np.max(np.abs(numerical)))
        return
    inverse.budget_weight = arguments.budget
    inverse.regularization = arguments.regularization
    inverse.smoothing = arguments.smoothing
    inverse.loss = arguments.loss
    for trial in range(arguments.starts):
        if arguments.mode == 'refine':
            pattern = np.asarray(json.loads((OUTPUT / 'design.json').read_text())['pattern'], dtype=float)
            if trial:
                pattern[random.choice(64, 8, replace=False)] = random.uniform(0, 1, 8)
            pattern = pattern * 0.98 + 0.01
        elif trial % 3 == 0:
            pattern = random.uniform(0.0, 0.25, 64)
        elif trial % 3 == 1:
            pattern = binary(random.random(64)) * 0.9 + 0.05
        else:
            pattern = random.uniform(0.0, 1.0, 64)
        pattern[27] = 0.99
        pattern[22] = 0.01
        start = time.time()
        initial = inverse.error(pattern)
        result = least_squares(inverse.fun, pattern, jac=inverse.jac, bounds=(0, 1), max_nfev=arguments.nfev, ftol=1e-6)
        relaxed_error = inverse.error(result.x)
        rounded = binary(result.x)
        rounded_error = inverse.error(rounded)
        print('TRIAL', trial, 'elapsed', time.time() - start, 'initial', initial, 'relaxed', relaxed_error, 'binary', rounded_error, 'sum', result.x.sum(), 'nfev', result.nfev, flush=True)
        print('continuous', np.round(result.x, 3).reshape(8, 8), flush=True)
        np.savez(OUTPUT / f'continuous_{arguments.seed}_{trial}.npz', pattern=result.x, error=relaxed_error)
        save_best(inverse, rounded)


if __name__ == '__main__':
    main()
