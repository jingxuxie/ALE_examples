import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import least_squares, minimize

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/superconga_an_open_source_framework_for_mesoscopic_superconductivity__2205_15000/concept_2/participant')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'workspace'))
from spectral import load_problem, hamiltonian, response, discrepancies, validate_design


class Model:
    def __init__(self, stride=2, conditions=None):
        self.config, self.target = load_problem(ROOT / 'input')
        self.sites = self.config['width'] * self.config['height']
        self.candidates = np.array([row * self.config['width'] + column for column, row in self.config['candidates']])
        self.probes = np.array([row * self.config['width'] + column for column, row in self.config['probes']])
        self.selection = np.arange(0, len(self.config['energies']), stride)
        self.energies = np.asarray(self.config['energies'])[self.selection]
        self.conditions = list(range(len(self.config['conditions']))) if conditions is None else conditions
        self.target = self.target[self.conditions][:, :, self.selection]
        self.scales = np.maximum(np.sqrt(np.mean(self.target ** 2, axis=2, keepdims=True)), .02)
        self.base = []
        self.pair = []
        for condition_index in self.conditions:
            matrix = hamiltonian(self.config, np.zeros(len(self.candidates)), self.config['conditions'][condition_index])
            self.base.append(matrix[:self.sites, :self.sites])
            self.pair.append(matrix[:self.sites, self.sites:])
        self.neighbors = []
        self.gaps = []
        for candidate in self.candidates:
            indices = np.flatnonzero(self.pair[0][candidate])
            self.neighbors.append(np.pad(indices, (0, 8 - len(indices))))
        self.neighbors = np.asarray(self.neighbors)
        for pairing in self.pair:
            self.gaps.append(pairing[self.candidates[:, None], self.neighbors])
        self.calls = 0
        self.last_pattern = None

    def calculate(self, pattern, jacobian=True):
        normal = np.zeros(self.sites)
        normal[self.candidates] = pattern
        amplitude = 1 - normal
        matrices = []
        derivatives = []
        indices = np.arange(self.sites)
        for base, pairing, gaps in zip(self.base, self.pair, self.gaps):
            hopping = base.copy()
            hopping[indices, indices] += self.config['pin_potential'] * normal
            paired = pairing * amplitude[:, None] * amplitude[None, :]
            matrix = np.block([[hopping, paired], [paired.conj().T, -hopping.conj()]])
            eigenvalues, eigenvectors = eigh(matrix, check_finite=False, driver='evr', overwrite_a=True)
            factors = 1 / (self.energies[None, :] + 1j * self.config['broadening'] - eigenvalues[:, None])
            weights = np.abs(eigenvectors[self.probes]) ** 2
            observed = -np.imag(weights @ factors) / np.pi
            matrices.append(observed)
            if not jacobian:
                continue
            forward = (eigenvectors @ (eigenvectors[self.probes].conj().T[:, :, None] * factors[:, None, :]).reshape(2 * self.sites, -1)).T
            backward = (eigenvectors.conj() @ (eigenvectors[self.probes].T[:, :, None] * factors[:, None, :]).reshape(2 * self.sites, -1)).T
            electron = self.candidates
            hole = electron + self.sites
            derivative = self.config['pin_potential'] * (backward[:, electron] * forward[:, electron] - backward[:, hole] * forward[:, hole])
            for neighbor_index in range(8):
                neighbor = self.neighbors[:, neighbor_index]
                gap = gaps[:, neighbor_index] * amplitude[neighbor]
                neighbor_hole = neighbor + self.sites
                derivative -= gap[None, :] * (backward[:, electron] * forward[:, neighbor_hole] + backward[:, neighbor] * forward[:, hole])
                derivative -= gap.conj()[None, :] * (backward[:, neighbor_hole] * forward[:, electron] + backward[:, hole] * forward[:, neighbor])
            derivatives.append((-np.imag(derivative) / np.pi).reshape(len(self.probes), len(self.energies), -1))
        self.calls += 1
        return np.asarray(matrices), np.asarray(derivatives) if jacobian else None

    def objective(self, pattern, sigma=0, binary=0, budget=0, mode='linear'):
        if self.last_pattern is None or not np.array_equal(pattern, self.last_pattern):
            self.last_output, self.last_derivative = self.calculate(pattern)
            self.last_pattern = pattern.copy()
        residual = (self.last_output - self.target) / self.scales
        derivative = self.last_derivative / self.scales[:, :, :, None]
        if mode == 'log':
            offset = .015
            residual = np.log(self.last_output + offset) - np.log(self.target + offset)
            derivative = self.last_derivative / (self.last_output[:, :, :, None] + offset)
        if mode == 'cdf':
            residual = np.cumsum(residual, axis=2) / len(self.energies)
            derivative = np.cumsum(derivative, axis=2) / len(self.energies)
        if sigma:
            residual = gaussian_filter1d(residual, sigma, axis=2)
            derivative = gaussian_filter1d(derivative, sigma, axis=2)
        residual = residual.flatten() / np.sqrt(residual.size)
        derivative = derivative.reshape(-1, len(pattern)) / np.sqrt(residual.size)
        if binary:
            residual = np.concatenate([residual, np.sqrt(binary / len(pattern)) * pattern * (1 - pattern)])
            derivative = np.vstack([derivative, np.diag(np.sqrt(binary / len(pattern)) * (1 - 2 * pattern))])
        if budget:
            residual = np.append(residual, np.sqrt(budget) * (pattern.sum() - self.config['normal_site_count']) / len(pattern))
            derivative = np.vstack([derivative, np.full(len(pattern), np.sqrt(budget) / len(pattern))])
        return residual, derivative


