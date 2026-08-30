"""Weak, seeded random witness search, using only public assets."""

import argparse
import json
import os
import sys
import time
from pathlib import Path


os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "input"))
import numpy as np
from local_api import measure
from problem import BINS, Kernel, QUANTUM, validate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir")
    parser.add_argument("--trials", type=int, default=24)
    parser.add_argument("--seed", type=int, default=180103219)
    args = parser.parse_args()
    if not 1 <= args.trials <= 10000:
        raise ValueError("trials must be between 1 and 10000")
    started = time.monotonic()
    generator = np.random.default_rng(args.seed)
    kernel = Kernel()
    best = None
    best_margin = -1.0
    history = []
    for trial in range(args.trials):
        coefficients = generator.normal(size=24)
        integers = np.rint(coefficients / np.abs(coefficients).sum() * (QUANTUM - 48)).astype(np.int64)
        witness = {"version": 1, "bin": list(BINS)[int(generator.integers(0, 3))],
                   "band_start": int(generator.integers(1, 54)), "tilt": int(generator.integers(-4, 5)),
                   "curvature": int(generator.integers(-4, 5)),
                   "cosine": integers[:12].tolist(), "sine": integers[12:].tolist()}
        validate(witness)
        result = measure(witness, kernel=kernel)
        margin = result["worst_screen_margin"]
        history.append({"trial": trial, "bin": witness["bin"], "band_start": witness["band_start"],
                        "worst_screen_margin": margin})
        if margin > best_margin:
            best, best_margin = witness, margin
    destination = Path(args.output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "witness.json").write_text(json.dumps(best, indent=2) + "\n", encoding="utf-8")
    (destination / "search_log.json").write_text(json.dumps({"seed": args.seed, "trials": args.trials,
                                                             "best_screen_margin": best_margin,
                                                             "seconds": time.monotonic() - started,
                                                             "history": history}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(destination / "witness.json"), "best_screen_margin": best_margin}))


if __name__ == "__main__":
    main()
