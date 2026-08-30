import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from scipy.optimize import minimize, least_squares
from scipy.ndimage import gaussian_filter1d

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/superconga_an_open_source_framework_for_mesoscopic_superconductivity__2205_15000/concept_2')
sys.path.insert(0, str(ROOT / 'participant/workspace'))
from spectral import load_problem, hamiltonian, response, discrepancies, validate_design

CONFIG, TARGET = load_problem(ROOT / 'participant/input')
OUT = Path(__file__).resolve().parent


class Model:
    def __init__(self, config=CONFIG, target=TARGET):
        self.config = config
        self.target = target
        self.sites = config['width'] * config['height']
        self.candidates = np.array([row * config['width'] + column for column, row in config['candidates']])
        self.probes = np.array([row * config['width'] + column for column, row in config['probes']])
        self.base = np.array([hamiltonian(config, np.zeros(len(self.candidates)), condition) for condition in config['conditions']])
        self.pairing = self.base[:, :self.sites, self.sites:].copy()
        self.energies = np.array(config['energies'])
        self.eta = config['broadening']
        self.scale = np.maximum(np.sqrt(np.mean(target**2, axis=2, keepdims=True)), .02)
        self.neighbor_sites = []
        self.neighbor_parameters = []
        for parameter, site in enumerate(self.candidates):
            for neighbor in np.flatnonzero(self.pairing[0, site]):
                self.neighbor_sites.append((site, neighbor))
                self.neighbor_parameters.append(parameter)
        self.neighbor_sites = np.array(self.neighbor_sites)
        self.neighbor_parameters = np.array(self.neighbor_parameters)
        self.count = 0

    def matrix(self, pattern, condition_index):
        normal = np.zeros(self.sites)
        normal[self.candidates] = pattern
        amplitude = 1 - normal
        matrix = self.base[condition_index].copy()
        matrix[self.candidates, self.candidates] += self.config['pin_potential'] * pattern
        matrix[self.candidates + self.sites, self.candidates + self.sites] -= self.config['pin_potential'] * pattern
        pairing = self.pairing[condition_index] * amplitude[:, None] * amplitude[None, :]
        matrix[:self.sites, self.sites:] = pairing
        matrix[self.sites:, :self.sites] = pairing.conj().T
        return matrix, amplitude

    def evaluate(self, pattern, gradient=True, smooth=0, mode='linear', conditions=None):
        loss = 0.
        grad = np.zeros(len(pattern))
        spectra = []
        if conditions is None:
            conditions = range(len(self.base))
        norm = len(conditions) * self.target.shape[1] * self.target.shape[2]
        for condition_index in conditions:
            matrix, amplitude = self.matrix(pattern, condition_index)
            eigenvalues, vectors = eigh(matrix, check_finite=False, driver='evr')
            probe_vectors = vectors[self.probes]
            delta = self.energies[:, None] - eigenvalues[None, :]
            lorentz = self.eta / np.pi / (delta**2 + self.eta**2)
            weights = abs(probe_vectors)**2
            observed = weights @ lorentz.T
            spectra.append(observed)
            target = self.target[condition_index]
            scale = self.scale[condition_index]
            if mode == 'log':
                residual = np.log(observed + .003) - np.log(target + .003)
                derivative = 1 / (observed + .003)
            elif mode == 'sqrt':
                residual = (np.sqrt(observed + .001) - np.sqrt(target + .001)) / np.sqrt(scale)
                derivative = .5 / np.sqrt((observed + .001) * scale)
            else:
                residual = (observed - target) / scale
                derivative = 1 / scale
            if smooth:
                residual = gaussian_filter1d(residual, smooth, axis=1, mode='reflect')
            loss += np.sum(residual**2) / norm
            if not gradient:
                continue
            adjoint = 2 * residual / norm
            if smooth:
                adjoint = gaussian_filter1d(adjoint, smooth, axis=1, mode='reflect')
            adjoint *= derivative
            functions = adjoint @ lorentz
            numerator = (probe_vectors.conj() * functions).T @ probe_vectors
            numerator = numerator - numerator.conj().T
            denominator = eigenvalues[:, None] - eigenvalues[None, :]
            np.fill_diagonal(denominator, 1.)
            kernel = numerator / denominator
            lorentz_derivative = 2 * self.eta / np.pi * delta / (delta**2 + self.eta**2)**2
            np.fill_diagonal(kernel, np.sum(weights * (adjoint @ lorentz_derivative), axis=0))
            sensitivity = vectors @ kernel @ vectors.conj().T
            grad += self.config['pin_potential'] * (sensitivity.diagonal()[self.candidates].real - sensitivity.diagonal()[self.candidates + self.sites].real)
            source, destination = self.neighbor_sites.T
            contributions = -2 * np.real((sensitivity[destination + self.sites, source] + sensitivity[source + self.sites, destination]) * self.pairing[condition_index, source, destination]) * amplitude[destination]
            grad += np.bincount(self.neighbor_parameters, contributions, minlength=len(pattern))
        self.count += 1
        return (loss, grad) if gradient else (loss, np.array(spectra))

    def residual_jacobian(self, pattern, mode='linear', smooth=0, budget_weight=1., binary_weight=0.):
        residuals = []
        jacobians = []
        norm = np.sqrt(self.target.size)
        for condition_index in range(len(self.base)):
            matrix, amplitude = self.matrix(pattern, condition_index)
            eigenvalues, vectors = eigh(matrix, check_finite=False, driver='evr')
            probe_vectors = vectors[self.probes]
            resolvent = 1 / (self.energies[:, None] + 1j*self.eta - eigenvalues[None, :])
            observed = -(abs(probe_vectors)**2 @ resolvent.imag.T) / np.pi
            rows = ((resolvent[:, None, :] * probe_vectors[None, :, :]).reshape(-1, 2*self.sites) @ vectors.conj().T).reshape(len(self.energies), len(self.probes), 2*self.sites)
            columns = ((resolvent[:, None, :] * probe_vectors.conj()[None, :, :]).reshape(-1, 2*self.sites) @ vectors.T).reshape(len(self.energies), len(self.probes), 2*self.sites)
            jacobian = -self.config['pin_potential']/np.pi * (rows[:, :, self.candidates] * columns[:, :, self.candidates] - rows[:, :, self.candidates+self.sites] * columns[:, :, self.candidates+self.sites]).imag
            source, destination = self.neighbor_sites.T
            pairing = self.pairing[condition_index, source, destination]
            contributions = ((rows[:, :, source]*columns[:, :, destination+self.sites] + rows[:, :, destination]*columns[:, :, source+self.sites])*pairing + (rows[:, :, destination+self.sites]*columns[:, :, source] + rows[:, :, source+self.sites]*columns[:, :, destination])*pairing.conj()).imag * amplitude[destination] / np.pi
            jacobian += contributions.reshape(len(self.energies), len(self.probes), len(pattern), 8).sum(axis=-1)
            jacobian = jacobian.transpose(1,0,2)
            target = self.target[condition_index]
            scale = self.scale[condition_index]
            if mode == 'log':
                residual = np.log(observed + .003) - np.log(target + .003)
                jacobian /= (observed + .003)[:, :, None]
            elif mode == 'sqrt':
                residual = (np.sqrt(observed + .001) - np.sqrt(target + .001)) / np.sqrt(scale)
                jacobian *= (.5 / np.sqrt((observed + .001) * scale))[:, :, None]
            else:
                residual = (observed - target) / scale
                jacobian /= scale[:, :, None]
            if smooth:
                residual = gaussian_filter1d(residual, smooth, axis=1, mode='reflect')
                jacobian = gaussian_filter1d(jacobian, smooth, axis=1, mode='reflect')
            residuals.append(residual.ravel() / norm)
            jacobians.append(jacobian.reshape(-1, len(pattern)) / norm)
        if budget_weight:
            residuals.append(np.array([np.sqrt(budget_weight) * (pattern.sum() - 24) / 24]))
            jacobians.append(np.full((1, len(pattern)), np.sqrt(budget_weight) / 24))
        if binary_weight:
            residuals.append(np.sqrt(binary_weight/len(pattern)) * pattern * (1 - pattern))
            jacobians.append(np.diag(np.sqrt(binary_weight/len(pattern)) * (1 - 2*pattern)))
        self.count += 1
        return np.concatenate(residuals), np.concatenate(jacobians)


