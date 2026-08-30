import os

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
from pathlib import Path
import sys
import time

import numpy as np

asset_dir = Path(__file__).resolve().parents[1] / "input"
if not (asset_dir / "gl_model.py").is_file():
    asset_dir = Path("/participant/input")
sys.path.insert(0, str(asset_dir))
from gl_model import load_case


def solve(model):
    return model.initial.copy()


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
