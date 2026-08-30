import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from scipy.ndimage import gaussian_filter1d, label
from scipy.optimize import minimize

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/superconga_an_open_source_framework_for_mesoscopic_superconductivity__2205_15000/concept_2')
sys.path.insert(0, str(ROOT / 'participant/workspace'))
from spectral import load_problem, hamiltonian, response, discrepancies, validate_design

OUTPUT = Path(__file__).resolve().parent


class Model:
    def __init__(self):
        self.config, self.target = load_problem(ROOT / 'participant/input')
        self.sites = self.config['width'] * self.config['height']
        self.candidates = np.array([row * self.config['width'] + column for column, row in self.config['candidates']])
        self.probes = np.array([row * self.config['width'] + column for column, row in self.config['probes']])
        self.base = [hamiltonian(self.config, np.zeros(len(self.candidates)), condition) for condition in self.config['conditions']]
        self.edges_source, self.edges_destination = np.nonzero(np.triu(self.base[0][:self.sites, self.sites:], 1))
        self.pair = [base[self.edges_source, self.edges_destination + self.sites].copy() for base in self.base]
        self.energies = np.asarray(self.config['energies'])
        self.scale = np.maximum(np.sqrt(np.mean(self.target ** 2, axis=2, keepdims=True)), .02)
        self.sigma = 0.0
        self.binary = 0.0
        self.budget = .002
        self.calls = 0

    def matrix(self, pattern, condition_index):
        normal = np.zeros(self.sites)
        normal[self.candidates] = pattern
        amplitude = 1 - normal
        matrix = self.base[condition_index].copy()
        matrix[self.candidates, self.candidates] += self.config['pin_potential'] * pattern
        matrix[self.candidates + self.sites, self.candidates + self.sites] -= self.config['pin_potential'] * pattern
        pairing = self.pair[condition_index] * amplitude[self.edges_source] * amplitude[self.edges_destination]
        matrix[self.edges_source, self.edges_destination + self.sites] = pairing
        matrix[self.edges_destination, self.edges_source + self.sites] = pairing
        matrix[self.edges_destination + self.sites, self.edges_source] = pairing.conj()
        matrix[self.edges_source + self.sites, self.edges_destination] = pairing.conj()
        return matrix, amplitude

    def evaluate(self, pattern, gradient=True, conditions=None):
        if conditions is None:
            conditions = range(3)
        objective = 0.0
        derivative = np.zeros(len(pattern))
        results = []
        for condition_index in conditions:
            matrix, amplitude = self.matrix(pattern, condition_index)
            eigenvalues, eigenvectors = eigh(matrix, check_finite=False, driver='evr')
            probe_vectors = eigenvectors[self.probes]
            weights = np.abs(probe_vectors) ** 2
            delta = self.energies[:, None] - eigenvalues[None, :]
            denominator = delta ** 2 + self.config['broadening'] ** 2
            lorentzian = self.config['broadening'] / np.pi / denominator
            observed = weights @ lorentzian.T
            results.append(observed)
            residual = observed - self.target[condition_index]
            if self.sigma:
                residual = gaussian_filter1d(residual, self.sigma, axis=-1, mode='reflect')
            residual /= self.scale[condition_index]
            objective += np.sum(residual ** 2) / (len(conditions) * residual.size)
            if not gradient:
                continue
            adjoint = 2 * residual / self.scale[condition_index] / (len(conditions) * residual.size)
            if self.sigma:
                adjoint = gaussian_filter1d(adjoint, self.sigma, axis=-1, mode='reflect')
            weighted = adjoint @ lorentzian
            difference = eigenvalues[:, None] - eigenvalues[None, :]
            np.fill_diagonal(difference, 1)
            divided = np.zeros(matrix.shape, dtype=complex)
            for probe_index in range(len(self.probes)):
                vector = probe_vectors[probe_index]
                divided += vector.conj()[:, None] * vector[None, :] * (weighted[probe_index, :, None] - weighted[probe_index, None, :]) / difference
            lorentzian_derivative = 2 * self.config['broadening'] / np.pi * delta / denominator ** 2
            np.fill_diagonal(divided, np.sum(weights * (adjoint @ lorentzian_derivative), axis=0))
            transformed = eigenvectors @ divided
            diagonal = np.einsum('ij,ij->i', transformed, eigenvectors.conj()).real
            onsite = self.config['pin_potential'] * (diagonal[:self.sites] - diagonal[self.sites:])
            forward = np.einsum('ij,ij->i', transformed[self.edges_source], eigenvectors[self.edges_destination + self.sites].conj())
            reverse = np.einsum('ij,ij->i', transformed[self.edges_destination], eigenvectors[self.edges_source + self.sites].conj())
            edge_derivative = -2 * np.real((forward + reverse).conj() * self.pair[condition_index])
            np.add.at(onsite, self.edges_source, edge_derivative * amplitude[self.edges_destination])
            np.add.at(onsite, self.edges_destination, edge_derivative * amplitude[self.edges_source])
            derivative += onsite[self.candidates]
        self.calls += 1
        if not gradient:
            return objective, np.array(results)
        budget_error = pattern.sum() - self.config['normal_site_count']
        objective += self.budget * budget_error ** 2 + self.binary * np.mean(pattern * (1 - pattern))
        derivative += 2 * self.budget * budget_error + self.binary * (1 - 2 * pattern) / len(pattern)
        return objective, derivative

    def rounded(self, pattern):
        result = np.zeros(len(pattern), dtype=int)
        result[np.argsort(pattern)[-self.config['normal_site_count']:]] = 1
        for attempt in range(20):
            grid = np.ones((16, 16), dtype=int)
            grid.ravel()[self.candidates] = 1 - result
            labels, count = label(grid)
            if count == 1:
                return result
            disconnected = np.flatnonzero((labels.ravel()[self.candidates] != labels[0, 0]) & (result == 0))
            if not len(disconnected):
                return None
            result[disconnected] = 1
            available = np.flatnonzero(result)
            available = available[~np.isin(available, disconnected)]
            result[available[np.argsort(pattern[available])[:len(disconnected)]]] = 0
        return None


