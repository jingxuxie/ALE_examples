import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from optimize import COLUMNS, FREQUENCIES, PAIRS, ROWS, certify, grid_constraints, objective, save


def main():
    coefficients = np.array(json.loads(Path("refined.json").read_text())["kernel_b"])[ROWS, COLUMNS]
    design = grid_constraints(64)
    constraints = np.vstack((-design, design))
    upper = np.concatenate((np.full(len(design), .915), np.full(len(design), 4.995)))
    generator = np.random.default_rng(3945)
    start = time.monotonic()
    best = objective(coefficients)[0]
    for iteration in range(15):
        value, gradient = objective(coefficients)
        result = linprog(-gradient, A_ub=constraints, b_ub=upper, bounds=(-1, 1), method="highs")
        if result.success:
            coefficients = result.x
    base = coefficients.copy()
    base_value, gradient = objective(base)
    support = gradient @ base
    face_constraints = np.vstack((constraints, -gradient))
    for trial in range(240):
        loss = [1e-6, 1e-5, 1e-4, .001, .005, .02, .05, .1][trial % 8]
        objective_noise = generator.normal(size=len(PAIRS))
        if trial % 2 == 0:
            objective_noise *= (FREQUENCIES[ROWS] % 2 == 1)
        result = linprog(-objective_noise, A_ub=face_constraints,
                         b_ub=np.append(upper, -support + loss), bounds=(-1, 1), method="highs")
        if not result.success:
            continue
        coefficients = result.x
        value = objective(coefficients)[0]
        print("face", trial, loss, "raw", value, "distance", np.linalg.norm(coefficients - base), flush=True)
        if value > base_value - .01 or trial % 8 == 7:
            for iteration in range(25):
                old_value, current_gradient = objective(coefficients)
                result = linprog(-current_gradient, A_ub=constraints, b_ub=upper, bounds=(-1, 1), method="highs")
                if not result.success:
                    break
                coefficients = result.x
                value = objective(coefficients)[0]
                if value - old_value < 1e-7:
                    break
            certified, report = certify(coefficients)
            if report["trace"] > best:
                best = report["trace"]
                save(coefficients, Path("face_search.json"))
                print("BEST", trial, json.dumps(report), flush=True)
            print("ascent", trial, value, "best", best, "seconds", time.monotonic() - start, flush=True)


if __name__ == "__main__":
    main()
