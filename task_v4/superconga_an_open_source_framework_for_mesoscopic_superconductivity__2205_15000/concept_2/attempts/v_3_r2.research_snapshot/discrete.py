import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh
from scipy.ndimage import gaussian_filter1d

from optimize import Model, OUTPUT, response, discrepancies, validate_design


class Discrete(Model):
    def prepare(self, pattern):
        self.pattern = pattern.copy()
        self.flip_sign = 1 - 2 * pattern
        self.single_inverse = np.zeros((144, 4, 4), dtype=complex)
        self.single_inverse[:, 0, 2] = 1
        self.single_inverse[:, 2, 0] = 1
        self.single_inverse[:, 1, 3] = 1
        self.single_inverse[:, 3, 1] = 1
        self.single_inverse[:, 2, 2] = -self.config['pin_potential'] * self.flip_sign
        self.single_inverse[:, 3, 3] = self.config['pin_potential'] * self.flip_sign
        self.cache = []
        observed_all = []
        singles_all = []
        for condition_index in range(3):
            matrix, amplitude = self.matrix(pattern, condition_index)
            eigenvalues, eigenvectors = eigh(matrix, check_finite=False, driver='evr')
            resolvent = 1 / (self.energies[None, :] + 1j*self.config['broadening'] - eigenvalues[:, None])
            probe_vectors = eigenvectors[self.probes]
            observed = -(np.abs(probe_vectors)**2 @ resolvent).imag / np.pi
            changes = -self.flip_sign[None, :] * self.base[condition_index][:self.sites, self.sites:][:, self.candidates] * amplitude[:, None]
            projected = np.zeros((144, 4, 512), dtype=complex)
            projected[:, 0, :] = eigenvectors[self.candidates].conj()
            projected[:, 1, :] = eigenvectors[self.candidates + self.sites].conj()
            projected[:, 2, :] = (eigenvectors[self.sites:].conj().T @ changes.conj()).T
            projected[:, 3, :] = (eigenvectors[:self.sites].conj().T @ changes).T
            coefficients = projected.conj()[:, :, None, :] * projected[:, None, :, :]
            local = (coefficients.reshape(-1, 512) @ resolvent).reshape(144, 4, 4, -1).transpose(0, 3, 1, 2)
            coefficients = probe_vectors[None, :, None, :] * projected[:, None, :, :]
            left = (coefficients.reshape(-1, 512) @ resolvent).reshape(144, 8, 4, -1).transpose(0, 3, 1, 2)
            right = (coefficients.conj().reshape(-1, 512) @ resolvent).reshape(144, 8, 4, -1).transpose(0, 3, 2, 1)
            correction = np.einsum('nepa,neap->npe', left, np.linalg.solve(self.single_inverse[:, None] - local, right))
            singles = observed[None, :, :] - correction.imag / np.pi
            self.cache.append((projected, resolvent, local, left, right))
            observed_all.append(observed)
            singles_all.append(singles)
        self.observed = np.array(observed_all)
        self.singles = np.array(singles_all).transpose(1, 0, 2, 3)
        return self.observed, self.singles

    def pair_responses(self, pairs):
        responses = []
        first = pairs[:, 0]
        second = pairs[:, 1]
        for condition_index, (projected, resolvent, local, left, right) in enumerate(self.cache):
            combined_inverse = np.zeros((len(pairs), 8, 8), dtype=complex)
            combined_inverse[:, :4, :4] = self.single_inverse[first]
            combined_inverse[:, 4:, 4:] = self.single_inverse[second]
            pair_values = self.base[condition_index][self.candidates[first], self.candidates[second] + self.sites] * self.flip_sign[first] * self.flip_sign[second]
            adjacent = np.flatnonzero(pair_values)
            if len(adjacent):
                combined = np.linalg.inv(combined_inverse[adjacent])
                combined[:, 0, 5] += pair_values[adjacent]
                combined[:, 5, 0] += pair_values[adjacent].conj()
                combined[:, 4, 1] += pair_values[adjacent]
                combined[:, 1, 4] += pair_values[adjacent].conj()
                combined_inverse[adjacent] = np.linalg.inv(combined)
            cross_coefficients = projected[first].conj()[:, :, None, :] * projected[second][:, None, :, :]
            cross_forward = (cross_coefficients.reshape(-1, 512) @ resolvent).reshape(len(pairs), 4, 4, -1).transpose(0, 3, 1, 2)
            cross_reverse = (cross_coefficients.conj().reshape(-1, 512) @ resolvent).reshape(len(pairs), 4, 4, -1).transpose(0, 3, 2, 1)
            combined_local = np.zeros((len(pairs), len(self.energies), 8, 8), dtype=complex)
            combined_local[:, :, :4, :4] = local[first]
            combined_local[:, :, 4:, 4:] = local[second]
            combined_local[:, :, :4, 4:] = cross_forward
            combined_local[:, :, 4:, :4] = cross_reverse
            combined_left = np.concatenate([left[first], left[second]], axis=-1)
            combined_right = np.concatenate([right[first], right[second]], axis=-2)
            correction = np.einsum('nepa,neap->npe', combined_left, np.linalg.solve(combined_inverse[:, None] - combined_local, combined_right))
            responses.append(self.observed[condition_index][None] - correction.imag / np.pi)
        return np.array(responses).transpose(1, 0, 2, 3)

    def residual(self, observed):
        residual = observed - self.target
        if self.sigma:
            residual = gaussian_filter1d(residual, self.sigma, axis=-1, mode='reflect')
        return residual / self.scale

    def search(self, pattern, limit=128, exhaustive=False):
        observed, singles = self.prepare(pattern)
        current_residual = self.residual(observed).ravel()
        current_loss = np.mean(current_residual**2)
        single_residual = self.residual(singles).reshape(144, -1)
        differences = single_residual - current_residual
        single_loss = np.mean(single_residual**2, axis=1)
        approximate = single_loss[:, None] + single_loss[None, :] - current_loss + 2*differences @ differences.T / len(current_residual)
        occupied = np.flatnonzero(pattern)
        empty = np.flatnonzero(1-pattern)
        first, second = np.meshgrid(occupied, empty, indexing='ij')
        all_pairs = np.stack([first.ravel(), second.ravel()], axis=1)
        order = np.argsort(approximate[all_pairs[:, 0], all_pairs[:, 1]])
        if not exhaustive:
            order = order[:limit]
        best_loss = current_loss
        best_pattern = pattern.copy()
        best_observed = observed.copy()
        for offset in range(0, len(order), limit):
            pairs = all_pairs[order[offset:offset+limit]]
            candidates = self.pair_responses(pairs)
            losses = np.mean(self.residual(candidates)**2, axis=(1, 2, 3))
            for index in np.argsort(losses):
                if losses[index] >= best_loss:
                    break
                proposed = pattern.copy()
                proposed[pairs[index]] = 1-proposed[pairs[index]]
                try:
                    validate_design(self.config, proposed)
                except ValueError:
                    continue
                best_loss = losses[index]
                best_pattern = proposed
                best_observed = candidates[index]
                break
            if exhaustive and best_loss < .95*current_loss:
                break
        return best_pattern, best_loss, best_observed, current_loss


