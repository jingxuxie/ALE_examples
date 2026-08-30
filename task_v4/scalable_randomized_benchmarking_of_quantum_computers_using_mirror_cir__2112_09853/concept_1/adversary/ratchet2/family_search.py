import argparse
import json
import time

import numpy as np
from scipy.linalg import null_space, qr
from scipy.optimize import Bounds, LinearConstraint, NonlinearConstraint, minimize

from model import GeneralModel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--starts", type=int, default=12)
    parser.add_argument("--stratify-pairs", action="store_true")
    arguments = parser.parse_args()
    started = time.perf_counter()
    model = GeneralModel()
    family_means = np.zeros((256, 192))
    single_mask = model.error_gate < 24
    family_means[model.error_label[single_mask], np.flatnonzero(single_mask)] = 1
    full_linear = np.vstack((model.full_constraint, family_means[1:]))
    full_target = full_linear @ model.uniform
    _, triangular, pivots = qr(full_linear.T, pivoting=True, mode="economic")
    rank = int(np.sum(abs(np.diag(triangular)) > 1e-10))
    linear = full_linear[pivots[:rank]]
    target = full_target[pivots[:rank]]
    directions = null_space(linear)
    single_quadratic = model.quadratic.copy()
    single_quadratic[72:, :] = 0
    single_quadratic[:, 72:] = 0
    constraints = [LinearConstraint(linear, target, target),
                   NonlinearConstraint(model.overlap, model.pair_target, model.pair_target,
                                       jac=model.overlap_gradient)]
    if arguments.stratify_pairs:
        constraints.append(NonlinearConstraint(lambda point: point @ single_quadratic @ point / 24,
                                               1 / 3, 1 / 3,
                                               jac=lambda point: 2 * single_quadratic @ point / 24))
    generator = np.random.default_rng(20260828)
    results = []
    for start_index in range(arguments.starts):
        if start_index == 0 and not arguments.stratify_pairs:
            initial = model.initial_counts() / 60
        else:
            direction = directions @ generator.normal(size=directions.shape[1])
            allowed = np.minimum((model.upper / 60 - model.uniform) / np.maximum(direction, 1e-100),
                                 (model.uniform - model.lower / 60) / np.maximum(-direction, 1e-100))
            initial = model.uniform + 0.8 * float(np.min(allowed)) * direction
        run_started = time.perf_counter()
        optimized = minimize(lambda point: model.run(point, gradient=True, residual_limit=0.004),
                             initial, method="SLSQP", jac=True,
                             bounds=Bounds(model.lower / 60, model.upper / 60), constraints=constraints,
                             options={"maxiter": 500, "ftol": 1e-11, "disp": False})
        result = {"start": start_index, "success": bool(optimized.success), "message": str(optimized.message),
                  "iterations": int(optimized.nit), "elapsed_seconds": time.perf_counter() - run_started,
                  "linear_residual": float(np.max(abs(full_linear @ optimized.x - full_target))),
                  "overlap_residual": float(model.overlap(optimized.x) - model.pair_target),
                  "single_overlap_residual": float(optimized.x @ single_quadratic @ optimized.x / 24 - 1 / 3),
                  "metrics": {key: value for key, value in model.run(optimized.x, scan=True).items()
                              if key != "polarizations"}, "conditional": optimized.x.tolist()}
        results.append(result)
        print(json.dumps({key: value for key, value in result.items() if key != "conditional"}), flush=True)
    summary = {"stratify_pairs": arguments.stratify_pairs, "linear_rank": rank,
               "starts": arguments.starts, "elapsed_seconds": time.perf_counter() - started,
               "best_bias": max(result["metrics"]["bias"] for result in results if result["success"]),
               "runs": results}
    print("FINAL_JSON " + json.dumps(summary, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