def check():
    model = Model()
    pattern = np.random.default_rng(3).uniform(.1, .9, 64)
    start = time.monotonic()
    loss, gradient = model.evaluate(pattern)
    print('gradient evaluation', time.monotonic() - start, loss)
    for parameter in [0, 22, 27, 63]:
        positive = pattern.copy()
        negative = pattern.copy()
        positive[parameter] += 1e-5
        negative[parameter] -= 1e-5
        numerical = (model.evaluate(positive, False)[0] - model.evaluate(negative, False)[0]) / 2e-5
        print(parameter, gradient[parameter], numerical)
    observed = model.evaluate(pattern, False)[1]
    original = response(CONFIG, pattern)
    print('response agreement', np.max(abs(observed - original)))
    start = time.monotonic()
    residual, jacobian = model.residual_jacobian(pattern, budget_weight=0)
    print('Jacobian time', time.monotonic()-start, 'loss agreement', np.sum(residual**2)-loss, 'gradient agreement', np.max(abs(2*residual@jacobian-gradient)))


def run(seed, iterations, mode, smooth, start_file=None, budget_weight=0., binary_weight=0.):
    model = Model()
    random = np.random.default_rng(seed)
    if start_file:
        pattern = np.load(start_file)['pattern'].copy()
    elif seed % 3 == 0:
        pattern = random.uniform(.05, .75, 64)
    elif seed % 3 == 1:
        pattern = np.zeros(64)
        pattern[random.choice(64, 24, replace=False)] = 1.
        pattern = .9 * pattern + .05
    else:
        pattern = np.full(64, .375) + random.normal(0, .06, 64)
    start = time.monotonic()
    best = np.inf
    path = OUT / f'continuous_{seed}.npz'

    def objective(current):
        nonlocal best
        loss, gradient = model.evaluate(current, mode=mode, smooth=smooth)
        budget_error = (current.sum() - 24) / 24
        total = loss + budget_weight * budget_error**2 + binary_weight * np.mean(current * (1 - current))
        gradient += 2 * budget_weight * budget_error / 24 + binary_weight * (1 - 2 * current) / len(current)
        if total < best:
            best = total
            np.savez(path, pattern=current, loss=loss, total=total)
        if model.count % 25 == 0:
            print(json.dumps({'seed': seed, 'eval': model.count, 'loss': loss, 'total': total, 'sum': current.sum(), 'fractional': np.mean(current*(1-current)), 'elapsed': time.monotonic()-start}), flush=True)
        return total, gradient

    result = minimize(objective, pattern, method='L-BFGS-B', jac=True, bounds=[(0,1)]*64,
                      options={'maxiter': iterations, 'maxfun': iterations*3, 'ftol': 1e-12, 'gtol': 1e-7, 'maxls': 30, 'maxcor': 20})
    pattern = np.load(path)['pattern']
    loss, observed = model.evaluate(pattern, False)
    binary = np.zeros(64, dtype=int)
    binary[np.argsort(pattern)[-24:]] = 1
    binary_loss, binary_observed = model.evaluate(binary, False)
    np.savez(OUT / f'result_{seed}.npz', pattern=pattern, binary=binary, loss=loss, binary_loss=binary_loss)
    print('FINAL',seed,result.message, 'continuous',loss,'binary',binary_loss, 'sum',pattern.sum(), 'time', time.monotonic()-start, flush=True)
    print('PATTERN', seed, np.round(pattern,3).tolist(),flush=True)


