import os

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
from pathlib import Path
import sys
import time

import numpy as np
from scipy.optimize import minimize

asset_dir = Path(__file__).resolve().parents[1] / "input"
if not (asset_dir / "gl_model.py").is_file():
    asset_dir = Path("/participant/input")
sys.path.insert(0, str(asset_dir))
from gl_model import load_case


def solve(model):
    best = model.initial.copy()
    best_energy = model.energy(best)
    generator = np.random.default_rng(104729)
    starts = [best, best * np.exp(0.6j * generator.standard_normal(model.shape))]
    for initial in starts:
        result = minimize(
            model.objective,
            model.pack(initial),
            jac=True,
            method="L-BFGS-B",
            options={"maxiter": 1100, "ftol": 1e-12, "gtol": 2e-6, "maxcor": 10},
        )
        field = model.unpack(result.x)
        energy = model.energy(field)
        if energy < best_energy:
            best_energy, best = energy, field
    return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    started = time.monotonic()
    model = load_case(args.input)
    field = solve(model)
    with open(args.output, "wb") as stream:
        np.savez_compressed(stream, psi=field)
    print("energy=%.12g gradient_rms=%.6g elapsed=%.3f" % (
        model.energy(field), model.gradient_rms(field), time.monotonic() - started
    ))


if __name__ == "__main__":
    main()
