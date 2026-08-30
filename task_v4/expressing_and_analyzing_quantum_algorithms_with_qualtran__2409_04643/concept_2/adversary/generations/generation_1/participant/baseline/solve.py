import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from target_method import fft_complementary_polynomial


def candidate(seed=73000, degree=40):
    rng = np.random.default_rng(seed)
    polynomial = np.exp(1j * rng.uniform(-np.pi, np.pi, degree + 1))
    polynomial *= 0.78 / np.max(np.abs(np.fft.fft(polynomial, 65536)))
    certificate = 0.8 * fft_complementary_polynomial(polynomial / 0.8, tolerance=0, num_modes=65536)
    return {"P": [[float(value.real), float(value.imag)] for value in polynomial],
            "H": [[float(value.real), float(value.imag)] for value in certificate]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=73000)
    parser.add_argument("--degree", type=int, default=40)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(candidate(args.seed, args.degree)))


if __name__ == "__main__":
    main()
