import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(os.environ['ASSETS']) / 'workspace'))
from target_method import fft_complementary_polynomial, qsp_phase_factors, rotation_matrix
from checker import audit_pair, evaluate, exact_residual


def quick_phases(polynomial, complement):
    state = np.array([polynomial, complement])
    length = len(polynomial)
    theta = np.zeros(length)
    phi = np.zeros(length)
    margin = float('inf')
    lost = []
    for degree in reversed(range(length)):
        leading, other = state[:, degree]
        margin = min(margin, abs(other), abs(leading * other.conjugate()))
        theta[degree] = np.arctan2(abs(other), abs(leading))
        phi[degree] = np.angle(leading * other.conjugate())
        if degree == 0:
            lambd = np.angle(other)
        else:
            state = rotation_matrix(theta[degree], phi[degree], 0).conj().T @ state
            lost.append(abs(state[0, 0]))
            state = np.array([state[0, 1:], state[1, :-1]])
    return (theta, phi, lambd), margin, lost


def quick_error(polynomial, complement, angles):
    theta, phi, lambd = angles
    actual = rotation_matrix(theta[0], phi[0], lambd)[:, :1]
    for index in range(1, len(theta)):
        actual = rotation_matrix(theta[index], phi[index], 0) @ np.array([
            np.pad(actual[0], (1, 0)), np.pad(actual[1], (0, 1))])
    target = np.array([polynomial, complement])
    overlap = np.vdot(target, actual)
    return np.linalg.norm(actual - target * overlap / abs(overlap))


def analyze(polynomial, modes=4096):
    complement = fft_complementary_polynomial(polynomial, tolerance=0, num_modes=modes)
    angles, margin, lost = quick_phases(polynomial, complement)
    return quick_error(polynomial, complement, angles), margin, lost


def dump(polynomial, path):
    certificate = 0.8 * fft_complementary_polynomial(polynomial / 0.8, tolerance=0, num_modes=65536)
    data = {key: [[float(value.real), float(value.imag)] for value in values]
            for key, values in [('P', polynomial), ('H', certificate)]}
    Path(path).write_text(json.dumps(data) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    maximum = 0
    started = time.monotonic()
    for trial in range(args.count):
        degree = 12
        magnitudes = np.exp(rng.uniform(-1.0, 1.0, degree + 1)) if trial % 2 else np.ones(degree + 1)
        polynomial = magnitudes * np.exp(1j * rng.uniform(-np.pi, np.pi, degree + 1))
        polynomial *= rng.uniform(0.65, 0.799) / np.max(np.abs(np.fft.fft(polynomial, 4096)))
        energy = np.vdot(polynomial, polynomial).real
        if not 0.08 < energy < 0.30 or abs(np.sum(polynomial ** 2)) > 0.8 * energy:
            continue
        rms = np.sqrt(energy / len(polynomial))
        if min(abs(polynomial)) < 0.25 * rms or max(abs(polynomial)) > 4 * rms:
            continue
        error, margin, lost = analyze(polynomial)
        if error > maximum and margin >= 1e-8:
            maximum = error
            dump(polynomial, f'best-{args.seed}.json')
            print('BEST', args.seed, trial, error, margin, energy, 'lost', lost, 'time', time.monotonic() - started, flush=True)
        if trial % 1000 == 0:
            print('PROGRESS', args.seed, trial, maximum, time.monotonic() - started, flush=True)
        if maximum >= 0.1:
            records = audit_pair(polynomial)
            print('AUDIT', records, flush=True)
            if all(record['rms_error'] >= 0.05 and record['guard_valid'] and record['completion_valid'] for record in records):
                dump(polynomial, 'counterexample.json')
                print('SUCCESS', evaluate(Path.cwd()), flush=True)
                return
    print('DONE', args.seed, maximum, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