def save_binary(model, pattern, name):
    order = np.argsort(pattern)
    binary = np.zeros(len(pattern), dtype=int)
    binary[order[-model.config['normal_site_count']:]] = 1
    score_config, score_target = load_problem(ROOT / 'input')
    metrics = discrepancies(score_config, response(score_config, binary), score_target)
    try:
        validate_design(model.config, binary)
        feasible = True
    except ValueError:
        feasible = False
    (OUT / (name + '.json')).write_text(json.dumps({'pattern': binary.tolist()}) + '\n')
    print('BINARY', name, feasible, metrics, flush=True)
    if feasible and metrics['core_score'] >= .96 and metrics['worst_family_score'] >= .94:
        (OUT / 'design.json').write_text(json.dumps({'pattern': binary.tolist()}) + '\n')
        (OUT / 'match.json').write_text(json.dumps(metrics) + '\n')
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--stride', type=int, default=2)
    parser.add_argument('--max-nfev', type=int, default=100)
    parser.add_argument('--start')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--schedule', default='6:0,3:0,1:0,0:0,0:.1,0:1,0:10')
    parser.add_argument('--budget', type=float, default=300)
    parser.add_argument('--etas', type=float, nargs='+')
    parser.add_argument('--mode', default='linear')
    arguments = parser.parse_args()
    model = Model(stride=arguments.stride)
    rng = np.random.default_rng(arguments.seed)
    pattern = np.clip(.375 + rng.normal(0, .15, len(model.candidates)), .001, .999)
    if arguments.start:
        pattern = np.load(arguments.start)
    if arguments.check:
        start = time.time()
        output, derivative = model.calculate(pattern)
        print('TIME', time.time() - start, flush=True)
        print('VALUE ERROR', np.max(np.abs(output - response(model.config, pattern)[:, :, model.selection])))
        for candidate in [0, 25, 64, 131]:
            changed = pattern.copy()
            changed[candidate] += 1e-6
            changed_output, _ = model.calculate(changed, False)
            print('JAC ERROR', candidate, np.max(np.abs((changed_output - output) / 1e-6 - derivative[:, :, :, candidate])))
        return
    start = time.time()
    original_target = model.target.copy()
    original_scales = model.scales.copy()
    schedule = [tuple(map(float, item.split(':'))) for item in arguments.schedule.split(',')]
    for stage, (sigma, binary) in enumerate(schedule):
        if arguments.etas:
            eta = arguments.etas[min(stage, len(arguments.etas) - 1)]
            if eta == .01:
                model.target = original_target.copy()
                model.scales = original_scales.copy()
                model.config['broadening'] = .01
            else:
                from broad import broaden
                broaden(model, eta)
            model.last_pattern = None
        iteration = [0]
        def objective(values):
            residual, derivative = model.objective(values, sigma=sigma, binary=binary, budget=arguments.budget, mode=arguments.mode)
            iteration[0] += 1
            if iteration[0] % 10 == 1:
                print('ITER', arguments.seed, stage, iteration[0], 'loss', np.linalg.norm(residual), 'sum', values.sum(), 'gray', np.mean(values * (1 - values)), 'time', round(time.time() - start, 2), flush=True)
            return residual
        def jacobian(values):
            return model.objective(values, sigma=sigma, binary=binary, budget=arguments.budget, mode=arguments.mode)[1]
        result = least_squares(objective, pattern, jac=jacobian, bounds=(0, 1), max_nfev=arguments.max_nfev, ftol=1e-6, xtol=1e-6, gtol=1e-7)
        pattern = result.x
        np.save(OUT / f'continuous_{arguments.seed}_{stage}.npy', pattern)
        print('STAGE', arguments.seed, stage, result.message, 'loss', np.linalg.norm(result.fun), flush=True)
        save_binary(model, pattern, f'binary_{arguments.seed}_{stage}')


if __name__ == '__main__':
    main()
