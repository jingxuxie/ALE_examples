import argparse
import json
import time
from pathlib import Path

import numpy as np

from robust_search import score
from search import dump


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=9000)
    parser.add_argument('--count', type=int, default=500000)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    population = []
    signatures = set()
    for prefix in ['mutate', 'optimal', 'ulp']:
        for path in Path('.').glob(prefix + '-*.json'):
            polynomial = np.array([complex(*pair) for pair in json.loads(path.read_text())['P']])
            minimum, errors = score(polynomial, 0)
            population.append((minimum, polynomial, errors))
            signatures.add(polynomial.tobytes())
    population.sort(key=lambda item: item[0], reverse=True)
    maximum = population[0][0]
    started = time.monotonic()
    for trial in range(args.count):
        parent = population[rng.integers(min(len(population), 32))]
        polynomial = parent[1].copy()
        components = polynomial.view(np.float64)
        count = rng.choice([1, 1, 1, 2, 2, 3, 6, 13])
        for component in rng.choice(26, size=count, replace=False):
            steps = rng.choice([-1, 1]) * 2 ** rng.integers(0, 12)
            components[component] += steps * abs(np.spacing(components[component]))
        signature = polynomial.tobytes()
        if signature in signatures:
            continue
        minimum, errors = score(polynomial, maximum * 0.88)
        if minimum > maximum * 0.88:
            signatures.add(signature)
            population.append((minimum, polynomial, errors))
            population.sort(key=lambda item: item[0], reverse=True)
            population = population[:64]
        if minimum > maximum:
            maximum = minimum
            dump(polynomial, f'ulp-{args.seed}.json')
            print('BEST', args.seed, trial, maximum, errors, 'time', time.monotonic() - started, flush=True)
        if trial % 10000 == 0:
            print('PROGRESS', args.seed, trial, maximum, time.monotonic() - started, flush=True)
    print('DONE', args.seed, maximum, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
