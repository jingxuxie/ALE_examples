import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from optimize import COLUMNS, MULTIPLICITY, PAIRS, ROWS, basis, certify, grid_constraints, matrix, objective, save


def main():
    generator = np.random.default_rng(24575)
    base = np.array(json.loads(Path("refined.json").read_text())["kernel_b"])[ROWS, COLUMNS]
    design = grid_constraints(64)
    constraints = np.vstack((-design, design))
    upper = np.concatenate((np.full(len(design), .915), np.full(len(design), 4.995)))
    angles = 2 * np.pi * np.arange(1024) / 1024
    features = basis(angles)
    best = objective(base)[0]
    pool = [base]
    start = time.monotonic()
    for restart in range(90):
        parent = pool[generator.integers(len(pool))]
        response = np.linalg.solve(np.eye(18) - matrix(parent), np.eye(18)[:, :2])
        if restart % 3 == 0:
            strength = generator.uniform(.05, .65)
            warp = angles + strength * (generator.normal() * np.sin(2 * angles)
                                        + generator.normal() * np.cos(2 * angles)
                                        + .5 * generator.normal() * np.sin(4 * angles)
                                        + .5 * generator.normal() * np.cos(4 * angles))
            response = features.T @ (basis(warp) @ response) / len(angles)
        elif restart % 3 == 1:
            shift = generator.uniform(-1.5, 1.5)
            response[:, 0] = features.T @ (basis(angles + shift) @ response[:, 0]) / len(angles)
            response[:, 1] *= np.exp(generator.uniform(-1, 1))
        else:
            noise = generator.normal(size=response.shape) * generator.uniform(.05, .7)
            noise[2::4] = 0
            noise[3::4] = 0
            response += noise
        derivative = response @ response.T
        gradient = derivative[ROWS, COLUMNS] * MULTIPLICITY
        old_value = 0.
        for iteration in range(30):
            result = linprog(-gradient, A_ub=constraints, b_ub=upper, bounds=(-1, 1), method="highs")
            if not result.success:
                break
            coefficients = result.x
            value, gradient = objective(coefficients)
            if value > best:
                certified, report = certify(coefficients)
                if report["trace"] > best:
                    best = report["trace"]
                    save(coefficients, Path("hop.json"))
                    print("BEST", restart, iteration, json.dumps(report), flush=True)
            if value - old_value < 1e-7:
                break
            old_value = value
        if value > 1.62:
            pool.append(coefficients)
            if len(pool) > 30:
                pool.pop(1)
        print("restart", restart, "trace", value, "best", best, "seconds", time.monotonic() - start, flush=True)


if __name__ == "__main__":
    main()
