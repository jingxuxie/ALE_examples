"""Derivative-free private calibration with explicit pulse perturbations."""

import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from simulator import compare


def family(knots, depth=36, epsilon=0.002):
    grid = np.linspace(0, 1, depth)
    angles = np.interp(grid, np.linspace(0, 1, len(knots)), knots)
    return [angles, angles - epsilon, angles + epsilon,
            angles + epsilon * (2 * grid - 1), angles - epsilon * (2 * grid - 1)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--evaluations", type=int, default=180)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    random = np.random.default_rng(options.seed)
    started = time.monotonic()
    best = float("inf")
    evaluations = 0
    initial = np.full(6, 1.30) + random.normal(0, 0.01, 6)
    def objective(knots):
        nonlocal best, evaluations
        if np.min(knots) < 0.12 or np.max(knots) > 1.45:
            return 100
        records = []
        for angles in family(knots):
            result = compare(angles)
            records.append({"metrics": result["metrics"]["zz1"], "result": result})
        error = min(record["metrics"]["error"] for record in records)
        spread = max(record["metrics"]["spread"] for record in records)
        value = spread + 2 * max(0, 0.15 - error)
        evaluations += 1
        if value < best:
            best = value
            record = {"seed": options.seed, "evaluations": evaluations,
                      "elapsed": time.monotonic() - started, "knots": knots.tolist(),
                      "depth": 36, "observable": "zz1", "error": error, "spread": spread,
                      "loss": value, "records": records}
            options.output.write_text(json.dumps(record, indent=2) + "\n")
            print(json.dumps({key: record[key] for key in ("evaluations", "elapsed", "knots", "error", "spread", "loss")}), flush=True)
        return value
    minimize(objective, initial, method="Nelder-Mead",
             options={"maxfev": options.evaluations, "xatol": 1e-6, "fatol": 1e-6,
                      "initial_simplex": np.vstack([initial] + [initial + 0.009 * row for row in np.eye(6)])})


if __name__ == "__main__":
    main()
