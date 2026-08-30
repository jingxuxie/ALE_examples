import argparse
import json
import time

import numpy as np
from scipy.linalg import eigh
from scipy.ndimage import gaussian_filter1d

from optimize import Inverse, OUTPUT, binary, save_best, validate_design


class Swaps:
    def __init__(self, inverse):
        self.inverse = inverse
        self.sites = inverse.sites
        self.all_indices = np.concatenate([inverse.indices, inverse.indices + self.sites])
        self.selectors = np.eye(2 * self.sites, dtype=complex)[:, self.all_indices]
        self.pair_blocks = []
        for pairing in inverse.pairings:
            block = pairing[inverse.indices[:, None], inverse.indices[None, :]]
            self.pair_blocks.append(np.block([[np.zeros((64, 64)), block], [block.conj().T, np.zeros((64, 64))]]))

    def prepare(self, pattern):
        self.pattern = pattern.copy()
        amplitude = np.ones(self.sites)
        amplitude[self.inverse.indices] -= pattern
        changes = 1 - 2 * pattern
        self.changes = np.tile(changes, 2)
        self.amplitudes = np.tile(1 - pattern, 2)
        self.diagonal = self.inverse.config['pin_potential'] * np.concatenate([changes, -changes])
        greens = []
        lefts = []
        rights = []
        responses = []
        selected_columns = []
        for base, pairing in zip(self.inverse.bases, self.inverse.pairings):
            matrix = base.copy()
            matrix[self.inverse.indices, self.inverse.indices] += self.inverse.config['pin_potential'] * pattern
            matrix[self.inverse.indices + self.sites, self.inverse.indices + self.sites] -= self.inverse.config['pin_potential'] * pattern
            gap = pairing * amplitude[:, None] * amplitude[None, :]
            matrix[:self.sites, self.sites:] = gap
            matrix[self.sites:, :self.sites] = gap.conj().T
            eigenvalues, eigenvectors = eigh(matrix, check_finite=False, driver='evr', overwrite_a=True)
            columns = np.zeros((2 * self.sites, 128), dtype=complex)
            columns[self.all_indices, np.arange(128)] = self.diagonal
            columns[:self.sites, 64:] = -pairing[:, self.inverse.indices] * changes[None, :] * amplitude[:, None]
            columns[self.sites:, :64] = -pairing.conj()[:, self.inverse.indices] * changes[None, :] * amplitude[:, None]
            selected_columns.append(columns[self.all_indices])
            basis = np.concatenate([self.selectors, columns], axis=1)
            transformed = eigenvectors.conj().T @ basis
            probe_vectors = eigenvectors[self.inverse.probes]
            denominators = 1 / (self.inverse.energies[:, None] + 1j * self.inverse.config['broadening'] - eigenvalues[None, :])
            greens.append(np.asarray([transformed.conj().T @ (denominator[:, None] * transformed) for denominator in denominators]))
            lefts.append(np.asarray([(probe_vectors * denominator[None, :]) @ transformed for denominator in denominators]))
            rights.append(np.asarray([transformed.conj().T @ (denominator[:, None] * probe_vectors.conj().T) for denominator in denominators]))
            responses.append((np.abs(probe_vectors) ** 2) @ (-denominators.imag.T / np.pi))
        self.greens = np.asarray(greens)
        self.lefts = np.asarray(lefts)
        self.rights = np.asarray(rights)
        self.responses = np.asarray(responses)
        self.selected_columns = np.asarray(selected_columns)
        residual = self.inverse.residual(self.responses)
        self.error = np.sqrt(np.mean(residual ** 2))
        return self.error

    def evaluate(self, pairs, chunk_size=96, store=False):
        errors = []
        raw_errors = []
        residuals = []
        for offset in range(0, len(pairs), chunk_size):
            chunk = pairs[offset:offset + chunk_size]
            select = np.concatenate([chunk, chunk + 64], axis=1)
            basis_select = np.concatenate([select, select + 128], axis=1)
            squares = np.zeros(len(chunk))
            raw_squares = np.zeros(len(chunk))
            chunk_residuals = []
            rank = select.shape[1]
            for condition in range(len(self.inverse.conditions)):
                columns = self.selected_columns[condition][select[:, :, None], select[:, None, :]]
                correction = columns + columns.conj().transpose(0, 2, 1)
                amplitudes = self.amplitudes[select]
                changes = self.changes[select]
                factor = changes[:, :, None] * changes[:, None, :] - changes[:, :, None] * amplitudes[:, None, :] - amplitudes[:, :, None] * changes[:, None, :]
                correction -= self.pair_blocks[condition][select[:, :, None], select[:, None, :]] * factor
                correction[:, np.arange(rank), np.arange(rank)] -= self.diagonal[select]
                inverse_update = np.zeros((len(chunk), 2 * rank, 2 * rank), dtype=complex)
                inverse_update[:, :rank, rank:] = np.eye(rank)
                inverse_update[:, rank:, :rank] = np.eye(rank)
                inverse_update[:, rank:, rank:] = correction
                green = self.greens[condition][:, basis_select[:, :, None], basis_select[:, None, :]]
                left = self.lefts[condition][:, :, basis_select].transpose(0, 2, 1, 3)
                right = self.rights[condition][:, basis_select, :]
                solved = np.linalg.solve(inverse_update[None, :, :, :] - green, right)
                change = np.sum(left * solved.transpose(0, 1, 3, 2), axis=3)
                observed = self.responses[condition].T[:, None, :] - change.imag / np.pi
                target = self.inverse.target[condition].T[:, None, :]
                scales = self.inverse.scales[condition, :, 0][None, None, :]
                residual = (observed - target) / scales
                raw_squares += np.sum(residual ** 2, axis=(0, 2))
                if self.inverse.loss == 'log':
                    residual = np.log(observed / scales + 0.05) - np.log(target / scales + 0.05)
                elif self.inverse.loss == 'sqrt':
                    residual = 2 * (np.sqrt(observed / scales + 0.05) - np.sqrt(target / scales + 0.05))
                if self.inverse.smoothing:
                    residual = gaussian_filter1d(residual, self.inverse.smoothing, axis=0)
                if store:
                    chunk_residuals.append(residual.transpose(1, 0, 2).reshape(len(chunk), -1))
                squares += np.sum(residual ** 2, axis=(0, 2))
            errors.extend(np.sqrt(squares / self.inverse.target.size).tolist())
            raw_errors.extend(np.sqrt(raw_squares / self.inverse.target.size).tolist())
            if store:
                residuals.append(np.concatenate(chunk_residuals, axis=1))
        self.raw_errors = np.asarray(raw_errors)
        if store:
            self.residuals = np.concatenate(residuals, axis=0) / np.sqrt(self.inverse.target.size)
        return np.asarray(errors)

    def double_choices(self, pairs, errors, count=192):
        current = self.inverse.residual(self.responses).transpose(0, 2, 1).ravel() / np.sqrt(self.inverse.target.size)
        delta = self.residuals - current[None, :]
        predicted = 2 * (delta @ delta.T) + errors[:, None] ** 2 + errors[None, :] ** 2 - self.error ** 2
        invalid = (pairs[:, 0, None] == pairs[None, :, 0]) | (pairs[:, 1, None] == pairs[None, :, 1])
        predicted[invalid] = np.inf
        predicted[np.tril_indices(len(pairs))] = np.inf
        shortlist = min(count * 8, predicted.size)
        indices = np.argpartition(predicted.ravel(), shortlist)[:shortlist]
        indices = indices[np.argsort(predicted.ravel()[indices])]
        selected = []
        known = set()
        for index in indices:
            first, second = divmod(index, len(pairs))
            mutation = tuple(sorted(np.concatenate([pairs[first], pairs[second]])))
            if mutation not in known:
                known.add(mutation)
                selected.append(mutation)
                if len(selected) == count:
                    break
        return np.asarray(selected)

    def choices(self):
        occupied = np.flatnonzero(self.pattern)
        empty = np.flatnonzero(1 - self.pattern)
        pairs = np.stack(np.meshgrid(occupied, empty, indexing='ij'), axis=-1).reshape(-1, 2)
        return pairs


