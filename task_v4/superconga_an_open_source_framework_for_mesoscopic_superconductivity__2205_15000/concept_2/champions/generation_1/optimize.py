import argparse
import json
import os
from pathlib import Path
import sys
import time

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import least_squares

ASSETS = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/superconga_an_open_source_framework_for_mesoscopic_superconductivity__2205_15000/concept_2/participant')
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ASSETS / 'workspace'))
from spectral import discrepancies, hamiltonian, load_problem, response, validate_design


class SpectralFit:
    def __init__(self, conditions=None, broadening=None):
        self.config, self.target = load_problem(ASSETS / 'input')
        self.sites = self.config['width'] * self.config['height']
        self.indices = np.array([row * self.config['width'] + column for column, row in self.config['candidates']])
        self.probes = np.array([row * self.config['width'] + column for column, row in self.config['probes']])
        self.energies = np.array(self.config['energies'])
        self.broadening = broadening or self.config['broadening']
        self.conditions = list(range(3)) if conditions is None else conditions
        self.target = self.target[self.conditions]
        self.scales = np.maximum(np.sqrt(np.mean(self.target ** 2, axis=2, keepdims=True)), 0.02)
        self.base = [hamiltonian(self.config, np.zeros(64), self.config['conditions'][condition]) for condition in self.conditions]
        self.pairing = [matrix[:self.sites, self.sites:].copy() for matrix in self.base]
        self.sources, self.destinations = np.nonzero(np.triu(np.abs(self.pairing[0]) > 0, 1))
        self.edge_to_candidate = np.zeros((len(self.sources), 64))
        self.edge_from_candidate = np.zeros((len(self.sources), 64))
        for candidate, site in enumerate(self.indices):
            self.edge_to_candidate[:, candidate] = self.sources == site
            self.edge_from_candidate[:, candidate] = self.destinations == site
        self.last_pattern = None
        self.last_residual = None
        self.last_jacobian = None
        self.evaluations = 0

    def evaluate(self, pattern, jacobian=True):
        if self.last_pattern is not None and np.array_equal(pattern, self.last_pattern) and (not jacobian or self.last_jacobian is not None):
            return self.last_residual, self.last_jacobian
        normal = np.zeros(self.sites)
        normal[self.indices] = pattern
        amplitude = 1 - normal
        pair_amplitudes = amplitude[:, None] * amplitude[None, :]
        output = []
        derivatives = []
        for condition_index, (base, pairing) in enumerate(zip(self.base, self.pairing)):
            matrix = base.copy()
            diagonal = np.arange(self.sites)
            matrix[diagonal, diagonal] += self.config['pin_potential'] * normal
            matrix[diagonal + self.sites, diagonal + self.sites] -= self.config['pin_potential'] * normal
            matrix[:self.sites, self.sites:] = pairing * pair_amplitudes
            matrix[self.sites:, :self.sites] = (pairing * pair_amplitudes).conj().T
            eigenvalues, eigenvectors = eigh(matrix, check_finite=False, driver='evr')
            weights = np.abs(eigenvectors[self.probes]) ** 2
            denominators = 1 / (self.energies[:, None] + 1j * self.broadening - eigenvalues[None, :])
            output.append(weights @ (-denominators.imag / np.pi).T)
            if not jacobian:
                continue
            selected = eigenvectors[self.probes]
            left = (selected[:, None, :] * denominators[None, :, :]).reshape(-1, 2 * self.sites) @ eigenvectors.conj().T
            right = (selected.conj()[:, None, :] * denominators[None, :, :]).reshape(-1, 2 * self.sites) @ eigenvectors.T
            onsite = -self.config['pin_potential'] / np.pi * (left[:, self.indices] * right[:, self.indices] - left[:, self.indices + self.sites] * right[:, self.indices + self.sites]).imag
            sources = self.sources
            destinations = self.destinations
            gaps = pairing[sources, destinations]
            pair_terms = (gaps[None, :] * (left[:, sources] * right[:, destinations + self.sites] + left[:, destinations] * right[:, sources + self.sites]) + gaps.conj()[None, :] * (left[:, destinations + self.sites] * right[:, sources] + left[:, sources + self.sites] * right[:, destinations])).imag / np.pi
            derivative = onsite + (pair_terms * amplitude[destinations]) @ self.edge_to_candidate + (pair_terms * amplitude[sources]) @ self.edge_from_candidate
            derivatives.append(derivative.reshape(len(self.probes), len(self.energies), 64) / self.scales[condition_index, :, :, None])
        self.observed = np.array(output)
        self.last_pattern = pattern.copy()
        self.last_residual = ((self.observed - self.target) / self.scales).ravel()
        self.last_jacobian = np.array(derivatives).reshape(-1, 64) if jacobian else None
        self.evaluations += 1
        return self.last_residual, self.last_jacobian

    def residual(self, pattern):
        return self.evaluate(pattern)[0]

    def jacobian(self, pattern):
        return self.evaluate(pattern)[1]