def run_least_squares(seed, iterations, mode, smooth, start_file=None, budget_weight=1., binary_weight=0.):
    model = Model()
    random = np.random.default_rng(seed)
    if start_file:
        pattern = np.load(start_file)['pattern'].copy()
    else:
        pattern = random.uniform(.01, .8, 64)
    start = time.monotonic()
    cache = {}
    best = np.inf
    path = OUT / f'continuous_{seed}.npz'

    def objective(current, jac=False):
        nonlocal best
        if 'pattern' not in cache or not np.array_equal(current, cache['pattern']):
            residual, jacobian = model.residual_jacobian(current, mode, smooth, budget_weight, binary_weight)
            cache.update(pattern=current.copy(), residual=residual, jacobian=jacobian)
            total = np.sum(residual**2)
            if total < best:
                best = total
                np.savez(path, pattern=current, total=total)
            if model.count % 20 == 0:
                print(json.dumps({'seed': seed, 'eval': model.count, 'total': total, 'sum': current.sum(), 'fractional': np.mean(current*(1-current)), 'elapsed': time.monotonic()-start}), flush=True)
        return cache['jacobian'] if jac else cache['residual']

    result = least_squares(objective, np.clip(pattern, 1e-8, 1-1e-8), jac=lambda current: objective(current, True), bounds=(0,1), max_nfev=iterations, ftol=1e-10, xtol=1e-10, gtol=1e-8)
    pattern = np.load(path)['pattern']
    loss, observed = model.evaluate(pattern, False)
    binary = np.zeros(64, dtype=int)
    binary[np.argsort(pattern)[-24:]] = 1
    binary_loss, binary_observed = model.evaluate(binary, False)
    np.savez(OUT / f'result_{seed}.npz', pattern=pattern, binary=binary, loss=loss, binary_loss=binary_loss)
    print('FINAL',seed,result.message, 'continuous',loss,'binary',binary_loss, 'sum',pattern.sum(), 'time', time.monotonic()-start, flush=True)
    print('PATTERN', seed, np.round(pattern,3).tolist(),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--iterations', type=int, default=400)
    parser.add_argument('--mode', default='linear')
    parser.add_argument('--smooth', type=float, default=0)
    parser.add_argument('--start-file')
    parser.add_argument('--budget-weight', type=float, default=1.)
    parser.add_argument('--binary-weight', type=float, default=0.)
    parser.add_argument('--least-squares', action='store_true')
    arguments = parser.parse_args()
    if arguments.check:
        check()
    else:
        runner = run_least_squares if arguments.least_squares else run
        runner(arguments.seed, arguments.iterations, arguments.mode, arguments.smooth, arguments.start_file, arguments.budget_weight, arguments.binary_weight)
