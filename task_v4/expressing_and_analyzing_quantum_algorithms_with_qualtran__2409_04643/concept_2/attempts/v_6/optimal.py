import argparse
import time

import numpy as np

from robust_search import score
from search import dump


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=7000)
    parser.add_argument('--count', type=int, default=300000)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    maximum = 0.0005
    started = time.monotonic()
    for trial in range(args.count):
        total = 208 * (1 - 1e-7)
        fraction = 0.899998 if trial % 3 else rng.uniform(0.895, 0.899998)
        polynomial = 1j * rng.choice([-1, 1], size=13).astype(complex)
        polynomial[11] = np.sqrt(total * fraction)
        polynomial[10] = 1j * np.sqrt(total * (1 - fraction) - 11)
        polynomial[12] = 1j
        energy_target = 0.0800001 if trial % 4 == 0 else rng.uniform(0.0800001, 0.095)
        polynomial *= np.sqrt(energy_target / total)
        phase = rng.uniform(-np.pi, np.pi)
        polynomial *= np.exp(1j * phase)
        if trial % 2:
            polynomial *= np.exp(1j * rng.normal(size=13) * 10 ** rng.uniform(-15, -4))
        energy = np.vdot(polynomial, polynomial).real
        if abs(np.sum(polynomial ** 2)) > 0.8 * energy:
            continue
        minimum, errors = score(polynomial, maximum)
        if minimum > maximum:
            maximum = minimum
            dump(polynomial, f'optimal-{args.seed}.json')
            print('BEST', args.seed, trial, maximum, errors, 'time', time.monotonic() - started, flush=True)
        if trial % 10000 == 0:
            print('PROGRESS', args.seed, trial, maximum, time.monotonic() - started, flush=True)
    print('DONE', args.seed, maximum, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
