import argparse
import json
import time
from pathlib import Path

import numpy as np

from search import dump, quick_error
from checker import audit_pair, evaluate
from target_method import fft_complementary_polynomial, qsp_phase_factors, phase_guard_margin, rotation_matrix


def fast_error(polynomial, complement):
    state = np.array([polynomial, complement])
    loss = 0.0
    for degree in reversed(range(len(polynomial))):
        leading, other = state[:, degree]
        product = leading * np.conj(other)
        if np.abs(other) < 1e-8 or np.abs(product) < 1e-8:
            return 0.0
        if degree:
            theta = np.arctan2(np.abs(other), np.abs(leading))
            phi = np.angle(product)
            state = rotation_matrix(theta, phi, 0).conj().T @ state
            loss += np.abs(state[0, 0]) ** 2 + np.abs(state[1, -1]) ** 2
            state = np.array([state[0, 1:], state[1, :-1]])
    normalization = np.linalg.norm(state) - 1.0
    return np.sqrt(loss + normalization ** 2)


def score(polynomial, cutoff):
    errors = []
    for modes, gauge in [(8192, 0), (16384, 0), (16384, 1), (8192, 1), (4096, 0), (4096, 1)]:
        transformed = polynomial.copy()
        if gauge:
            transformed *= np.exp(1j * (0.3125 + 0.2718281828459045 * np.arange(len(polynomial))))
        complement = fft_complementary_polynomial(transformed, tolerance=0, num_modes=modes)
        error = fast_error(transformed, complement)
        errors.append(error)
        if error < cutoff:
            return 0, errors
    return min(errors), errors


def generate(rng):
    polynomial = 1j * rng.choice([-1, 1], size=13).astype(complex)
    dominant = rng.uniform(13.3, 13.68)
    secondary = np.sqrt(rng.uniform(207.7, 207.99) - 11 - dominant ** 2)
    polynomial[11] = dominant
    polynomial[10] = secondary * 1j
    polynomial[12] = 1j
    jitter = rng.uniform(0, 0.6)
    polynomial *= np.exp(1j * rng.uniform(-jitter, jitter, 13))
    polynomial *= np.exp(1j * (rng.uniform(-np.pi, np.pi) + rng.uniform(-0.12, 0.12) * np.arange(13)))
    energy = np.vdot(polynomial, polynomial).real
    if abs(np.sum(polynomial ** 2)) > 0.8 * energy:
        return None
    desired_energy = rng.uniform(0.080001, 0.12) if rng.random() < 0.75 else rng.uniform(0.12, 0.30)
    polynomial *= np.sqrt(desired_energy / energy)
    if np.max(abs(np.fft.fft(polynomial, 4096))) >= 0.799:
        return None
    return polynomial


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=1000)
    parser.add_argument('--count', type=int, default=100000)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    maximum = 0.0002
    started = time.monotonic()
    for trial in range(args.count):
        polynomial = generate(rng)
        if polynomial is None:
            continue
        minimum, errors = score(polynomial, maximum)
        if minimum > maximum:
            maximum = minimum
            dump(polynomial, f'robust-{args.seed}.json')
            print('BEST', args.seed, trial, minimum, errors, 'time', time.monotonic() - started, flush=True)
            if minimum >= 0.05:
                records = audit_pair(polynomial)
                if all(record['rms_error'] >= 0.05 and record['guard_valid'] and record['completion_valid'] for record in records):
                    dump(polynomial, 'counterexample.json')
                    print('SUCCESS', evaluate(Path.cwd()), flush=True)
                    return
        if trial % 10000 == 0:
            print('PROGRESS', args.seed, trial, maximum, time.monotonic() - started, flush=True)
    print('DONE', args.seed, maximum, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
