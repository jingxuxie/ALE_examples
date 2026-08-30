import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize


def baseline_module():
    filename = Path(__file__).resolve().parents[2] / "participant/baseline/solver.py"
    specification = importlib.util.spec_from_file_location("starting_point", filename)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def cayley(parameters, dimension):
    upper = np.triu_indices(dimension, 1)
    skew = np.zeros((dimension, dimension))
    skew[upper] = parameters
    skew -= skew.T
    inverse = np.linalg.inv(np.eye(dimension) - skew)
    rotation = inverse @ (np.eye(dimension) + skew)
    return rotation, inverse, upper


def optimize(case, starting, seconds):
    one_body = np.asarray(case["one_body"])
    factors = np.asarray(case["factors"])
    dimension, rank = len(one_body), len(factors)
    orbital_size = dimension * (dimension - 1) // 2
    auxiliary_size = rank * (rank - 1) // 2
    orbital_center = np.asarray(starting["orbital"])
    auxiliary_center = np.asarray(starting["auxiliary"])
    best = dict(starting)
    reference = baseline_module()
    best_cost = reference.cost(one_body, factors, orbital_center, auxiliary_center)
    scale = best_cost
    deadline = time.monotonic() + seconds
    evaluations = 0

    for epsilon in (0.05, 0.02, 0.007, 0.002, 0.0005, 0.0001):
        def function(parameters):
            nonlocal best, best_cost, evaluations
            if time.monotonic() >= deadline:
                raise TimeoutError
            orbital_rotation, orbital_inverse, orbital_upper = cayley(parameters[:orbital_size], dimension)
            auxiliary_rotation, auxiliary_inverse, auxiliary_upper = cayley(parameters[orbital_size:], rank)
            orbital = orbital_center @ orbital_rotation
            auxiliary = auxiliary_rotation @ auxiliary_center
            rotated = np.einsum("pi,apq,qj->aij", orbital, factors, orbital, optimize=True)
            mixed = np.einsum("ab,bij->aij", auxiliary, rotated, optimize=True)
            new_one = orbital.T @ one_body @ orbital
            smooth_factors = np.sqrt(mixed * mixed + epsilon * epsilon)
            weights = smooth_factors.sum(axis=(1, 2))
            smooth_one = np.sqrt(new_one * new_one + epsilon * epsilon)
            value = (smooth_one.sum() + 0.5 * weights @ weights) / scale
            actual_weights = np.abs(mixed).sum(axis=(1, 2))
            actual = float(np.abs(new_one).sum() + 0.5 * actual_weights @ actual_weights)
            if actual < best_cost:
                best_cost = actual
                best = {"id": case["id"], "orbital": orbital.tolist(), "auxiliary": auxiliary.tolist()}
            gradient_mixed = weights[:, None, None] * mixed / smooth_factors
            gradient_auxiliary = np.einsum("aij,bij->ab", gradient_mixed, rotated)
            gradient_rotated = np.einsum("ab,aij->bij", auxiliary, gradient_mixed)
            gradient_orbital = 2 * one_body @ orbital @ (new_one / smooth_one)
            gradient_orbital += 2 * np.einsum("apq,qj,aji->pi", factors, orbital, gradient_rotated, optimize=True)
            gradient_orbital_rotation = orbital_center.T @ gradient_orbital
            gradient_auxiliary_rotation = gradient_auxiliary @ auxiliary_center.T
            gradient_orbital_skew = orbital_inverse.T @ gradient_orbital_rotation @ (np.eye(dimension) + orbital_rotation).T
            gradient_auxiliary_skew = auxiliary_inverse.T @ gradient_auxiliary_rotation @ (np.eye(rank) + auxiliary_rotation).T
            gradient = np.concatenate(((gradient_orbital_skew - gradient_orbital_skew.T)[orbital_upper], (gradient_auxiliary_skew - gradient_auxiliary_skew.T)[auxiliary_upper])) / scale
            evaluations += 1
            return value, gradient
        try:
            result = minimize(function, np.zeros(orbital_size + auxiliary_size), method="L-BFGS-B", jac=True, options={"maxiter": 220, "ftol": 1e-10, "gtol": 1e-7, "maxls": 25})
            orbital_rotation = cayley(result.x[:orbital_size], dimension)[0]
            auxiliary_rotation = cayley(result.x[orbital_size:], rank)[0]
            orbital_center = orbital_center @ orbital_rotation
            auxiliary_center = auxiliary_rotation @ auxiliary_center
        except TimeoutError:
            break
    return best, {"id": case["id"], "cost": best_cost, "reduction": 1 - best_cost / case["baseline_cost"], "evaluations": evaluations}


def main():
    request = json.loads(Path(sys.argv[1]).read_text())
    reference = baseline_module()
    solutions, records = [], []
    for case in request["cases"]:
        starting = reference.solve(case)
        solution, record = optimize(case, starting, request.get("seconds_per_case", 10) * 0.8)
        solutions.append(solution)
        records.append(record)
        print(json.dumps(record), file=sys.stderr, flush=True)
    Path(sys.argv[2]).write_text(json.dumps({"solutions": solutions}, allow_nan=False))


if __name__ == "__main__":
    main()
