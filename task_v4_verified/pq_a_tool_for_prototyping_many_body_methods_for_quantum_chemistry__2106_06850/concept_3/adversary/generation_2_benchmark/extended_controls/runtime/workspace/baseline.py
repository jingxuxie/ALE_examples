"""Weak deterministic greedy append search with a limited angle-only refinement."""

import argparse
import json
import math
import os
from pathlib import Path
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
from scipy.optimize import minimize

from fermion import (
    allowed_excitations, apply_generator, apply_rotation, load_cases,
    reference_state, rotation_pairs, squared_overlap,
)


def best_append(target, state, pairs):
    sources, destinations, signs = pairs
    active = float(target[sources] @ state[sources] + target[destinations] @ state[destinations])
    tangent = float(
        target[destinations] @ (signs * state[sources])
        - target[sources] @ (signs * state[destinations])
    )
    stationary = math.atan2(tangent, active)
    candidates = (stationary, (stationary + 2.0 * math.pi) % (2.0 * math.pi) - math.pi)
    evaluated = [
        (squared_overlap(target, apply_rotation(state, pairs, theta)), theta)
        for theta in candidates
    ]
    return max(evaluated, key=lambda entry: entry[0])


def optimize_angles(case, labels, angles, max_iterations):
    pairs_list = [rotation_pairs(case.n_orbitals, case.n_electrons, label) for label in labels]
    target_norm = float(case.target @ case.target)

    def objective(parameters):
        history = [reference_state(case)]
        for pairs, theta in zip(pairs_list, parameters):
            history.append(apply_rotation(history[-1], pairs, float(theta)))
        overlap = float(case.target @ history[-1])
        adjoint = case.target.copy()
        gradient = np.empty(len(parameters))
        for position in reversed(range(len(parameters))):
            derivative = apply_generator(history[position + 1], pairs_list[position])
            gradient[position] = -2.0 * overlap * float(adjoint @ derivative) / target_norm
            adjoint = apply_rotation(adjoint, pairs_list[position], -float(parameters[position]))
        return 1.0 - overlap * overlap / target_norm, gradient

    initial_value = objective(np.asarray(angles))[0]
    result = minimize(
        objective, np.asarray(angles), jac=True, method="L-BFGS-B",
        bounds=[(-math.pi, math.pi)] * len(angles),
        options={"maxiter": max_iterations, "ftol": 1e-12, "gtol": 1e-8, "maxls": 20},
    )
    return result.x if math.isfinite(result.fun) and result.fun <= initial_value else np.asarray(angles)


def solve_case(case, refine_iterations):
    candidates = allowed_excitations(case.n_orbitals)
    candidate_pairs = [rotation_pairs(case.n_orbitals, case.n_electrons, gate) for gate in candidates]
    state = reference_state(case)
    labels, angles = [], []
    for position in range(case.max_gates):
        choices = [best_append(case.target, state, pairs) for pairs in candidate_pairs]
        winner = max(range(len(choices)), key=lambda index: choices[index][0])
        theta = choices[winner][1]
        labels.append(candidates[winner])
        angles.append(theta)
        state = apply_rotation(state, candidate_pairs[winner], theta)
    angles = optimize_angles(case, labels, angles, refine_iterations)
    gates = [{
        "annihilate": list(label.annihilate), "create": list(label.create), "theta": float(theta),
    } for label, theta in zip(labels, angles)]
    return {"case_id": case.case_id, "gates": gates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--refine-iterations", type=int, default=60)
    arguments = parser.parse_args()
    if not 1 <= arguments.refine_iterations <= 200:
        parser.error("refine-iterations must be between 1 and 200")
    started = time.perf_counter()
    result = {"schema_version": 1, "circuits": [
        solve_case(case, arguments.refine_iterations) for case in load_cases()
    ]}
    destination = Path(arguments.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(destination), "runtime_seconds": time.perf_counter() - started}))


if __name__ == "__main__":
    main()
