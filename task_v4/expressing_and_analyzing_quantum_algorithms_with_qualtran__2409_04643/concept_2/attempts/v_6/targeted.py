import argparse
import json
import time
from pathlib import Path

import numpy as np

from search import analyze, dump
from checker import audit_pair, evaluate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=10)
    parser.add_argument('--count', type=int, default=10000)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    maximum = 0
    started = time.monotonic()
    for trial in range(args.count):
        polynomial = np.exp(1j * rng.uniform(-np.pi, np.pi, 13))
        polynomial[11] *= rng.uniform(11.5, 13.6)
        secondary = rng.integers(0, 11)
        polynomial[secondary] *= rng.uniform(3.5, 5.5)
        if trial % 2:
            polynomial[secondary] = abs(polynomial[secondary]) * 1j * polynomial[11] / abs(polynomial[11])
        energy = np.vdot(polynomial, polynomial).real
        if min(abs(polynomial)) < 0.25 * np.sqrt(energy / len(polynomial)) or abs(np.sum(polynomial ** 2)) > 0.8 * energy:
            continue
        polynomial *= np.sqrt(rng.uniform(0.08, 0.30) / energy)
        if np.max(abs(np.fft.fft(polynomial, 4096))) > 0.795:
            continue
        error, margin, lost = analyze(polynomial)
        if error > maximum and margin >= 1e-8:
            maximum = error
            dump(polynomial, f'target-{args.seed}.json')
            print('BEST', args.seed, trial, error, margin, 'lost', lost, 'time', time.monotonic() - started, flush=True)
        if error >= 0.05 and margin >= 1e-8:
            records = audit_pair(polynomial)
            minimum = min(record['rms_error'] for record in records)
            print('AUDIT', args.seed, trial, minimum, [record['rms_error'] for record in records], flush=True)
            if all(record['rms_error'] >= 0.05 and record['guard_valid'] and record['completion_valid'] for record in records):
                dump(polynomial, 'counterexample.json')
                print('SUCCESS', evaluate(Path.cwd()), flush=True)
                return
        if trial % 1000 == 0:
            print('PROGRESS', args.seed, trial, maximum, time.monotonic() - started, flush=True)
    print('DONE', args.seed, maximum, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
