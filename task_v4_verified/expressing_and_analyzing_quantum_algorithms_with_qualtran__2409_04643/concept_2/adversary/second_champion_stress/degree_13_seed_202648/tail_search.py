import json
import time
from pathlib import Path

import numpy as np

from search import error_fast, make_artifact, fft_complementary_polynomial, qsp_phase_factors, phase_guard_margin, audit_pair


def assess(polynomial):
    errors = []
    margins = []
    for modes in (4096, 8192, 16384):
        for gauge in (0, 1):
            transformed = polynomial.copy()
            if gauge:
                transformed *= np.exp(1j * (0.3125 + 0.2718281828459045 * np.arange(len(polynomial))))
            complement = fft_complementary_polynomial(transformed, tolerance=0, num_modes=modes)
            angles = qsp_phase_factors(transformed, complement)
            errors.append(error_fast(transformed, complement, angles))
            margins.append(phase_guard_margin(transformed, complement, *angles[:2]))
    return min(errors), min(margins), errors


def run():
    rng = np.random.default_rng(202648)
    started = time.monotonic()
    existing = json.loads(Path('counterexample.json').read_text())
    best = assess(np.array([complex(*pair) for pair in existing['P']]))[0]
    print('starting best', best, flush=True)
    for trial in range(5000):
        degree = 13
        phases = np.pi / 2 + np.pi * rng.integers(0, 2, degree + 1) + rng.normal(0, .12, degree + 1)
        polynomial = np.exp(1j * phases)
        magnitudes = rng.uniform(.6, 1.4, degree + 1)
        magnitudes[-2] = 0
        magnitudes[-1] = 0
        dominant = rng.uniform(.855, .89)
        leading = rng.uniform(.251, .275) / np.sqrt(degree + 1)
        magnitudes *= np.sqrt((1 - dominant - leading**2) / np.sum(magnitudes**2))
        magnitudes[-1] = leading
        polynomial *= magnitudes
        polynomial[-2] = np.sqrt(dominant)
        polynomial *= .77 / np.max(np.abs(np.fft.fft(polynomial, 4096)))
        energy = np.vdot(polynomial, polynomial).real
        rms = np.sqrt(energy / len(polynomial))
        if not .08 <= energy <= .30 or abs(np.sum(polynomial**2)) > .8 * energy:
            continue
        if np.min(np.abs(polynomial)) < .25 * rms:
            continue
        score, margin, errors = assess(polynomial)
        if score > best and margin >= 1e-8:
            best = score
            make_artifact(polynomial, 'tail_best.json')
            print(trial, 'min_error', score, 'guard', margin, 'energy', energy, 'errors', errors, 'time', time.monotonic() - started, flush=True)
            if score >= .05:
                make_artifact(polynomial)
            if score >= .20:
                print(json.dumps(audit_pair(polynomial), indent=2), flush=True)
                break
        if trial % 100 == 0:
            print('progress', trial, best, 'time', time.monotonic() - started, flush=True)


if __name__ == '__main__':
    run()
