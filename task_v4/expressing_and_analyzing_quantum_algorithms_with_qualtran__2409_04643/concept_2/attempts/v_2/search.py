import argparse
import json
import time
from pathlib import Path

import numpy as np

from checker import audit_pair, exact_residual
from target_method import fft_complementary_polynomial, qsp_phase_factors, rotation_matrix


def quick_error(polynomial, complement, angles):
    theta, phi, lambd = angles
    actual = rotation_matrix(theta[0], phi[0], lambd)[:, :1]
    for index in range(1, len(theta)):
        shifted = np.zeros((2, index + 1), dtype=complex)
        shifted[0, 1:] = actual[0]
        shifted[1, :-1] = actual[1]
        actual = rotation_matrix(theta[index], phi[index], 0) @ shifted
    target = np.array([polynomial, complement])
    overlap = np.vdot(target, actual)
    phase = overlap / abs(overlap) if overlap else 1
    return float(np.linalg.norm(actual - phase * target))


def quick_audit(polynomial, resolution=4096, gauge=0):
    transformed = polynomial.copy()
    if gauge:
        transformed *= np.exp(1j * (0.3125 + 0.2718281828459045 * np.arange(len(polynomial))))
    complement = fft_complementary_polynomial(transformed, tolerance=0, num_modes=resolution)
    angles = qsp_phase_factors(transformed, complement)
    return quick_error(transformed, complement, angles)


def serialize(polynomial):
    certificate = 0.8 * fft_complementary_polynomial(polynomial / 0.8, tolerance=0, num_modes=65536)
    return {"P": [[float(value.real), float(value.imag)] for value in polynomial],
            "H": [[float(value.real), float(value.imag)] for value in certificate]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--degree", type=int, default=48)
    parser.add_argument("--amplitudes", default="equal")
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    started = time.monotonic()
    best = 0
    valid = 0
    for iteration in range(args.count):
        polynomial = np.exp(1j * rng.uniform(-np.pi, np.pi, args.degree + 1))
        if args.amplitudes == "random":
            polynomial *= np.exp(rng.uniform(-1, 1, len(polynomial)))
        if args.amplitudes == "endpoints":
            polynomial[0] *= 3
            polynomial[-1] *= 0.5
        polynomial *= 0.79 / np.max(np.abs(np.fft.fft(polynomial, 8192)))
        energy = np.vdot(polynomial, polynomial).real
        if not 0.08 <= energy <= 0.30:
            continue
        if np.min(abs(polynomial)) < 0.25 * np.sqrt(energy / len(polynomial)):
            continue
        valid += 1
        error = quick_audit(polynomial)
        if error > best:
            best = error
            print(json.dumps({"iteration": iteration, "valid": valid, "best_first": best,
                              "energy": energy, "seconds": time.monotonic() - started}), flush=True)
            Path(f"best_{args.seed}.json").write_text(json.dumps(serialize(polynomial)))
        if error > 0.02:
            errors = [error] + [quick_audit(polynomial, resolution, gauge)
                               for resolution, gauge in ((4096, 1), (8192, 0), (8192, 1), (16384, 0), (16384, 1))]
            print(json.dumps({"iteration": iteration, "errors": errors}), flush=True)
            if min(errors) >= 0.05:
                records = audit_pair(polynomial)
                Path(f"hit_{args.seed}_{iteration}.json").write_text(json.dumps(serialize(polynomial)))
                Path(f"hit_{args.seed}_{iteration}_report.json").write_text(json.dumps(records, indent=2))
                print(json.dumps({"hit": iteration, "records": records}), flush=True)
                if all(record["completion_valid"] and record["guard_valid"] for record in records):
                    Path("counterexample.json").write_text(json.dumps(serialize(polynomial)))
                    break
        if iteration % 1000 == 999:
            print(json.dumps({"iteration": iteration, "valid": valid, "best_first": best,
                              "seconds": time.monotonic() - started}), flush=True)


if __name__ == "__main__":
    main()
