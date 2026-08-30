import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from optimize import COLUMNS, FREQUENCIES, MULTIPLICITY, PAIRS, ROWS, certify, grid_constraints, matrix, objective, save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--restarts", type=int, default=120)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--rank", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("spectral.json"))
    arguments = parser.parse_args()
    selected = np.arange(len(PAIRS)) if arguments.full else np.flatnonzero(ROWS % 2 == COLUMNS % 2)
    active = np.flatnonzero(FREQUENCIES % 2 == 1) if arguments.full else np.arange(0, 18, 4)
    design = grid_constraints(64)[:, selected]
    if not arguments.full:
        _, unique = np.unique(np.round(design, 10), axis=0, return_index=True)
        design = design[unique]
    constraints = np.vstack((-design, design))
    upper = np.concatenate((np.full(len(design), .915), np.full(len(design), 4.995)))
    generator = np.random.default_rng(3287)
    best = 1.
    start = time.monotonic()
    for restart in range(arguments.restarts):
        bias = [.02, .05, .1, .2, .35, .5, .75, 1., 1.5, 2.][restart % 10]
        response = np.zeros((18, arguments.rank))
        response[active] = generator.normal(size=(len(active), arguments.rank))
        response[active] /= np.sqrt(FREQUENCIES[active, None])
        response /= np.linalg.norm(response)
        derivative = response @ response.T
        gradient = derivative[ROWS, COLUMNS] * MULTIPLICITY
        old_value = 0
        for iteration in range(30):
            result = linprog(-gradient[selected], A_ub=constraints, b_ub=upper, bounds=(-1, 1), method="highs")
            if not result.success:
                break
            coefficients = np.zeros(len(PAIRS))
            coefficients[selected] = result.x
            block = matrix(coefficients)[np.ix_(active, active)]
            block[:(2 if arguments.full else 1), :(2 if arguments.full else 1)] += bias * np.eye(2 if arguments.full else 1)
            eigenvalues, eigenvectors = np.linalg.eigh(block)
            response[:] = 0
            response[active] = eigenvectors[:, -arguments.rank:]
            derivative = response @ response.T
            gradient = derivative[ROWS, COLUMNS] * MULTIPLICITY
            if np.sum(eigenvalues[-arguments.rank:]) - old_value < 1e-8:
                break
            old_value = np.sum(eigenvalues[-arguments.rank:])
        raw_value = objective(coefficients)[0]
        print("spectral", restart, bias, "eigenvalue", eigenvalues[-1], "raw trace", raw_value, flush=True)
        for iteration in range(30):
            old_value, gradient = objective(coefficients)
            result = linprog(-gradient[selected], A_ub=constraints, b_ub=upper, bounds=(-1, 1), method="highs")
            if not result.success:
                break
            coefficients[selected] = result.x
            value = objective(coefficients)[0]
            if value > best:
                certified, report = certify(coefficients)
                if report["trace"] > best:
                    best = report["trace"]
                    save(coefficients, arguments.output)
                    print("BEST", restart, iteration, json.dumps(report), flush=True)
            if value - old_value < 1e-7:
                break
        print("restart", restart, "trace", value, "best", best, "seconds", round(time.monotonic() - start, 1), flush=True)


if __name__ == "__main__":
    main()
