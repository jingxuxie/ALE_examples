import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import maximum_filter, minimum_filter
from scipy.optimize import linprog

from optimize import COLUMNS, ERROR_WEIGHTS, MULTIPLICITY, PAIRS, ROWS, basis, certify, grid_constraints, matrix, objective, save


def point_design(first, second, features):
    design = features[first[:, None], ROWS] * features[second[:, None], COLUMNS]
    off_diagonal = ROWS != COLUMNS
    design[:, off_diagonal] += (features[first[:, None], COLUMNS] * features[second[:, None], ROWS])[:, off_diagonal]
    return design


def canonical_points(first, second, count):
    low = np.minimum(first, second)
    high = np.maximum(first, second)
    shifted = low >= count // 2
    low[shifted] -= count // 2
    high[shifted] -= count // 2
    swapped = (high >= count // 2) & (low > high - count // 2)
    saved = low[swapped].copy()
    low[swapped] = high[swapped] - count // 2
    high[swapped] = saved + count // 2
    return set(zip(low.tolist(), high.tolist()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("initial", type=Path)
    parser.add_argument("--output", type=Path, default=Path("refined.json"))
    parser.add_argument("--iterations", type=int, default=60)
    parser.add_argument("--perturb", type=float, default=0)
    parser.add_argument("--seed", type=int, default=44)
    parser.add_argument("--safety", type=float, default=2e-6)
    arguments = parser.parse_args()
    coefficients = np.array(json.loads(arguments.initial.read_text())["kernel_b"])[ROWS, COLUMNS]
    coefficients += np.random.default_rng(arguments.seed).normal(size=len(PAIRS)) * arguments.perturb
    design = grid_constraints(64)
    count = len(PAIRS)
    features = basis(2 * np.pi * np.arange(1024) / 1024)
    signs = np.block([[np.eye(count), -np.eye(count)], [-np.eye(count), -np.eye(count)]])
    known = set()
    best = 1.0
    start = time.monotonic()
    for iteration in range(arguments.iterations):
        old_value, gradient = objective(coefficients)
        for cut in range(40):
            errors = np.broadcast_to(ERROR_WEIGHTS, design.shape)
            constraints = np.vstack((np.hstack((-design, errors)), np.hstack((design, errors)), signs))
            upper = np.concatenate((np.full(len(design), .92 - arguments.safety), np.full(len(design), 5 - arguments.safety), np.zeros(2 * count)))
            result = linprog(np.concatenate((-gradient, np.zeros(count))),
                             A_ub=constraints, b_ub=upper,
                             bounds=[(-1, 1)] * count + [(0, 1)] * count,
                             method="highs", options={"dual_feasibility_tolerance": 1e-8,
                                                      "primal_feasibility_tolerance": 1e-8})
            if not result.success:
                result = linprog(np.concatenate((-gradient, np.zeros(count))),
                                 A_ub=constraints, b_ub=upper,
                                 bounds=[(-1, 1)] * count + [(0, 1)] * count,
                                 method="highs-ipm")
            if not result.success:
                print("LP failure", result.message, flush=True)
                return
            candidate = result.x[:count]
            kernel = 1 + features @ matrix(candidate) @ features.T
            error = ERROR_WEIGHTS @ np.abs(candidate)
            lower, upper_bound = kernel.min() - error, kernel.max() + error
            if lower >= .08 + arguments.safety / 2 and upper_bound <= 6 - arguments.safety / 2:
                break
            minima = (kernel == minimum_filter(kernel, size=3, mode="wrap")) & (kernel - error < .08 + arguments.safety / 2)
            maxima = (kernel == maximum_filter(kernel, size=3, mode="wrap")) & (kernel + error > 6 - arguments.safety / 2)
            first, second = np.where(minima | maxima)
            points = canonical_points(first, second, 1024) - known
            if not points:
                break
            known.update(points)
            first, second = np.array(sorted(points)).T
            design = np.vstack((design, point_design(first, second, features)))
            print("cut", iteration, cut, len(points), len(design), float(lower), float(upper_bound), flush=True)
        coefficients = candidate
        value = objective(coefficients)[0]
        certified, report = certify(coefficients)
        if report["trace"] > best:
            best = report["trace"]
            save(coefficients, arguments.output)
        print("iterate", iteration, value, "best", best, "time", time.monotonic() - start, flush=True)
        if value - old_value < 1e-8:
            break


if __name__ == "__main__":
    main()
