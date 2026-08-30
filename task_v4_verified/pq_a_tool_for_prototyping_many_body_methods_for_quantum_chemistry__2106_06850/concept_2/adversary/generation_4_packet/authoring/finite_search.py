"""Private nonlinear optimization of the actual two adaptive neighboring roots."""

import argparse
import json
import time
from pathlib import Path

from reduced_search import ReducedModel, artifact, robust_screen

import numpy as np
from scipy.optimize import minimize


class FiniteModel:
    def __init__(self, source, dad, target):
        self.base = ReducedModel(source, dad, 1e-4, target)
        self.cache = {}

    def evaluate(self, coordinates):
        key = coordinates.tobytes()
        if key not in self.cache:
            response, hessian = self.base.stationary_response(coordinates)
            norm = np.linalg.norm(response)
            if norm <= 1e-12:
                direction = np.eye(120)[0]
                derivative_direction = np.zeros((120, 120))
            else:
                direction = response / norm
                derivative_direction = (np.eye(120) - np.outer(direction, direction)) @ hessian / norm
            objective = 1e-6 * coordinates @ coordinates
            objective_gradient = 2e-6 * coordinates
            inequalities, derivatives, records = [], [], []
            base_values = None
            for sign in (0, 1, -1):
                point = coordinates + sign * 0.001 * direction
                transformation = np.eye(120) + sign * 0.001 * derivative_direction
                output, derivative, info, full = self.base.evaluate(point)
                gradient = np.array(self.base.response_function(full))
                energy_error = info[1]
                objective += energy_error ** 2 / 1e-8
                objective_gradient += 2 * energy_error / 1e-8 * gradient @ transformation
                inequalities.extend(output[37:])
                derivatives.extend(derivative[37:] @ transformation)
                records.append(info.tolist())
                if sign == 0:
                    base_values = full.copy()
                    self.base.amplitudes = full[120:138].copy()
            self.cache.clear()
            self.cache[key] = (float(objective), objective_gradient, np.array(inequalities),
                               np.array(derivatives), records, base_values, float(norm))
        return self.cache[key]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=160)
    parser.add_argument("--stages", type=int, default=15)
    parser.add_argument("--minutes", type=float, default=12)
    parser.add_argument("--dad", type=float, default=0.0009)
    parser.add_argument("--target", type=float, default=0.0201)
    parser.add_argument("--step", type=float, default=0.05)
    parser.add_argument("--soft-energy", action="store_true")
    arguments = parser.parse_args()
    arguments.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    model = FiniteModel(arguments.source, arguments.dad, arguments.target)
    center = model.base.initial.copy()
    iterations = 0
    best = float("inf")
    records = []
    retained_center = center.copy()
    retained_amplitudes = model.base.amplitudes.copy()

    def constraint_values(values):
        inequalities = model.evaluate(values)[2]
        return inequalities.reshape((3, -1))[:, 2:].reshape(-1) if arguments.soft_energy else inequalities

    def constraint_derivative(values):
        derivative = model.evaluate(values)[3]
        return derivative.reshape((3, -1, 120))[:, 2:].reshape((-1, 120)) if arguments.soft_energy else derivative

    def callback(coordinates):
        nonlocal iterations, best
        objective, derivative, inequalities, jacobian, info, full, gradient_norm = model.evaluate(coordinates)
        iterations += 1
        maximum_error = max(abs(point[1]) for point in info)
        physical = np.array(inequalities).reshape((3, -1))[:, 2:]
        record = {"iteration": iterations, "gradient_norm": gradient_norm, "max_finite_energy_error": maximum_error,
                  "minimum_all_margin": float(min(inequalities)), "minimum_nonenergy_margin": float(np.min(physical)),
                  "max_dad": max(point[8] for point in info), "min_population": min(point[9] for point in info),
                  "elapsed_seconds": time.monotonic() - started}
        if iterations % 10 == 0:
            print(json.dumps(record), flush=True)
        if np.min(physical) >= -1e-7 and maximum_error < best:
            best = maximum_error
            matrix = np.einsum("k,kij->ij", coordinates, model.base.axes)
            (arguments.output / "candidate.json").write_text(json.dumps(artifact(matrix, full[120:138]), indent=2))
            (arguments.output / "candidate_metrics.json").write_text(json.dumps(record, indent=2))
            if maximum_error <= 1e-4:
                complete = robust_screen(matrix, full[120:138], model.base.oracle, check_paths=False)
                (arguments.output / "endpoint_screen.json").write_text(json.dumps(complete, indent=2))
                if complete.get("endpoint_feasible") and complete["worst_population_violation"] >= 0.02:
                    raise StopIteration("all 243 endpoints pass; independent certification required")
        if time.monotonic() - started > arguments.minutes * 60:
            raise StopIteration("private finite-search time limit")

    for stage in range(arguments.stages):
        lower = np.maximum(model.base.bounds[:, 0], center - arguments.step)
        upper = np.minimum(model.base.bounds[:, 1], center + arguments.step)
        try:
            result = minimize(lambda values: model.evaluate(values)[0], center,
                              jac=lambda values: model.evaluate(values)[1], method="SLSQP",
                              bounds=list(zip(lower, upper)),
                              constraints=[{"type": "ineq", "fun": constraint_values,
                                            "jac": constraint_derivative}],
                              callback=callback, options={"maxiter": arguments.iterations, "ftol": 1e-12})
            callback(result.x)
            if min(constraint_values(result.x)) < -0.005 or model.evaluate(result.x)[4][0][2] < 0.995:
                arguments.step *= 0.5
                center = retained_center.copy()
                model.base.amplitudes = retained_amplitudes.copy()
                model.base.cache.clear()
                model.cache.clear()
                print(json.dumps({"stage": stage, "rollback": "invalid endpoint branch or excessive constraint loss"}), flush=True)
                continue
            center = result.x.copy()
            full = model.evaluate(center)[5]
            retained_center = center.copy()
            retained_amplitudes = full[120:138].copy()
            model.base.amplitudes = retained_amplitudes.copy()
            matrix = np.einsum("k,kij->ij", center, model.base.axes)
            (arguments.output / "last_iterate.json").write_text(json.dumps(artifact(matrix, full[120:138]), indent=2))
            record = {"stage": stage, "message": str(result.message), "objective": model.evaluate(center)[0],
                      "minimum_margin": float(min(model.evaluate(center)[2])), "elapsed_seconds": time.monotonic() - started}
            records.append(record)
            print(json.dumps(record), flush=True)
        except StopIteration as error:
            records.append({"stage": stage, "stop": str(error)})
            break
        except Exception as error:
            records.append({"stage": stage, "error": type(error).__name__ + ": " + str(error)})
            print(json.dumps(records[-1]), flush=True)
            arguments.step *= 0.5
            model.base.amplitudes = retained_amplitudes.copy()
            center = retained_center.copy()
            model.base.cache.clear()
            model.cache.clear()
        if time.monotonic() - started > arguments.minutes * 60:
            break
    summary = {"best_max_finite_energy_error": best if np.isfinite(best) else None,
               "records": records, "runtime_seconds": time.monotonic() - started}
    (arguments.output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
