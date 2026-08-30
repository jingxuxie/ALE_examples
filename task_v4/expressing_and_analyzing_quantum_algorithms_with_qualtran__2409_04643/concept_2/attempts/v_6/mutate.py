import argparse
import json
import time
from pathlib import Path

import numpy as np

from robust_search import score
from search import dump


def load(path):
    return np.array([complex(*pair) for pair in json.loads(path.read_text())['P']])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=5000)
    parser.add_argument('--count', type=int, default=100000)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    population = []
    for path in list(Path('.').glob('robust-*.json')) + list(Path('.').glob('mutate-*.json')) + list(Path('.').glob('structured-*.json')) + list(Path('.').glob('optimal-*.json')):
        polynomial = load(path)
        minimum, errors = score(polynomial, 0)
        population.append((minimum, polynomial, errors))
    population.sort(key=lambda item: item[0], reverse=True)
    maximum = population[0][0]
    started = time.monotonic()
    for trial in range(args.count):
        base = population[rng.integers(min(len(population), 16))][1]
        polynomial = base.copy()
        kind = trial % 5
        if kind == 0:
            polynomial *= np.exp(1j * rng.uniform(-np.pi, np.pi))
        elif kind == 1:
            polynomial *= np.exp(1j * rng.normal(size=13) * 10 ** rng.uniform(-16, -5))
        elif kind == 2:
            polynomial *= np.exp(1j * rng.normal(size=13) * 10 ** rng.uniform(-5, -0.5))
        elif kind == 3:
            polynomial *= np.exp(1j * rng.normal() * np.arange(13) * 10 ** rng.uniform(-15, -1))
        else:
            polynomial *= 1 + rng.normal() * 10 ** rng.uniform(-15, -1)
        energy = np.vdot(polynomial, polynomial).real
        if not 0.08 <= energy <= 0.30 or abs(np.sum(polynomial ** 2)) > 0.8 * energy:
            continue
        if min(abs(polynomial)) < 0.25 * np.sqrt(energy / 13):
            continue
        minimum, errors = score(polynomial, maximum * 0.92)
        if minimum > maximum * 0.92:
            population.append((minimum, polynomial, errors))
            population.sort(key=lambda item: item[0], reverse=True)
            population = population[:32]
        if minimum > maximum:
            maximum = minimum
            dump(polynomial, f'mutate-{args.seed}.json')
            print('BEST', args.seed, trial, maximum, errors, 'time', time.monotonic() - started, flush=True)
        if trial % 10000 == 0:
            print('PROGRESS', args.seed, trial, maximum, time.monotonic() - started, flush=True)
    print('DONE', args.seed, maximum, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
