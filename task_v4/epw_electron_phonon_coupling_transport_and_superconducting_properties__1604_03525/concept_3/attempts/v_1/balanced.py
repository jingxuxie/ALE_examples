import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from optimize import COLUMNS, FREQUENCIES, MULTIPLICITY, PAIRS, ROWS, certify, grid_constraints, matrix, objective, save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--restarts", type=int, default=100)
    parser.add_argument("--output", type=Path, default=Path("balanced.json"))
    arguments = parser.parse_args()
    selected = np.arange(len(PAIRS)) if arguments.full else np.flatnonzero(ROWS % 2 == COLUMNS % 2)
    design = grid_constraints(64)[:, selected]
    if not arguments.full:
        _, unique = np.unique(np.round(design, 10), axis=0, return_index=True)
        design = design[unique]
    constraints = np.vstack((-design, design))
    upper = np.concatenate((np.full(len(design), .915), np.full(len(design), 4.995)))
    generator = np.random.default_rng(83937)
    best = 1.
    start = time.monotonic()
    for restart in range(arguments.restarts):
        coefficients = np.zeros(len(PAIRS))
        coefficients[selected] = generator.normal(size=len(selected)) * .003
        for iteration in range(40):
            full_matrix = matrix(coefficients)
            if restart % 2 == 0:
                response = np.vstack((np.eye(2), np.linalg.solve(np.eye(16) - full_matrix[2:, 2:], full_matrix[2:, :2])))
                value = np.trace(full_matrix[:2, 2:] @ response[2:])
                derivative = response @ response.T
            else:
                response = np.linalg.solve(np.eye(18) - full_matrix, np.eye(18)[:, :2])
                value = np.linalg.slogdet(response[:2])[1]
                derivative = response @ np.linalg.inv(response[:2]) @ response.T
            gradient = derivative[ROWS, COLUMNS] * MULTIPLICITY
            result = linprog(-gradient[selected], A_ub=constraints, b_ub=upper, bounds=(-1, 1), method="highs")
            if not result.success:
                break
            coefficients[selected] = result.x
            trace = objective(coefficients)[0]
            if trace > best:
                certified, report = certify(coefficients)
                if report["trace"] > best:
                    best = report["trace"]
                    save(coefficients, arguments.output)
                    print("BEST", restart, iteration, json.dumps(report), flush=True)
            if iteration > 1 and value - previous_value < 1e-7:
                break
            previous_value = value
        for iteration in range(25):
            value, gradient = objective(coefficients)
            result = linprog(-gradient[selected], A_ub=constraints, b_ub=upper, bounds=(-1, 1), method="highs")
            if not result.success:
                break
            coefficients[selected] = result.x
            trace = objective(coefficients)[0]
            if trace > best:
                certified, report = certify(coefficients)
                if report["trace"] > best:
                    best = report["trace"]
                    save(coefficients, arguments.output)
                    print("BEST", restart, iteration, json.dumps(report), flush=True)
            if trace - value < 1e-7:
                break
        print("restart", restart, "trace", trace, "best", best, "seconds", time.monotonic() - start, flush=True)


if __name__ == "__main__":
    main()