def feasible(inverse, pattern):
    try:
        validate_design(inverse.config, pattern)
        return True
    except ValueError:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', default='check')
    parser.add_argument('--stride', type=int, default=2)
    parser.add_argument('--conditions', type=int, default=3)
    parser.add_argument('--seed', type=int, default=444)
    parser.add_argument('--rounds', type=int, default=1000)
    parser.add_argument('--restart', type=int, default=8)
    parser.add_argument('--smoothing', type=float, default=0.0)
    parser.add_argument('--loss', default='linear')
    parser.add_argument('--initial', default='design.json')
    parser.add_argument('--global-restarts', action='store_true')
    arguments = parser.parse_args()
    inverse = Inverse(stride=arguments.stride, conditions=list(range(arguments.conditions)))
    inverse.smoothing = arguments.smoothing
    inverse.loss = arguments.loss
    swaps = Swaps(inverse)
    random = np.random.default_rng(arguments.seed)
    if arguments.initial == 'random':
        while True:
            pattern = binary(random.random(64))
            if feasible(inverse, pattern):
                break
    elif arguments.initial.endswith('.npz'):
        pattern = binary(np.load(OUTPUT / arguments.initial)['pattern'])
    else:
        pattern = np.asarray(json.loads((OUTPUT / arguments.initial).read_text())['pattern'], dtype=float)
    if arguments.mode == 'check':
        start = time.time()
        print('prepare error', swaps.prepare(pattern), 'time', time.time() - start, flush=True)
        pairs = swaps.choices()
        start = time.time()
        errors = swaps.evaluate(pairs)
        print('evaluate time', time.time() - start, flush=True)
        for chosen in [0, 100, 500, np.argmin(errors)]:
            changed = pattern.copy()
            changed[pairs[chosen]] = 1 - changed[pairs[chosen]]
            print('pair', pairs[chosen], 'woodbury', errors[chosen], 'actual', inverse.error(changed), flush=True)
        return
    best_pattern = pattern.copy()
    best_error = inverse.error(pattern)
    best_raw = float('inf')
    stale = 0
    tabu = {}
    start = time.time()
    for iteration in range(arguments.rounds):
        if (OUTPUT / 'STOP').exists():
            break
        current_error = swaps.prepare(pattern)
        pairs = swaps.choices()
        errors = swaps.evaluate(pairs)
        selected = None
        for choice in np.argsort(errors):
            changed = pattern.copy()
            changed[pairs[choice]] = 1 - changed[pairs[choice]]
            key = np.packbits(changed.astype(np.uint8)).tobytes()
            if key in tabu and tabu[key] > iteration and errors[choice] >= best_error:
                continue
            if feasible(inverse, changed):
                selected = choice
                break
        if selected is None:
            break
        chosen_error = errors[selected]
        chosen_raw = swaps.raw_errors[selected]
        tabu[np.packbits(pattern.astype(np.uint8)).tobytes()] = iteration + 16
        pattern[pairs[selected]] = 1 - pattern[pairs[selected]]
        stale += 1
        if chosen_error < best_error:
            best_pattern = pattern.copy()
            best_error = chosen_error
            stale = 0
            np.savez(OUTPUT / f'discrete_{arguments.seed}.npz', pattern=pattern, error=best_error)
        if chosen_raw < best_raw:
            best_raw = chosen_raw
            save_best(inverse, pattern)
        print('STEP', iteration, 'time', round(time.time() - start, 2), 'error', chosen_error, 'raw', chosen_raw, 'best', best_error, 'swap', pairs[selected].tolist(), 'stale', stale, flush=True)
        if chosen_raw < 0.035:
            break
        if stale >= arguments.restart:
            pattern = best_pattern.copy()
            if arguments.global_restarts:
                if random.random() < 0.6:
                    while True:
                        pattern = binary(random.random(64))
                        if feasible(inverse, pattern):
                            break
                else:
                    pattern = np.asarray(json.loads((OUTPUT / 'design.json').read_text())['pattern'], dtype=float)
                best_error = inverse.error(pattern)
                best_pattern = pattern.copy()
            for attempt in range(100):
                changed = pattern.copy()
                count = random.integers(2, 6)
                changed[random.choice(np.flatnonzero(pattern), count, replace=False)] = 0
                changed[random.choice(np.flatnonzero(1 - pattern), count, replace=False)] = 1
                if feasible(inverse, changed):
                    pattern = changed
                    break
            stale = 0
            tabu = {}
            print('RESTART', flush=True)


if __name__ == '__main__':
    main()
