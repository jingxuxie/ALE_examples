import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from optimize import COLUMNS, FREQUENCIES, PAIRS, ROWS, certify, grid_constraints, objective, save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--restarts", type=int, default=30)
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--seed", type=int, default=6173)
    parser.add_argument("--reduced", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("continuation.json"))
    arguments = parser.parse_args()
    selected = np.flatnonzero(ROWS % 2 == COLUMNS % 2) if arguments.reduced else np.arange(len(PAIRS))
    design = grid_constraints(64)[:, selected]
    if arguments.reduced:
        _, unique = np.unique(np.round(design, 10), axis=0, return_index=True)
        design = design[unique]
    constraints = np.vstack((-design, design))
    generator = np.random.default_rng(arguments.seed)
    best = 1.
    start = time.monotonic()
    stages = [(.002, 12), (.002, 9), (.002, 6), (.03, 6), (.055, 6), (.08, 6)]
    for restart in range(arguments.restarts):
        coefficients = np.zeros(len(PAIRS))
        coefficients[selected] = generator.normal(size=len(selected)) * .003
        for lower, upper_bound in stages:
            upper = np.concatenate((np.full(len(design), 1 - lower - .003),
                                    np.full(len(design), upper_bound - 1 - .003)))
            for iteration in range(arguments.iterations):
                old_value, gradient = objective(coefficients)
                result = linprog(-gradient[selected], A_ub=constraints, b_ub=upper,
                                 bounds=(-1, 1), method="highs")
                if not result.success:
                    break
                coefficients[selected] = result.x
                value = objective(coefficients)[0]
                if iteration > 0 and value - old_value < 1e-7:
                    break
            certified, report = certify(coefficients)
            if report["trace"] > best:
                best = report["trace"]
                save(coefficients, arguments.output)
                print("BEST", restart, lower, upper_bound, json.dumps(report), flush=True)
            print("stage", restart, lower, upper_bound, value, "best", best,
                  "seconds", round(time.monotonic() - start, 1), flush=True)


if __name__ == "__main__":
    main()
