import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import basinhopping, linprog

from optimize import COLUMNS, FREQUENCIES, MULTIPLICITY, PAIRS, ROWS, certify, grid_constraints, matrix, objective, save


def main():
    design = grid_constraints(64)
    constraints = np.vstack((-design, design))
    upper = np.concatenate((np.full(len(design), .915), np.full(len(design), 4.995)))
    active = np.flatnonzero((FREQUENCIES % 2 == 1) & (FREQUENCIES > 1))
    base = np.array(json.loads(Path("refined.json").read_text())["kernel_b"])
    response = np.linalg.solve(np.eye(18) - base, np.eye(18)[:, :2])
    response /= response[0, 0]
    initial = np.concatenate(([response[1, 1], response[0, 1]], response[active].ravel()))
    best = 1.696
    calls = 0
    start = time.monotonic()

    def evaluate(parameters):
        nonlocal best, calls
        response = np.zeros((18, 2))
        response[0, 0] = 1
        response[1, 1] = parameters[0]
        response[0, 1] = response[1, 0] = parameters[1]
        response[active] = parameters[2:].reshape(8, 2)
        derivative = response @ response.T
        cost = derivative[ROWS, COLUMNS] * MULTIPLICITY
        result = linprog(-cost, A_ub=constraints, b_ub=upper, bounds=(-1, 1), method="highs")
        if not result.success:
            result = linprog(-cost, A_ub=constraints, b_ub=upper, bounds=(-1, 1), method="highs-ipm")
        if not result.success:
            return 1000., np.zeros(18)
        coefficients = result.x
        energy = np.sum(response ** 2) + result.fun
        overlap = 1 + parameters[0]
        value = overlap ** 2 / (2 * energy)
        trace = objective(coefficients)[0]
        calls += 1
        if trace > best:
            certified, report = certify(coefficients)
            if report["trace"] > best:
                best = report["trace"]
                save(coefficients, Path("full_response.json"))
                print("BEST", calls, value, json.dumps(report), flush=True)
        if calls % 50 == 0:
            print("calls", calls, "value", value, "best", best, "seconds", time.monotonic() - start, flush=True)
        gradient_energy = 2 * (np.eye(18) - matrix(coefficients)) @ response
        derivative_energy = np.concatenate(([gradient_energy[1, 1], gradient_energy[0, 1] + gradient_energy[1, 0]], gradient_energy[active].ravel()))
        gradient = -overlap ** 2 * derivative_energy / (2 * energy ** 2)
        gradient[0] += overlap / energy
        return -value, -gradient

    def callback(parameters, value, accepted):
        print("basin", value, accepted, "calls", calls, flush=True)

    result = basinhopping(evaluate, initial, niter=35, T=.03, stepsize=.25,
                          seed=9912, interval=5, callback=callback,
                          minimizer_kwargs={"jac": True, "method": "L-BFGS-B",
                                            "bounds": [(.3, 3.), (-1.5, 1.5)] + [(-3., 3.)] * 16,
                                            "options": {"maxiter": 25, "maxfun": 60, "ftol": 1e-9}})
    print("final", result.fun, result.x.tolist(), flush=True)


if __name__ == "__main__":
    main()
