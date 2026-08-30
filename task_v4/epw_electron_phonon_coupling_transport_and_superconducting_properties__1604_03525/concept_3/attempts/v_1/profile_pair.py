import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from optimize import COLUMNS, MULTIPLICITY, ROWS, basis, certify, grid_constraints, matrix, objective, save


def main():
    base = np.array(json.loads(Path("oriented_refined.json").read_text())["kernel_b"])
    responses = np.linalg.solve(np.eye(18) - base, np.eye(18)[:, :2])
    eigenvalues, eigenvectors = np.linalg.eigh(responses[:2])
    profile = responses @ eigenvectors[:, -1]
    profile /= np.linalg.norm(profile[:2])
    angles = 2 * np.pi * np.arange(1024) / 1024
    features = basis(angles)
    design = grid_constraints(64)
    constraints = np.vstack((-design, design))
    upper = np.concatenate((np.full(len(design), .915), np.full(len(design), 4.995)))
    best = 1.69735
    start = time.monotonic()
    for shift in np.linspace(.08, np.pi / 2, 12):
        shifted = features.T @ (basis(angles + shift) @ profile) / len(angles)
        response = np.column_stack((profile, shifted))
        response = response @ np.linalg.inv(response[:2])
        for weight in (.7, 1.4):
            derivative = response @ np.diag([weight, 1.]) @ response.T
            gradient = derivative[ROWS, COLUMNS] * MULTIPLICITY
            previous = 0.
            for iteration in range(35):
                result = linprog(-gradient, A_ub=constraints, b_ub=upper, bounds=(-1, 1), method="highs-ipm")
                if not result.success:
                    break
                coefficients = result.x
                value, gradient = objective(coefficients)
                if value > best:
                    certified, report = certify(coefficients)
                    if report["trace"] > best:
                        best = report["trace"]
                        save(coefficients, Path("profile_pair.json"))
                        print("BEST", shift, weight, iteration, json.dumps(report), flush=True)
                if value - previous < 1e-7:
                    break
                previous = value
            print("pair", shift, weight, value, "best", best, "seconds", time.monotonic() - start, flush=True)


if __name__ == "__main__":
    main()
