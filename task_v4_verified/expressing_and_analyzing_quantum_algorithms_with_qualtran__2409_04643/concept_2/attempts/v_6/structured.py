import argparse
import time

import numpy as np

from robust_search import score
from search import dump


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=6000)
    parser.add_argument('--count', type=int, default=100000)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    maximum = 0.0001
    started = time.monotonic()
    for trial in range(args.count):
        polynomial = 1j * rng.choice([-1, 1], size=13).astype(complex)
        polynomial[11] = 13.5 if trial % 2 else 13.65625
        polynomial[10] = 3.75j if trial % 2 else 3.25j
        polynomial[12] = 1j
        scale = rng.integers(41, 78) / 2048 if trial % 3 else rng.uniform(0.0197, 0.022)
        polynomial *= scale
        if trial % 4:
            angle = rng.choice([0, np.pi / 2, np.pi, -np.pi / 2]) + rng.normal() * 10 ** rng.uniform(-17, -1)
            polynomial *= np.exp(1j * angle)
        energy = np.vdot(polynomial, polynomial).real
        if not 0.08 <= energy <= 0.30 or abs(np.sum(polynomial ** 2)) > 0.8 * energy:
            continue
        if min(abs(polynomial)) < 0.25 * np.sqrt(energy / 13):
            continue
        if max(abs(np.fft.fft(polynomial, 4096))) >= 0.798:
            continue
        minimum, errors = score(polynomial, maximum)
        if minimum > maximum:
            maximum = minimum
            dump(polynomial, f'structured-{args.seed}.json')
            print('BEST', args.seed, trial, maximum, errors, 'time', time.monotonic() - started, flush=True)
        if trial % 10000 == 0:
            print('PROGRESS', args.seed, trial, maximum, time.monotonic() - started, flush=True)
    print('DONE', args.seed, maximum, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
