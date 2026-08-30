import argparse
import json
import math
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

ASSETS = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/expressing_and_analyzing_quantum_algorithms_with_qualtran__2409_04643/concept_2/participant')
sys.path.insert(0, str(ASSETS / 'workspace'))
from target_method import fft_complementary_polynomial, qsp_phase_factors, phase_guard_margin, rotation_matrix
from checker import audit_pair, exact_residual, evaluate


def fast_error(polynomial, complement, angles):
    theta, phi, lambd = angles
    top = np.array([np.exp(1j * (phi[0] + lambd)) * np.cos(theta[0])])
    bottom = np.array([np.exp(1j * lambd) * np.sin(theta[0])])
    for index in range(1, len(theta)):
        upper = np.pad(top, (1, 0))
        lower = np.pad(bottom, (0, 1))
        cosine = np.cos(theta[index])
        sine = np.sin(theta[index])
        top = np.exp(1j * phi[index]) * (cosine * upper + sine * lower)
        bottom = sine * upper - cosine * lower
    target = np.concatenate((polynomial, complement))
    actual = np.concatenate((top, bottom))
    overlap = np.vdot(target, actual)
    phase = overlap / abs(overlap) if overlap else 1
    return float(np.linalg.norm(actual - phase * target))


def assess(polynomial, modes=4096, gauge=0):
    transformed = polynomial.copy()
    if gauge:
        transformed *= np.exp(1j * (0.3125 + 0.2718281828459045 * np.arange(len(polynomial))))
    complement = fft_complementary_polynomial(transformed, tolerance=0, num_modes=modes)
    angles = qsp_phase_factors(transformed, complement)
    error = fast_error(transformed, complement, angles)
    return error, phase_guard_margin(transformed, complement, angles[0], angles[1])


def certificate(polynomial):
    return 0.8 * fft_complementary_polynomial(polynomial / 0.8, tolerance=0, num_modes=65536)


def save(polynomial, filename):
    companion = certificate(polynomial)
    payload = {name: [[float(value.real), float(value.imag)] for value in values]
               for name, values in [('P', polynomial), ('H', companion)]}
    Path(filename).write_text(json.dumps(payload))
    return float(exact_residual(polynomial, companion, Fraction(16, 25)))


def admissible(polynomial):
    energy = np.vdot(polynomial, polynomial).real
    rms = np.sqrt(energy / len(polynomial))
    return (0.08 <= energy <= 0.30
            and min(abs(polynomial)) >= 0.25 * rms
            and max(abs(polynomial)) <= 4 * rms
            and abs(np.sum(polynomial ** 2)) <= 0.8 * energy
            and max(abs(np.fft.fft(polynomial, 1024))) < 0.795)


def generate(rng, index):
    count = 13
    main_phase = rng.uniform(-np.pi, np.pi)
    phase = main_phase + np.pi / 2 + rng.integers(0, 2, count) * np.pi + rng.normal(0, 0.1, count)
    phase[-2] = main_phase
    weights = np.full(count, 0.062501 / count)
    weights[-2] = rng.uniform(0.875, 0.898)
    extra = rng.dirichlet(np.full(count - 2, 0.3))
    weights[:-2] += extra * (1 - np.sum(weights))
    amplitude = np.sqrt(weights)
    polynomial = amplitude * np.exp(1j * phase)
    energy = rng.uniform(0.08001, 0.28)
    polynomial *= math.sqrt(energy / np.vdot(polynomial, polynomial).real)
    return polynomial


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=174311)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    best = 0
    valid = 0
    started = time.monotonic()
    for index in range(args.count):
        polynomial = generate(rng, index)
        if not admissible(polynomial):
            continue
        valid += 1
        error, margin = assess(polynomial)
        if error <= best or margin < 1e-8:
            continue
        results = [assess(polynomial, modes, gauge) for modes in (4096, 8192, 16384) for gauge in (0, 1)]
        score = min(value[0] for value in results) if min(value[1] for value in results) >= 1e-8 else 0
        if score > best:
            best = score
            residual = save(polynomial, 'counterexample.json')
            print(json.dumps({'index': index, 'valid': valid, 'best': best, 'errors': [value[0] for value in results], 'margin': min(value[1] for value in results), 'certificate': residual, 'elapsed': time.monotonic() - started}), flush=True)
            if best >= 0.05 and residual < 1e-12:
                print(json.dumps(evaluate(Path.cwd()), indent=2), flush=True)
                break
    print('done', valid, best, time.monotonic() - started, flush=True)


if __name__ == '__main__':
    main()
