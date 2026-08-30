import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from scipy.linalg import null_space
from scipy.optimize import Bounds, LinearConstraint, NonlinearConstraint, minimize

from model import GeneralModel


def repair(model, rounded, single_quadratic):
    if not np.array_equal(model.full_constraint @ rounded, model.integer_target):
        return {"status": "rounding_changed_linear_constraints",
                "max_error": float(np.max(abs(model.full_constraint @ rounded - model.integer_target)))}
    import itertools
    moves = []
    for first_gate in range(32):
        for second_gate in range(first_gate + 1, 32):
            if set(model.supports[first_gate]) != set(model.supports[second_gate]):
                continue
            for first_label, second_label in itertools.combinations(model.supports[first_gate], 2):
                for amount in (-1, 1):
                    change = np.zeros(192, dtype=int)
                    change[model.lookup[first_gate, first_label]] = amount
                    change[model.lookup[first_gate, second_label]] = -amount
                    change[model.lookup[second_gate, first_label]] = -amount
                    change[model.lookup[second_gate, second_label]] = amount
                    trial = rounded + change
                    if np.all(trial >= model.lower) and np.all(trial <= model.upper):
                        moves.append(change)
    moves = np.vstack((np.zeros(192, dtype=int), np.array(moves)))
    matches = np.ones((len(moves), len(moves)), dtype=bool)
    for quadratic, target in ((model.quadratic, 32640), (single_quadratic, 28800)):
        products = moves @ quadratic
        deltas = 2 * products @ rounded + np.sum(products * moves, axis=1)
        total = deltas[:, None] + deltas[None, :] + 2 * products @ moves.T
        matches &= total == target - int(rounded @ quadratic @ rounded)
    candidates = []
    for first_index, second_index in np.argwhere(matches):
        if first_index > second_index:
            continue
        trial = rounded + moves[first_index] + moves[second_index]
        if np.any(trial < model.lower) or np.any(trial > model.upper):
            continue
        metrics = model.run(trial / 60)
        candidates.append((metrics["r"], trial, metrics))
    if not candidates:
        return {"status": "no_one_or_two_move_repair", "moves": len(moves),
                "rounded_total_overlap": int(rounded @ model.quadratic @ rounded),
                "rounded_single_overlap": int(rounded @ single_quadratic @ rounded)}
    _, winner, metrics = min(candidates, key=lambda item: item[0])
    return {"status": "repaired", "moves": len(moves), "candidates": len(candidates),
            "witness": model.encode(winner), "family_calibrations": model.family_calibrations(winner),
            "metrics": {key: value for key, value in metrics.items() if key != "polarizations"},
            "passes_nominal": metrics["bias"] >= 0.0244 and metrics["max_residual"] <= 0.004 and metrics["end_signal"] >= 0.005}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("champion")
    parser.add_argument("--starts", type=int, default=8)
    arguments = parser.parse_args()
    started = time.perf_counter()
    raw = Path(arguments.champion).read_bytes()
    model = GeneralModel()
    champion = model.decode(json.loads(raw)) / 60
    single_quadratic = model.quadratic.copy()
    single_quadratic[72:, :] = 0
    single_quadratic[:, 72:] = 0
    constraints = [LinearConstraint(model.constraint, model.target, model.target),
                   NonlinearConstraint(model.overlap, model.pair_target, model.pair_target,
                                       jac=model.overlap_gradient),
                   NonlinearConstraint(lambda point: point @ single_quadratic @ point / 24, 1 / 3, 1 / 3,
                                       jac=lambda point: 2 * single_quadratic @ point / 24)]
    directions = null_space(model.constraint)
    generator = np.random.default_rng(17)
    results = []
    for start_index in range(arguments.starts):
        if start_index == 0:
            initial = champion
        else:
            direction = directions @ generator.normal(size=directions.shape[1])
            allowed = np.minimum((model.upper / 60 - model.uniform) / np.maximum(direction, 1e-100),
                                 (model.uniform - model.lower / 60) / np.maximum(-direction, 1e-100))
            initial = model.uniform + 0.8 * float(np.min(allowed)) * direction
        run_started = time.perf_counter()
        optimized = minimize(lambda point: model.run(point, gradient=True, residual_limit=0.004),
                             initial, method="SLSQP", jac=True, bounds=Bounds(model.lower / 60, model.upper / 60),
                             constraints=constraints, options={"maxiter": 500, "ftol": 1e-11, "disp": False})
        result = {"start": start_index, "success": bool(optimized.success), "message": str(optimized.message),
                  "iterations": int(optimized.nit), "elapsed_seconds": time.perf_counter() - run_started,
                  "linear_residual": float(np.max(abs(model.full_constraint @ optimized.x - model.full_target))),
                  "total_overlap_residual": float(model.overlap(optimized.x) - model.pair_target),
                  "single_overlap_residual": float(optimized.x @ single_quadratic @ optimized.x / 24 - 1 / 3),
                  "metrics": {key: value for key, value in model.run(optimized.x, scan=True).items()
                              if key != "polarizations"}, "conditional": optimized.x.tolist(),
                  "integer_repair": repair(model, np.rint(60 * optimized.x).astype(int), single_quadratic)}
        results.append(result)
        print(json.dumps({key: value for key, value in result.items() if key != "conditional"}), flush=True)
        if result["integer_repair"].get("passes_nominal"):
            break
    summary = {"champion_sha256": hashlib.sha256(raw).hexdigest(), "linear_rank": model.rank,
               "elapsed_seconds": time.perf_counter() - started,
               "best_continuous_bias": max(result["metrics"]["bias"] for result in results),
               "found_integer_pass": any(result["integer_repair"].get("passes_nominal", False) for result in results),
               "runs": results}
    print("FINAL_JSON " + json.dumps(summary, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
