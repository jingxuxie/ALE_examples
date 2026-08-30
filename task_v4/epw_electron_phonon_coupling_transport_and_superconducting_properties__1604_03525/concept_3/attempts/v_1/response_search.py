import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution, linprog, minimize

from optimize import COLUMNS, MULTIPLICITY, PAIRS, ROWS, certify, grid_constraints, matrix, objective, save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--seed", type=int, default=411)
    arguments = parser.parse_args()
    selected = np.flatnonzero(ROWS % 2 == COLUMNS % 2)
    design = grid_constraints(64)[:, selected]
    _, unique = np.unique(np.round(design, 10), axis=0, return_index=True)
    design = design[unique]
    constraints = np.vstack((-design, design))
    upper = np.concatenate((np.full(len(design), .915), np.full(len(design), 4.995)))
    best = 1.
    calls = 0
    start = time.monotonic()

    def evaluate(parameters, jacobian=False):
        nonlocal best, calls
        response = np.zeros((18, 2))
        response[0, 0] = 1
        response[1, 1] = parameters[0]
        response[4::4, 0] = parameters[1:5]
        response[5::4, 1] = parameters[5:9]
        derivative = response @ response.T
        cost = derivative[ROWS, COLUMNS] * MULTIPLICITY
        result = linprog(-cost[selected], A_ub=constraints, b_ub=upper, bounds=(-1, 1), method="highs")
        if not result.success:
            result = linprog(-cost[selected], A_ub=constraints, b_ub=upper, bounds=(-1, 1), method="highs-ipm")
        if not result.success:
            return (1e3, np.zeros(9)) if jacobian else 1e3
        coefficients = np.zeros(len(PAIRS))
        coefficients[selected] = result.x
        energy = np.sum(response ** 2) + result.fun
        overlap = 1 + parameters[0]
        value = overlap ** 2 / (2 * energy)
        trace = objective(coefficients)[0]
        calls += 1
        if trace > best:
            certified, report = certify(coefficients)
            if report["trace"] > best:
                best = report["trace"]
                save(coefficients, Path("response_search.json"))
                print("BEST", calls, value, json.dumps(report), flush=True)
        if calls % 200 == 0:
            print("calls", calls, "value", value, "best", best, "seconds", time.monotonic() - start, flush=True)
        if not jacobian:
            return -value
        gradient_energy = 2 * (np.eye(18) - matrix(coefficients)) @ response
        derivative_energy = np.concatenate(([gradient_energy[1, 1]], gradient_energy[4::4, 0], gradient_energy[5::4, 1]))
        gradient = -overlap ** 2 * derivative_energy / (2 * energy ** 2)
        gradient[0] += overlap / energy
        return -value, -gradient

    bounds = [(.3, 3.), (-2., 2.), (-1.5, 1.5), (-1., 1.), (-.75, .75),
              (-3., 3.), (-2., 2.), (-1.5, 1.5), (-1., 1.)]
    result = differential_evolution(evaluate, bounds, seed=arguments.seed,
                                    maxiter=arguments.iterations, popsize=12,
                                    tol=1e-6, polish=False, updating="immediate",
                                    mutation=(.5, 1.3), recombination=.8)
    print("DE", result.fun, result.x.tolist(), flush=True)
    result = minimize(lambda parameters: evaluate(parameters, True), result.x,
                      jac=True, method="L-BFGS-B", bounds=bounds,
                      options={"maxiter": 200, "ftol": 1e-12})
    print("polished", result.fun, result.x.tolist(), flush=True)


if __name__ == "__main__":
    main()