def project(pattern):
    binary = np.zeros(64, dtype=int)
    binary[np.argsort(pattern)[-24:]] = 1
    return binary


def assess(fit, pattern, label):
    config, target = load_problem(ASSETS / 'input')
    binary = project(pattern)
    results = discrepancies(config, response(config, binary), target)
    try:
        validate_design(config, binary)
        valid = True
    except ValueError:
        valid = False
    print(label, 'binary', results, 'valid', valid, flush=True)
    np.savez(OUTPUT / (label + '.npz'), continuous=pattern, pattern=binary, **results)
    if valid:
        path = OUTPUT / 'best.json'
        previous = json.loads(path.read_text()) if path.exists() else {'relative_rmse': 1e9}
        if results['relative_rmse'] < previous['relative_rmse']:
            path.write_text(json.dumps(dict(pattern=binary.tolist(), **results)) + '\n')
            (OUTPUT / 'design.json').write_text(json.dumps({'pattern': binary.tolist()}) + '\n')
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--starts', type=int, default=1)
    parser.add_argument('--nfev', type=int, default=250)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--initial')
    arguments = parser.parse_args()
    fit = SpectralFit()
    random = np.random.default_rng(arguments.seed)
    if arguments.check:
        pattern = random.uniform(0.1, 0.9, 64)
        start = time.monotonic()
        residual, jacobian = fit.evaluate(pattern)
        print('Evaluation seconds', time.monotonic() - start, flush=True)
        direction = random.normal(size=64)
        step = 1e-6
        numerical = (fit.evaluate(pattern + step * direction, False)[0] - fit.evaluate(pattern - step * direction, False)[0]) / (2 * step)
        analytic = jacobian @ direction
        print('Derivative relative error', np.linalg.norm(numerical - analytic) / np.linalg.norm(numerical), flush=True)
        print('Response max error', np.max(np.abs(response(fit.config, pattern) - fit.evaluate(pattern, False)[0].reshape(3, 8, 31) * fit.scales - fit.target)), flush=True)
        return
    for iteration in range(arguments.starts):
        if arguments.initial:
            initial = np.clip(np.load(arguments.initial)['continuous'], 1e-8, 1 - 1e-8)
        elif iteration == 0 and arguments.seed == 0:
            initial = np.full(64, 0.375)
        else:
            initial = random.uniform(0.02, 0.73, 64)
        start = time.monotonic()
        result = least_squares(fit.residual, initial, jac=fit.jacobian, bounds=(0, 1), max_nfev=arguments.nfev, verbose=1, ftol=1e-9, xtol=1e-9, gtol=1e-8)
        print('Start', iteration, 'time', time.monotonic() - start, 'cost', np.sqrt(np.mean(result.fun ** 2)), 'sum', result.x.sum(), 'binary distance', np.mean(np.minimum(result.x, 1 - result.x)), flush=True)
        assess(fit, result.x, 'fit_' + str(arguments.seed) + '_' + str(iteration))


if __name__ == '__main__':
    main()
