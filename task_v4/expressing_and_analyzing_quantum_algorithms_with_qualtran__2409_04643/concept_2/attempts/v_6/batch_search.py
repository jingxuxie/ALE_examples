import argparse
import json
import time
from pathlib import Path

import numpy as np

from robust_search import fast_error, score
from search import dump
from target_method import fft_complementary_polynomial


def batch_complement(polynomials, num_modes):
    padded = np.pad(polynomials, ((0, 0), (0, num_modes - 1)))
    values = np.fft.ifft(padded, norm='forward', axis=-1)
    logarithm = np.log(1 - np.abs(values) ** 2)
    modes = np.fft.fft(logarithm, norm='forward', axis=-1)
    modes[:, 0] *= 0.5
    modes[:, num_modes // 2 + 1:] = 0
    modes = np.fft.ifft(modes, norm='forward', axis=-1)
    return np.fft.fft(np.exp(modes), norm='forward', axis=-1)[:, :polynomials.shape[1]]


def physical_candidate(rng, spread=False):
    total = 208 * (1 - 1e-7)
    secondary = int(rng.integers(0, 11)) if spread else 10
    jitter = rng.uniform(0.001, 0.6)
    phases = np.pi / 2 + rng.normal(size=13) * jitter
    phases += rng.choice([0, np.pi], size=13)
    phases[10] = np.pi / 2 + rng.normal() * rng.uniform(0.001, 0.3)
    phases[11] = 0
    phases[12] = np.pi - phases[10]
    directions = np.exp(1j * phases)
    secondary_phase = directions[secondary] ** 2
    slope = 1 - secondary_phase
    intercept = (total - 11) * secondary_phase + sum(directions[index] ** 2 for index in range(13) if index not in (secondary, 11))
    linear = np.real(slope * intercept.conjugate())
    discriminant = linear ** 2 - abs(slope) ** 2 * (abs(intercept) ** 2 - (0.8 * total) ** 2)
    dominant_energy = (-linear + np.sqrt(max(0, discriminant))) / abs(slope) ** 2
    dominant_energy = min(total - 12, dominant_energy) * (1 - 1e-7)
    polynomial = directions.copy()
    polynomial[11] = np.sqrt(dominant_energy)
    polynomial[secondary] *= np.sqrt(total - 11 - dominant_energy)
    polynomial *= np.sqrt(rng.uniform(0.0800001, 0.087) / total)
    polynomial *= np.exp(1j * rng.uniform(-np.pi, np.pi))
    return polynomial


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=10000)
    parser.add_argument('--batches', type=int, default=10000)
    parser.add_argument('--batch-size', type=int, default=128)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--physical', action='store_true')
    parser.add_argument('--spread', action='store_true')
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    population = []
    for prefix in ['mutate', 'optimal', 'ulp', 'batch']:
        for path in Path('.').glob(prefix + '-*.json'):
            polynomial = np.array([complex(*pair) for pair in json.loads(path.read_text())['P']])
            minimum, errors = score(polynomial, 0)
            population.append((minimum, polynomial, errors))
    population.sort(key=lambda item: item[0], reverse=True)
    if args.check:
        polynomials = np.array([item[1] for item in population])
        for resolution in (4096, 8192, 16384):
            complements = batch_complement(polynomials, resolution)
            for index, polynomial in enumerate(polynomials):
                scalar = fft_complementary_polynomial(polynomial, tolerance=0, num_modes=resolution)
                print('CHECK', resolution, index, np.array_equal(scalar, complements[index]), max(abs(scalar - complements[index])), flush=True)
        return
    maximum = 0.0005 if args.physical else population[0][0]
    started = time.monotonic()
    gauge_factor = np.exp(1j * (0.3125 + 0.2718281828459045 * np.arange(13)))
    for batch in range(args.batches):
        if args.physical:
            polynomials = np.array([physical_candidate(rng, args.spread) for _ in range(args.batch_size)])
        else:
            polynomials = np.array([population[rng.integers(min(len(population), 32))][1] for _ in range(args.batch_size)])
            for polynomial in polynomials:
                components = polynomial.view(np.float64)
                count = rng.choice([1, 1, 2, 2, 3, 6, 13, 26])
                for component in rng.choice(26, size=count, replace=False):
                    steps = rng.choice([-1, 1]) * 2 ** rng.integers(0, 15)
                    components[component] += steps * abs(np.spacing(components[component]))
        indices = np.arange(len(polynomials))
        minimum = np.full(len(polynomials), np.inf)
        for modes, gauge in [(8192, 0), (16384, 0), (16384, 1), (8192, 1), (4096, 0), (4096, 1)]:
            if len(indices) == 0:
                break
            transformed = polynomials[indices].copy()
            if gauge:
                transformed *= gauge_factor
            complements = batch_complement(transformed, modes)
            errors = np.array([fast_error(polynomial, complement) for polynomial, complement in zip(transformed, complements)])
            minimum[indices] = np.minimum(minimum[indices], errors)
            indices = indices[errors >= maximum * 0.90]
        for index in indices:
            value, errors = score(polynomials[index], maximum * 0.90)
            if value >= maximum * 0.90:
                population.append((value, polynomials[index].copy(), errors))
            if value > maximum:
                maximum = value
                prefix = 'physical' if args.physical else 'batch'
                dump(polynomials[index], f'{prefix}-{args.seed}.json')
                print('BEST', args.seed, batch, maximum, errors, 'time', time.monotonic() - started, flush=True)
        population.sort(key=lambda item: item[0], reverse=True)
        population = population[:64]
        if batch % 100 == 0:
            print('PROGRESS', args.seed, batch, maximum, 'survivors', len(indices), time.monotonic() - started, flush=True)
    print('DONE', args.seed, maximum, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
