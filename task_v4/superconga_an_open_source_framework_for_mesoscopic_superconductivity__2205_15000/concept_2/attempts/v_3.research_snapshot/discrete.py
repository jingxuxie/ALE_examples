import argparse
import json
import time

import numpy as np
from scipy.linalg import eigh
from scipy.ndimage import gaussian_filter1d

from invert import Model, OUT, response, discrepancies, validate_design


class FlipModel(Model):
    def calculate_flips(self, pattern):
        self.cache = []
        self.current_pattern = pattern.copy()
        normal = np.zeros(self.sites)
        normal[self.candidates] = pattern
        amplitude = 1 - normal
        indices = np.arange(self.sites)
        observations = []
        flipped = []
        for base, pairing, gaps in zip(self.base, self.pair, self.gaps):
            hopping = base.copy()
            hopping[indices, indices] += self.config['pin_potential'] * normal
            paired = pairing * amplitude[:, None] * amplitude[None, :]
            matrix = np.block([[hopping, paired], [paired.conj().T, -hopping.conj()]])
            eigenvalues, eigenvectors = eigh(matrix, check_finite=False, driver='evr', overwrite_a=True)
            factors = 1 / (self.energies[:, None] + 1j * self.config['broadening'] - eigenvalues[None, :])
            probe_vectors = eigenvectors[self.probes]
            observed = -np.imag(factors @ (np.abs(probe_vectors) ** 2).T) / np.pi
            observations.append(observed.T)
            gap = gaps * amplitude[self.neighbors]
            transformed = np.stack([eigenvectors[self.candidates].conj(),
                                    eigenvectors[self.candidates + self.sites].conj(),
                                    np.sum(eigenvectors[self.neighbors + self.sites].conj() * gap.conj()[:, :, None], axis=1),
                                    np.sum(eigenvectors[self.neighbors].conj() * gap[:, :, None], axis=1)], axis=1)
            products = transformed.conj()[:, :, None, :] * transformed[:, None, :, :]
            gram = (factors @ products.reshape(-1, 2 * self.sites).T).reshape(len(self.energies), len(pattern), 4, 4)
            forward = ((factors[:, None, :] * probe_vectors[None, :, :]).reshape(-1, 2 * self.sites) @ transformed.reshape(-1, 2 * self.sites).T).reshape(len(self.energies), len(self.probes), len(pattern), 4).transpose(0, 2, 1, 3)
            backward = ((factors[:, None, :] * probe_vectors.conj()[None, :, :]).reshape(-1, 2 * self.sites) @ transformed.conj().reshape(-1, 2 * self.sites).T).reshape(len(self.energies), len(self.probes), len(pattern), 4).transpose(0, 2, 3, 1)
            inverse_coupling = np.array([[0, 0, -1, 0], [0, 0, 0, -1], [-1, 0, -self.config['pin_potential'], 0], [0, -1, 0, self.config['pin_potential']]])
            update = np.linalg.solve((1 - 2 * pattern)[None, :, None, None] * inverse_coupling[None, None, :, :] - gram, backward)
            correction = -np.imag(np.sum(forward * update.transpose(0, 1, 3, 2), axis=3)) / np.pi
            flipped.append((observed[:, None, :] + correction).transpose(1, 2, 0))
            self.cache.append((factors, transformed, gram, forward, backward, observed, pairing))
        return np.asarray(observations), np.stack(flipped, axis=1)

    def calculate_swaps(self, remove, add):
        outputs = []
        count = len(remove)
        for factors, transformed, gram, forward, backward, observed, pairing in self.cache:
            products = transformed[remove].conj()[:, :, None, :] * transformed[add][:, None, :, :]
            cross = (factors @ products.reshape(-1, 2 * self.sites).T).reshape(len(self.energies), count, 4, 4)
            reverse = (factors @ products.conj().reshape(-1, 2 * self.sites).T).reshape(len(self.energies), count, 4, 4).transpose(0, 1, 3, 2)
            joint_gram = np.concatenate([np.concatenate([gram[:, remove], cross], axis=3), np.concatenate([reverse, gram[:, add]], axis=3)], axis=2)
            joint_forward = np.concatenate([forward[:, remove], forward[:, add]], axis=3)
            joint_backward = np.concatenate([backward[:, remove], backward[:, add]], axis=2)
            coupling = np.zeros((count, 8, 8), dtype=complex)
            single = np.array([[self.config['pin_potential'], 0, -1, 0], [0, -self.config['pin_potential'], 0, -1], [-1, 0, 0, 0], [0, -1, 0, 0]])
            coupling[:, :4, :4] = -single
            coupling[:, 4:, 4:] = single
            interaction = pairing[self.candidates[remove], self.candidates[add]]
            coupling[:, 0, 5] -= interaction
            coupling[:, 4, 1] -= interaction
            coupling[:, 5, 0] -= interaction.conj()
            coupling[:, 1, 4] -= interaction.conj()
            update = np.linalg.solve(np.linalg.inv(coupling)[None] - joint_gram, joint_backward)
            correction = -np.imag(np.sum(joint_forward * update.transpose(0, 1, 3, 2), axis=3)) / np.pi
            outputs.append((observed[:, None, :] + correction).transpose(1, 2, 0))
        return np.stack(outputs, axis=1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--start', default='binary_1_3.json')
    parser.add_argument('--stride', type=int, default=3)
    parser.add_argument('--conditions', type=int, default=1)
    parser.add_argument('--steps', type=int, default=500)
    parser.add_argument('--sigma', type=float, default=0)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--anneal', action='store_true')
    arguments = parser.parse_args()
    model = FlipModel(stride=arguments.stride, conditions=list(range(arguments.conditions)))
    pattern = np.asarray(json.loads((OUT / arguments.start).read_text())['pattern'])
    if arguments.check:
        started = time.time()
        observed, flipped = model.calculate_flips(pattern)
        print('TIME', time.time() - started, flush=True)
        for candidate in [0, 25, 64, 131]:
            changed = pattern.copy()
            changed[candidate] = 1 - changed[candidate]
            check = response(model.config, changed)[model.conditions][:, :, model.selection]
            print('ERROR', candidate, np.max(np.abs(check - flipped[candidate])), flush=True)
        return
    rng = np.random.default_rng(arguments.seed)
    best = np.inf
    current_score = np.inf
    last_changed = np.full(len(pattern), -100)
    started = time.time()
    previous = -1
    best_pattern = pattern.copy()
    for step in range(arguments.steps):
        observed, flipped = model.calculate_flips(pattern)
        errors = (flipped - model.target[None]) / model.scales[None]
        own_error = (observed - model.target) / model.scales
        raw_score = np.mean(own_error ** 2)
        sigma = arguments.sigma
        if arguments.anneal:
            sigma *= max(0, 1 - (step % 1000) / 600)
        if sigma:
            errors = gaussian_filter1d(errors, sigma, axis=3)
            own_error = gaussian_filter1d(own_error, sigma, axis=2)
        costs = np.mean(errors ** 2, axis=(1, 2, 3))
        current_score = np.mean(own_error ** 2)
        if pattern.sum() == model.config['normal_site_count']:
            try:
                validate_design(model.config, pattern)
                feasible = True
            except ValueError:
                feasible = False
            if raw_score < best and feasible:
                best = raw_score
                best_pattern = pattern.copy()
                np.save(OUT / f'discrete_{arguments.seed}_best.npy', pattern)
                (OUT / f'discrete_{arguments.seed}_best.json').write_text(json.dumps({'pattern': pattern.tolist()}) + '\n')
                print('BEST', step, np.sqrt(best), 'feasible', feasible, 'time', round(time.time() - started, 1), flush=True)
                if feasible:
                    (OUT / f'discrete_{arguments.seed}_feasible.json').write_text(json.dumps({'pattern': pattern.tolist()}) + '\n')
                if best < .06 ** 2:
                    config, target = __import__('spectral').load_problem(__import__('invert').ROOT / 'input')
                    metrics = discrepancies(config, response(config, pattern), target)
                    print('FULL', metrics, flush=True)
                    if metrics['core_score'] >= .96 and metrics['worst_family_score'] >= .94:
                        (OUT / 'design.json').write_text(json.dumps({'pattern': pattern.tolist()}) + '\n')
                        (OUT / 'match.json').write_text(json.dumps(metrics) + '\n')
                        return
            eligible = np.ones(len(pattern), dtype=bool)
        elif pattern.sum() > model.config['normal_site_count']:
            eligible = pattern == 1
        else:
            eligible = pattern == 0
        eligible &= step - last_changed > (1 if arguments.anneal else 3 + step // 100 % 8)
        if previous >= 0:
            eligible[previous] = False
        costs[~eligible] = np.inf
        temperature = .002 * (1 + step // 50 % 5)
        if arguments.anneal:
            temperature = .02 * (.00001 / .02) ** ((step % 1000) / 999)
        noisy_costs = costs - rng.gumbel(size=len(pattern)) * temperature
        chosen = int(np.argmin(noisy_costs))
        previous = chosen
        last_changed[chosen] = step
        pattern[chosen] = 1 - pattern[chosen]
        if step % 10 == 0:
            print('STEP', step, 'error', np.sqrt(current_score), 'next', np.sqrt(costs[chosen]), 'best', np.sqrt(best), 'time', round(time.time() - started, 1), flush=True)
        if arguments.anneal and step % 1000 == 999:
            pattern = best_pattern.copy()
            last_changed[:] = -100
            previous = -1


if __name__ == '__main__':
    main()
