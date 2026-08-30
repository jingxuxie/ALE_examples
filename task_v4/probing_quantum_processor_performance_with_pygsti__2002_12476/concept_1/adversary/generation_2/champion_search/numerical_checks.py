import itertools
import json
import os
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.dont_write_bytecode = True

import numpy as np

from metrics import Benchmark, HERE, profile, write_json
from optimize import Search


def independent(features, counts):
    support = np.flatnonzero(counts)
    rows = features[:, support] * np.sqrt(64 * counts[support])[None, :, None]
    worst = np.zeros(len(rows))
    right = np.broadcast_to(np.eye(14)[:, :12], (len(rows), 14, 12))
    for deleted in itertools.combinations(range(len(support)), 3):
        keep = np.ones(len(support), dtype=bool)
        keep[list(deleted)] = False
        information = rows[:, keep].transpose(0, 2, 1) @ rows[:, keep] + np.eye(14) * 1e-10
        solution = np.linalg.solve(information, right)
        risk = np.trace(solution[:, :12], axis1=1, axis2=2)
        worst = np.maximum(worst, risk)
    return worst


def main():
    started = time.monotonic()
    benchmark = Benchmark()
    counts = np.array(json.loads((HERE / "phase_3_design.json").read_text())["batches"])
    results = {}
    for label, design in [("champion", benchmark.reference_counts), ("pilot", counts)]:
        direct = profile(benchmark.features, design, orders=(3,), direct=True)
        fast = profile(benchmark.features, design, orders=(3,), direct=False)
        independently_solved = independent(benchmark.features, design)
        results[label] = dict(rank_update_relative_error=float(np.max(np.abs(fast["loss_3"] / direct["loss_3"] - 1))),
                              independent_solve_relative_error=float(np.max(np.abs(independently_solved / direct["loss_3"] - 1))))
    optimizer = Search.__new__(Search)
    optimizer.data = benchmark
    optimizer.costs = benchmark.costs
    optimizer.available = 1312000
    optimizer.rows = benchmark.features * np.sqrt(64 * optimizer.available / optimizer.costs)[None, :, None]
    optimizer.upper = 48 * optimizer.costs / optimizer.available
    optimizer.family_masks = [benchmark.families == family for family in np.unique(benchmark.families)]
    optimizer.normalizers = np.array([benchmark.reference["intact"][mask].mean() for mask in optimizer.family_masks])
    support = np.flatnonzero(counts)
    allocation = counts[support] * optimizer.costs[support] / optimizer.available
    state = optimizer.state(allocation, support)
    errors = []
    step = 1e-7
    for position in range(len(support)):
        perturbation = np.zeros(len(support))
        perturbation[position] = step
        plus = optimizer.state(allocation + perturbation, support)
        minus = optimizer.state(allocation - perturbation, support)
        difference = (plus[2] - minus[2]) / (2 * step)
        errors.append(float(np.max(np.abs(difference - state[3][:, position]) / np.maximum(1, np.abs(difference)))))
    results["log_guard_gradient_max_normalized_error"] = max(errors)
    results["passed"] = max(entry["independent_solve_relative_error"] for entry in [results["champion"], results["pilot"]]) < 1e-7 and max(errors) < 1e-5
    results["no_main_held_out_models_used"] = True
    results["seconds"] = time.monotonic() - started
    write_json(HERE / "numerical_checks.json", results)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
