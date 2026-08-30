"""A nominal-only global-kick optimizer, deliberately not robust control."""

import argparse
import json
import os
from pathlib import Path
import sys

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from simulator import DEPTH, fidelities, save_pulses, training_scenarios


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=32)
    parser.add_argument("--seed", type=int, default=148873)
    parser.add_argument("--mode", choices=("nominal", "random"), default="nominal")
    parser.add_argument("--iterations", type=int, default=80)
    args = parser.parse_args()
    if not 1 <= args.trials <= 10000:
        parser.error("trials must be in [1, 10000]")
    generator = np.random.default_rng(args.seed)
    scenarios = training_scenarios()
    if args.mode == "nominal":
        def objective(controls):
            return -float(fidelities(np.repeat(controls[:, None], 2, axis=1))[0])
        result = minimize(objective, generator.uniform(-np.pi, np.pi, DEPTH),
                          method="L-BFGS-B", bounds=[(-np.pi, np.pi)] * DEPTH,
                          options={"maxiter": args.iterations, "ftol": 1e-11})
        angles = np.repeat(result.x[:, None], 2, axis=1)
        save_pulses(args.output, angles)
        scores = fidelities(angles, scenarios)
        print(json.dumps({"mode": "nominal", "nominal_fidelity": float(fidelities(angles)[0]),
                          "training_min_fidelity": float(scores.min()), "nfev": int(result.nfev),
                          "iterations": int(result.nit), "submission": str(args.output)}, indent=2))
        return
    candidates = [np.zeros((DEPTH, 2)), np.full((DEPTH, 2), np.pi / 2),
                  np.repeat(np.linspace(np.pi / 2, 0, DEPTH)[:, None], 2, axis=1)]
    candidates.extend(generator.uniform(-np.pi, np.pi, (args.trials, DEPTH, 2)))
    best_score = -1.0
    for angles in candidates:
        scores = fidelities(angles, scenarios)
        score = float(np.min(scores))
        if score > best_score:
            best_score = score
            best_angles = angles.copy()
    save_pulses(args.output, best_angles)
    print(json.dumps({"training_min_fidelity": best_score, "candidates": len(candidates),
                      "submission": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
