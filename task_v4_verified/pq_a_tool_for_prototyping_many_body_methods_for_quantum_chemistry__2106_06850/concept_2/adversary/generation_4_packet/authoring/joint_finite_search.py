"""Private simultaneous stationary-root search at base and adaptive neighbors."""

import argparse
import json
import time
from pathlib import Path

from reduced_search import ReducedModel, artifact, robust_screen

import jax
import jax.numpy as jnp
import numpy as np
from scipy.optimize import minimize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minutes", type=float, default=10)
    parser.add_argument("--iterations", type=int, default=2500)
    arguments = parser.parse_args()
    arguments.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    model = ReducedModel(arguments.source, 0.00099, 1e-4, 0.0201)
    base = model.evaluate(model.initial)[3]
    response = np.array(model.response_function(base))
    direction = response / np.linalg.norm(response)
    extras = []
    for sign in (1, -1):
        point = model.initial + sign * 0.001 * direction
        extras.extend(model.evaluate(point)[3][120:])
    initial = np.r_[base, extras]

    def calculate(values):
        response = model.response_function(values[:156])
        norm = jnp.linalg.norm(response)
        direction = response / jnp.maximum(norm, 1e-12)
        outputs, information = [], []
        for index, sign in enumerate((0, 1, -1)):
            parameters = values[120:156] if index == 0 else values[156 + (index - 1) * 36:156 + index * 36]
            point = jnp.r_[values[:120] + sign * 0.001 * direction, parameters]
            output, info = model.function(point)
            outputs.append(output)
            information.append(info)
        information = jnp.stack(information)
        objective = jnp.sum(information[:, 1] ** 2) / 1e-4 + 1e-10 * jnp.sum(values[:120] ** 2)
        equalities = jnp.concatenate([output[1:37] for output in outputs])
        inequalities = jnp.concatenate([output[39:] for output in outputs])
        return jnp.r_[objective, equalities, inequalities], information

    function = jax.jit(calculate)
    derivative = jax.jit(jax.jacfwd(lambda values: calculate(values)[0]))
    cache = {}
    iterations = 0
    best = float("inf")

    def evaluate(values):
        key = values.tobytes()
        if key not in cache:
            output, information = function(values)
            cache.clear()
            cache[key] = np.array(output), np.array(derivative(values)), np.array(information)
        return cache[key]

    def callback(values):
        nonlocal iterations, best
        output, _, info = evaluate(values)
        iterations += 1
        error = float(max(abs(output[1:109])))
        margin = float(min(output[109:]))
        maximum_energy = float(max(abs(info[:, 1])))
        record = {"iteration": iterations, "equation_error": error, "minimum_nonenergy_margin": margin,
                  "max_energy_error": maximum_energy, "min_population": float(min(info[:, 9])),
                  "max_dad": float(max(info[:, 8])), "base_gradient_norm": float(info[0, 0]),
                  "elapsed_seconds": time.monotonic() - started}
        if iterations % 20 == 0:
            print(json.dumps(record), flush=True)
        if iterations % 100 == 0:
            matrix = np.einsum("k,kij->ij", values[:120], model.axes)
            (arguments.output / "last_iterate.json").write_text(json.dumps(artifact(matrix, values[120:138]), indent=2))
        if error < 2e-9 and margin >= -1e-8 and maximum_energy < best:
            best = maximum_energy
            matrix = np.einsum("k,kij->ij", values[:120], model.axes)
            (arguments.output / "candidate.json").write_text(json.dumps(artifact(matrix, values[120:138]), indent=2))
            (arguments.output / "candidate_metrics.json").write_text(json.dumps(record, indent=2))
            if maximum_energy <= 1e-4:
                check = robust_screen(matrix, values[120:138], model.oracle, check_paths=False)
                (arguments.output / "endpoint_screen.json").write_text(json.dumps(check, indent=2))
                if check.get("endpoint_feasible") and check["worst_population_violation"] >= 0.02:
                    raise StopIteration("all 243 endpoints pass; independent certificates required")
        if time.monotonic() - started > arguments.minutes * 60:
            raise StopIteration("private joint finite search time limit")

    global_bounds = np.array(list(map(tuple, model.bounds)) + ([(-1.249, 1.249)] * 18 + [(-1.499, 1.499)] * 18) * 3)
    radii = np.r_[np.full(120, 0.05), np.full(108, 0.15)]
    bounds = list(zip(np.maximum(global_bounds[:, 0], initial - radii), np.minimum(global_bounds[:, 1], initial + radii)))
    message = ""
    try:
        result = minimize(lambda values: evaluate(values)[0][0], initial, jac=lambda values: evaluate(values)[1][0],
                          method="SLSQP", bounds=bounds,
                          constraints=[{"type": "eq", "fun": lambda values: evaluate(values)[0][1:109],
                                        "jac": lambda values: evaluate(values)[1][1:109]},
                                       {"type": "ineq", "fun": lambda values: evaluate(values)[0][109:],
                                        "jac": lambda values: evaluate(values)[1][109:]}],
                          callback=callback, options={"maxiter": arguments.iterations, "ftol": 1e-12})
        callback(result.x)
        matrix = np.einsum("k,kij->ij", result.x[:120], model.axes)
        (arguments.output / "last_iterate.json").write_text(json.dumps(artifact(matrix, result.x[120:138]), indent=2))
        message = str(result.message)
    except Exception as error:
        message = type(error).__name__ + ": " + str(error)
    report = {"best_stationary_three_point_max_energy": best if np.isfinite(best) else None,
              "iterations": iterations, "message": message, "runtime_seconds": time.monotonic() - started}
    (arguments.output / "summary.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
