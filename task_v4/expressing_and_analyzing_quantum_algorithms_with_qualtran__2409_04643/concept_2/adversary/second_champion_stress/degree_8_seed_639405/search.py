import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(os.environ['ASSETS']) / 'workspace'))
from target_method import fft_complementary_polynomial, qsp_phase_factors, rotation_matrix, phase_guard_margin
from checker import audit_pair, exact_residual


def error_fast(polynomial, complement, angles):
    theta, phi, lambd = angles
    state = rotation_matrix(theta[0], phi[0], lambd)[:, :1]
    for index in range(1, len(theta)):
        state = np.stack((np.pad(state[0], (1, 0)), np.pad(state[1], (0, 1))))
        state = rotation_matrix(theta[index], phi[index], 0) @ state
    target = np.array([polynomial, complement])
    overlap = np.vdot(target, state)
    return np.linalg.norm(state - overlap / abs(overlap) * target)


def make_artifact(polynomial, name='counterexample.json'):
    certificate = 0.8 * fft_complementary_polynomial(polynomial / 0.8, tolerance=0, num_modes=65536)
    data = {key: [[float(value.real), float(value.imag)] for value in array]
            for key, array in [('P', polynomial), ('H', certificate)]}
    Path(name).write_text(json.dumps(data, indent=2) + '\n')


def run(count, seed, degree):
    rng = np.random.default_rng(seed)
    best_error = 0.0
    started = time.monotonic()
    for trial in range(count):
        polynomial = np.exp(1j * rng.uniform(-np.pi, np.pi, degree + 1))
        if trial % 2:
            polynomial *= rng.uniform(0.3, 2, degree + 1)
        polynomial *= 0.785 / np.max(np.abs(np.fft.fft(polynomial, 2048)))
        energy = np.vdot(polynomial, polynomial).real
        rms = np.sqrt(energy / len(polynomial))
        if not .08 <= energy <= .30 or abs(np.sum(polynomial**2)) > .8 * energy:
            continue
        if np.min(np.abs(polynomial)) < .25 * rms:
            continue
        complement = fft_complementary_polynomial(polynomial, tolerance=0, num_modes=4096)
        angles = qsp_phase_factors(polynomial, complement)
        error = error_fast(polynomial, complement, angles)
        if error > best_error:
            best_error = error
            margin = phase_guard_margin(polynomial, complement, *angles[:2])
            print(trial, 'error', error, 'guard', margin, 'energy', energy, 'time', time.monotonic() - started, flush=True)
            make_artifact(polynomial)
        if trial % 1000 == 0:
            print('progress', trial, 'best', best_error, 'time', time.monotonic() - started, flush=True)
    print(json.dumps(audit_pair(polynomial), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=34857)
    parser.add_argument('--degree', type=int, default=14)
    args = parser.parse_args()
    run(args.count, args.seed, args.degree)
