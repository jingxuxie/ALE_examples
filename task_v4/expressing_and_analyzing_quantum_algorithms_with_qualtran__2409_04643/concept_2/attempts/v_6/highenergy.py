import argparse
import time

import numpy as np

from robust_search import score
from search import dump


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=8000)
    parser.add_argument('--count', type=int, default=200000)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    maximum = 0.0002
    started = time.monotonic()
    for trial in range(args.count):
        total = 208 * (1 - 1e-7)
        fraction = rng.uniform(0.89, 0.899999)
        polynomial = 1j * rng.choice([-1, 1], size=13).astype(complex)
        polynomial[11] = np.sqrt(total * fraction)
        polynomial[10] = 1j * np.sqrt(total * (1 - fraction) - 11)
        polynomial[12] = 1j
        polynomial *= np.exp(1j * rng.uniform(-np.pi, np.pi))
        if trial % 2:
            polynomial *= np.exp(1j * rng.normal(size=13) * 10 ** rng.uniform(-15, -4))
        scale = rng.uniform(0.795, 0.799) / max(abs(np.fft.fft(polynomial, 4096)))
        scale = min(scale, np.sqrt(0.299999 / total))
        polynomial *= scale
        energy = np.vdot(polynomial, polynomial).real
        if abs(np.sum(polynomial ** 2)) > 0.8 * energy:
            continue
        minimum, errors = score(polynomial, maximum)
        if minimum > maximum:
            maximum = minimum
            dump(polynomial, f'highenergy-{args.seed}.json')
            print('BEST', args.seed, trial, maximum, errors, 'energy', energy, 'time', time.monotonic() - started, flush=True)
        if trial % 10000 == 0:
            print('PROGRESS', args.seed, trial, maximum, time.monotonic() - started, flush=True)
    print('DONE', args.seed, maximum, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
