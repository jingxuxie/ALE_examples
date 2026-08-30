import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from optimize import PAIRS, certify, grid_constraints, objective, save


def main():
    coarse = grid_constraints(24)
    middle = grid_constraints(48)
    fine = grid_constraints(64)
    generator = np.random.default_rng(8594)
    best = 1.
    start = time.monotonic()
    stages = [(coarse, .915, 4.995),
              (np.vstack((coarse, middle)), None, None),
              (np.vstack((coarse, middle)), .915, 4.995),
              (np.vstack((coarse, middle, fine)), .915, 4.995)]
    for restart in range(30):
        coefficients = generator.normal(size=len(PAIRS)) * .003
        for stage, (design, lower, upper_bound) in enumerate(stages):
            constraints = np.vstack((-design, design))
            if lower is None:
                upper = np.concatenate((np.full(len(coarse), .915), np.full(len(middle), 1.2),
                                        np.full(len(coarse), 4.995), np.full(len(middle), 7.)))
            else:
                upper = np.concatenate((np.full(len(design), lower), np.full(len(design), upper_bound)))
            for iteration in range(30):
                old_value, gradient = objective(coefficients)
                result = linprog(-gradient, A_ub=constraints, b_ub=upper, bounds=(-1, 1), method="highs-ipm")
                if not result.success:
                    break
                coefficients = result.x
                value = objective(coefficients)[0]
                if iteration > 0 and value - old_value < 1e-7:
                    break
            certified, report = certify(coefficients)
            if report["trace"] > best:
                best = report["trace"]
                save(coefficients, Path("grid_continuation.json"))
                print("BEST", restart, stage, json.dumps(report), flush=True)
            print("stage", restart, stage, value, "best", best,
                  "seconds", time.monotonic() - start, flush=True)


if __name__ == "__main__":
    main()