def run(arguments):
    model = Model()
    random = np.random.default_rng(arguments.seed)
    if arguments.start:
        pattern = np.load(arguments.start)
    elif arguments.initial == 'uniform':
        pattern = .375 + random.normal(0, .08, 144)
    else:
        pattern = np.zeros(144)
        pattern[random.choice(144, 54, replace=False)] = 1
        pattern = pattern * .8 + .075
    best = np.inf
    start_time = time.time()
    prefix = OUTPUT / f'run_{arguments.seed}'
    iteration = 0

    def callback(current):
        nonlocal iteration, best
        iteration += 1
        if iteration % 10 == 0:
            objective, _ = model.evaluate(current)
            np.save(str(prefix) + '_continuous.npy', current)
            print(arguments.seed, 'iter', iteration, 'calls', model.calls, 'elapsed', round(time.time()-start_time, 1), 'loss', objective, 'sum', current.sum(), 'binary', np.mean(current*(1-current)), flush=True)
        if iteration % 40 == 0:
            rounded = model.rounded(current)
            if rounded is not None:
                observed = response(model.config, rounded)
                metrics = discrepancies(model.config, observed, model.target)
                print(arguments.seed, 'rounded', metrics, flush=True)
                if metrics['relative_rmse'] < best:
                    best = metrics['relative_rmse']
                    (OUTPUT / f'best_{arguments.seed}.json').write_text(json.dumps({'pattern': rounded.tolist()}))
                    np.save(str(prefix) + '_binary.npy', rounded)

    stages = [(12, 0, 160), (6, 0, 160), (2, 0, 160), (0, 0, 200), (0, .03, 100), (0, .1, 100), (0, .3, 100)]
    if arguments.stages:
        stages = json.loads(arguments.stages)
    for sigma, binary, maxiter in stages:
        model.sigma = sigma
        model.binary = binary
        print(arguments.seed, 'STAGE', sigma, binary, maxiter, flush=True)
        result = minimize(model.evaluate, pattern, method='L-BFGS-B', jac=True, bounds=[(0, 1)]*144, callback=callback, options={'maxiter': maxiter, 'ftol': 1e-12, 'gtol': 1e-7, 'maxls': 25, 'maxcor': 20})
        pattern = result.x
        np.save(str(prefix) + f'_stage_{sigma}_{binary}.npy', pattern)
        print(arguments.seed, 'END', result.message, result.fun, flush=True)
    callback(pattern)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--initial', default='uniform')
    parser.add_argument('--start')
    parser.add_argument('--stages')
    parser.add_argument('--check', action='store_true')
    arguments = parser.parse_args()
    if arguments.check:
        model = Model()
        pattern = np.random.default_rng(3).uniform(0, 1, 144)
        start = time.time()
        value, gradient = model.evaluate(pattern)
        print('eval time', time.time()-start, value)
        for index in [0, 20, 70, 100]:
            delta = np.zeros(144)
            delta[index] = 1e-5
            numerical = (model.evaluate(pattern+delta)[0] - model.evaluate(pattern-delta)[0]) / 2e-5
            print(index, gradient[index], numerical)
        matrix, _ = model.matrix(pattern, 0)
        print('matrix error', np.max(np.abs(matrix-hamiltonian(model.config, pattern, model.config['conditions'][0]))))
    else:
        run(arguments)
