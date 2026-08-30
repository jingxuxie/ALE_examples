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
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--seed", type=int, default=957)
    parser.add_argument("--output", type=Path, default=Path("reduced.json"))
    parser.add_argument("--directional", action="store_true")
    arguments = parser.parse_args()
    selected = np.flatnonzero((ROWS % 2) == (COLUMNS % 2))
    design = grid_constraints(64)[:, selected]
    _, unique = np.unique(np.round(design, 10), axis=0, return_index=True)
    design = design[unique]
    constraints = np.vstack((-design, design))
    upper = np.concatenate((np.full(len(design), .915), np.full(len(design), 4.995)))
    generator = np.random.default_rng(arguments.seed)
    best = 1.
    start = time.monotonic()
    print("setup", design.shape, flush=True)
    for restart in range(arguments.restarts):
        response = np.zeros((18, 2))
        if restart % 3 == 0:
            response[0, 0] = 1
            response[1, 1] = 1
            response[4::4, 0] = generator.normal(size=4) * generator.uniform(.3, 2.)
            response[5::4, 1] = generator.normal(size=4) * generator.uniform(.3, 2.)
        elif restart % 3 == 1:
            response[0::4, 0] = generator.normal(size=5) / np.arange(1, 6) ** .5
            response[1::4, 1] = generator.normal(size=5) / np.arange(1, 6) ** .5
        else:
            response[0, 0] = generator.uniform(.2, 1.)
            response[1, 1] = generator.uniform(.2, 1.)
            response[generator.choice([4, 8, 12, 16]), 0] = 1
            response[generator.choice([5, 9, 13, 17]), 1] = generator.choice([-1, 1])
        response[:, 1] *= np.exp(generator.uniform(-2, 2))
        if arguments.directional:
            response[:, 1] = 0
        derivative = response @ response.T
        gradient = (derivative[ROWS, COLUMNS] * MULTIPLICITY)[selected]
        old_value = 0.
        for iteration in range(arguments.iterations):
            result = linprog(-gradient, A_ub=constraints, b_ub=upper,
                             bounds=(-1, 1), method="highs")
            if not result.success:
                print("failure", restart, iteration, result.message, flush=True)
                break
            coefficients = np.zeros(len(PAIRS))
            coefficients[selected] = result.x
            value, full_gradient = objective(coefficients)
            if value > best:
                certified, report = certify(coefficients)
                if report["trace"] > best:
                    best = report["trace"]
                    save(coefficients, arguments.output)
                    print("BEST", restart, iteration, json.dumps(report), flush=True)
            if arguments.directional:
                response = np.linalg.solve(np.eye(18) - matrix(coefficients), np.eye(18)[:, 0])
                value = response[0] / 2
                derivative = np.outer(response, response) / 2
                full_gradient = derivative[ROWS, COLUMNS] * MULTIPLICITY
            gradient = full_gradient[selected]
            if value - old_value < 1e-7:
                break
            old_value = value
        print("restart", restart, "objective", value, "best", best,
              "seconds", round(time.monotonic() - start, 2), flush=True)


if __name__ == "__main__":
    main()
