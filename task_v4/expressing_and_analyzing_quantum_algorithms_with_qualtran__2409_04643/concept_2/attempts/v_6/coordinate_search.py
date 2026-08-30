import argparse
import json
import time
from pathlib import Path

import numpy as np

from batch_search import batch_complement
from robust_search import fast_error, score
from search import dump


CONFIGURATIONS = [(8192, 0), (16384, 0), (16384, 1), (8192, 1), (4096, 0), (4096, 1)]


def all_errors(polynomials):
    result = np.zeros((len(polynomials), 6))
    factor = np.exp(1j * (0.3125 + 0.2718281828459045 * np.arange(13)))
    for column, (modes, gauge) in enumerate(CONFIGURATIONS):
        transformed = polynomials.copy()
        if gauge:
            for row in transformed:
                row *= factor
        complements = batch_complement(transformed, modes)
        result[:, column] = [fast_error(polynomial, complement) for polynomial, complement in zip(transformed, complements)]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=13000)
    parser.add_argument('--rounds', type=int, default=10000)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    candidates = []
    for prefix in ['ulp', 'batch', 'surrogate', 'coordinate']:
        for path in Path('.').glob(prefix + '-*.json'):
            polynomial = np.array([complex(*pair) for pair in json.loads(path.read_text())['P']])
            minimum, errors = score(polynomial, 0)
            candidates.append((minimum, polynomial, np.array(errors)))
    maximum, polynomial, baseline_errors = max(candidates, key=lambda item: item[0])
    powers = [1, 2, 4, 8, 16, 32, 64, 128, 256, 1024, 8192, 65536]
    power_index = 0
    started = time.monotonic()
    for iteration in range(args.rounds):
        steps = powers[power_index]
        polynomials = np.repeat(polynomial[None, :], 52, axis=0)
        components = polynomials.view(np.float64)
        for component in range(26):
            spacing = abs(np.spacing(components[0, component]))
            components[2 * component, component] += steps * spacing
            components[2 * component + 1, component] -= steps * spacing
        errors = all_errors(polynomials)
        minima = np.min(errors, axis=-1)
        best_index = np.argmax(minima)
        best = (minima[best_index], polynomials[best_index], errors[best_index])
        if best[0] <= maximum:
            predicted = errors[:, None, :] + errors[None, :, :] - baseline_errors
            pair_score = np.min(predicted, axis=-1)
            for index in range(52):
                pair_score[index, :index + 1] = -1
                pair_score[index, 2 * (index // 2):2 * (index // 2) + 2] = -1
            pairs = np.argpartition(pair_score.ravel(), -64)[-64:]
            pair_polynomials = np.repeat(polynomial[None, :], len(pairs), axis=0)
            pair_components = pair_polynomials.view(np.float64)
            for index, pair in enumerate(pairs):
                first, second = divmod(int(pair), 52)
                pair_components[index, first // 2] = components[first, first // 2]
                pair_components[index, second // 2] = components[second, second // 2]
            pair_errors = all_errors(pair_polynomials)
            minima = np.min(pair_errors, axis=-1)
            best_index = np.argmax(minima)
            if minima[best_index] > best[0]:
                best = (minima[best_index], pair_polynomials[best_index], pair_errors[best_index])
        if best[0] > maximum:
            confirmed, confirmed_errors = score(best[1], 0)
            if confirmed > maximum:
                maximum = confirmed
                polynomial = best[1].copy()
                baseline_errors = np.array(confirmed_errors)
                power_index = 0
                dump(polynomial, f'coordinate-{args.seed}.json')
                print('BEST', args.seed, iteration, steps, maximum, confirmed_errors, 'time', time.monotonic() - started, flush=True)
                continue
        power_index = (power_index + 1) % len(powers)
        if power_index == 0:
            powers = [1] + [int(value) for value in np.ceil(2.0 ** rng.uniform(0, 22, size=11))]
            print('CYCLE', args.seed, iteration, maximum, time.monotonic() - started, flush=True)
    print('DONE', args.seed, maximum, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
