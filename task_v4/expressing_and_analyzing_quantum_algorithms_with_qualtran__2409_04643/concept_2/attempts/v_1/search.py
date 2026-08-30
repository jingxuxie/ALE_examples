import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ASSETS = Path(os.environ['ASSETS'])
sys.path.insert(0, str(ASSETS / 'workspace'))
from target_method import fft_complementary_polynomial, qsp_phase_factors, rotation_matrix
from checker import audit_pair, exact_residual


def fast_angles(polynomial, complement, diagnostics=False):
    state = np.array([polynomial, complement])
    length = len(polynomial)
    theta = np.zeros(length)
    phi = np.zeros(length)
    margin = float('inf')
    stages = []
    for degree in reversed(range(length)):
        leading, other = state[:, degree]
        product = leading * np.conj(other)
        margin = min(margin, abs(other), abs(product))
        theta[degree] = np.arctan2(abs(other), abs(leading))
        phi[degree] = np.angle(product) if abs(other) > 1e-10 and abs(product) > 1e-10 else 0.0
        if degree:
            state = rotation_matrix(theta[degree], phi[degree], 0).conj().T @ state
            if diagnostics:
                stages.append((degree, abs(leading), abs(other), abs(product), abs(state[0, 0]), abs(state[1, -1])))
            state = np.array([state[0, 1:degree + 1], state[1, :degree]])
        else:
            lambd = np.angle(other) if abs(other) > 1e-10 else 0.0
    if diagnostics:
        return (theta, phi, lambd), margin, stages
    return (theta, phi, lambd), margin


def quick_error(polynomial, complement, angles):
    theta, phi, lambd = angles
    top = np.array([np.exp(1j * (phi[0] + lambd)) * np.cos(theta[0])])
    bottom = np.array([np.exp(1j * lambd) * np.sin(theta[0])])
    for degree in range(1, len(theta)):
        shifted = np.pad(top, (1, 0))
        padded = np.pad(bottom, (0, 1))
        top = np.exp(1j * phi[degree]) * (np.cos(theta[degree]) * shifted + np.sin(theta[degree]) * padded)
        bottom = np.sin(theta[degree]) * shifted - np.cos(theta[degree]) * padded
    actual = np.concatenate((top, bottom))
    target = np.concatenate((polynomial, complement))
    overlap = np.vdot(target, actual)
    common = overlap / abs(overlap) if overlap else 1
    return np.linalg.norm(actual - common * target)


def quick_audit(polynomial, full=False):
    records = []
    for resolution in ((4096, 8192, 16384) if full else (4096,)):
        for gauge in ((0, 1) if full else (0,)):
            transformed = polynomial.copy()
            if gauge:
                transformed *= np.exp(1j * (0.3125 + 0.2718281828459045 * np.arange(len(polynomial))))
            complement = fft_complementary_polynomial(transformed, tolerance=0, num_modes=resolution)
            angles, margin = fast_angles(transformed, complement)
            error = quick_error(transformed, complement, angles)
            records.append((resolution, gauge, error, margin))
    return records


def save_candidate(polynomial, path):
    certificate = 0.8 * fft_complementary_polynomial(polynomial / 0.8, tolerance=0, num_modes=65536)
    data = {key: [[float(value.real), float(value.imag)] for value in array] for key, array in [('P', polynomial), ('H', certificate)]}
    Path(path).write_text(json.dumps(data) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=1000)
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--degree', type=int, default=48)
    parser.add_argument('--kind', default='random')
    parser.add_argument('--output', default='search_best.json')
    args = parser.parse_args()
    best = 0
    started = time.monotonic()
    energies = []
    for seed in range(args.start, args.start + args.count):
        rng = np.random.default_rng(seed)
        polynomial = np.exp(1j * rng.uniform(-np.pi, np.pi, args.degree + 1))
        if args.kind == 'amplitude':
            polynomial *= np.exp(rng.uniform(-1.2, 1.2, args.degree + 1))
        if args.kind == 'chirp':
            indices = np.arange(args.degree + 1)
            polynomial = np.exp(1j * (rng.uniform(0.01, 3) * indices ** 2 + rng.uniform(0.0, 0.5) * rng.standard_normal(len(indices))))
        polynomial *= 0.79 / np.max(np.abs(np.fft.fft(polynomial, 8192)))
        energy = np.vdot(polynomial, polynomial).real
        if not 0.08 <= energy <= 0.3:
            continue
        rms = np.sqrt(energy / len(polynomial))
        if np.min(np.abs(polynomial)) < 0.25 * rms or np.max(np.abs(polynomial)) > 4 * rms:
            continue
        if abs(np.sum(polynomial ** 2)) > 0.8 * energy:
            continue
        records = quick_audit(polynomial)
        error, margin = records[0][2:]
        if margin < 1e-8:
            continue
        if error > best:
            best = error
            save_candidate(polynomial, args.output)
            print(json.dumps({'seed': seed, 'error': error, 'margin': margin, 'energy': energy, 'elapsed': time.monotonic() - started}), flush=True)
            if error > 0.03:
                full = quick_audit(polynomial, full=True)
                print('FULL', full, flush=True)
                if all(row[2] >= 0.05 and row[3] >= 1e-8 for row in full):
                    print('TARGET', flush=True)
                    break
        if (seed - args.start) % 250 == 249:
            print('PROGRESS', seed, best, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