def run(arguments):
    model = Discrete()
    random = np.random.default_rng(arguments.seed)
    if arguments.start:
        if arguments.start.endswith('.json'):
            pattern = np.asarray(json.loads(Path(arguments.start).read_text())['pattern'])
        else:
            pattern = model.rounded(np.load(arguments.start))
    else:
        while True:
            pattern = np.zeros(144, dtype=int)
            pattern[random.choice(144, 54, replace=False)] = 1
            try:
                validate_design(model.config, pattern)
                break
            except ValueError:
                pass
    start = time.time()
    best = np.inf
    iteration = 0
    stages = json.loads(arguments.stages)
    for sigma, iterations in stages:
        model.sigma = sigma
        for stage_iteration in range(iterations):
            candidate, loss, observed, previous = model.search(pattern, arguments.limit)
            if arguments.exhaustive and np.array_equal(pattern,candidate):
                print(arguments.seed,'EXHAUSTIVE',iteration,sigma,flush=True)
                candidate, loss, observed, previous = model.search(pattern, arguments.limit, exhaustive=True)
            iteration += 1
            metrics = discrepancies(model.config, observed, model.target)
            print(arguments.seed, iteration, 'sigma', sigma, 'elapsed', round(time.time()-start,1), 'loss', loss, 'previous', previous, 'metrics', metrics, flush=True)
            if metrics['relative_rmse'] < best:
                best = metrics['relative_rmse']
                (OUTPUT / f'discrete_best_{arguments.seed}.json').write_text(json.dumps({'pattern':candidate.tolist()}))
            (OUTPUT / f'discrete_current_{arguments.seed}.json').write_text(json.dumps({'pattern':candidate.tolist()}))
            if np.array_equal(pattern, candidate):
                break
            pattern = candidate
            if metrics['core_score'] >= .96 and metrics['worst_family_score'] >= .94:
                (OUTPUT / 'design.json').write_text(json.dumps({'pattern': pattern.tolist()}))
                return


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--start')
    parser.add_argument('--stages', default='[[10,40],[5,40],[2,40],[0,60]]')
    parser.add_argument('--limit', type=int, default=128)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--exhaustive', action='store_true')
    arguments = parser.parse_args()
    if arguments.check:
        model = Discrete()
        pattern = np.zeros(144,dtype=int)
        pattern[np.random.default_rng(3).choice(144,54,replace=False)] = 1
        start = time.time()
        observed, singles = model.prepare(pattern)
        print('prepare time',time.time()-start,flush=True)
        flipped = pattern.copy()
        flipped[50] = 1-flipped[50]
        print('single error',np.max(np.abs(response(model.config,flipped)-singles[50])),flush=True)
        pairs = np.array([[50,51],[20,90],[71,82]])
        start=time.time()
        predictions=model.pair_responses(pairs)
        print('pair time',time.time()-start,flush=True)
        for index,pair in enumerate(pairs):
            flipped=pattern.copy()
            flipped[pair]=1-flipped[pair]
            print(pair,'pair error',np.max(np.abs(response(model.config,flipped)-predictions[index])),flush=True)
    else:
        run(arguments)
