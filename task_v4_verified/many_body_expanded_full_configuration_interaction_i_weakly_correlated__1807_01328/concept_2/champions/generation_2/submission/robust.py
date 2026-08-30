import argparse
import json
import time

import numpy as np
from scipy.optimize import minimize

from search import BOUNDS, Engine, ROOT, load, save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("start")
    parser.add_argument("--tail", type=float, default=110)
    parser.add_argument("--sigma", type=float, default=3.5)
    parser.add_argument("--box", action="store_true")
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--name", default="robust")
    arguments = parser.parse_args()
    engine = Engine()
    initial = load(arguments.start)
    started = time.monotonic()
    print("Initial", engine.summary(initial), flush=True)
    cache_values = None
    cache_result = None
    iteration = 0
    best = np.inf

    def evaluate(values):
        nonlocal cache_values, cache_result
        if cache_values is None or not np.array_equal(cache_values, values):
            increments, jacobian, tail, tail_gradient, properties, hessian = engine.evaluate(values[:42], second_order=True)
            deviations = 0.001 / np.sqrt(3) * np.linalg.norm(jacobian, axis=1)
            deviation_jacobian = (0.001 ** 2 / 3) * np.einsum("ijk,ij->ik", hessian, jacobian) / np.maximum(deviations[:, None], 1e-15)
            if arguments.box:
                smoothed = np.sqrt(jacobian ** 2 + 0.01 ** 2)
                deviations = 0.001 * smoothed.sum(axis=1)
                deviation_jacobian = 0.001 * np.einsum("ijk,ij->ik", hessian, jacobian / smoothed)
            upper = increments + arguments.sigma * deviations
            lower = -increments + arguments.sigma * deviations
            constraints = np.r_[values[42] - upper, values[42] - lower, (-tail - arguments.tail) / 100]
            derivatives = np.zeros((71, 43))
            derivatives[:35, :42] = -jacobian - arguments.sigma * deviation_jacobian
            derivatives[35:70, :42] = jacobian - arguments.sigma * deviation_jacobian
            derivatives[:70, 42] = 1
            derivatives[70, :42] = -tail_gradient / 100
            cache_values = values.copy()
            cache_result = constraints, derivatives, float(max(upper.max(), lower.max())), float(tail), properties
        return cache_result

    def callback(values):
        nonlocal iteration, best
        constraints, derivatives, bound, tail, properties = evaluate(values)
        if bound < best and tail <= -arguments.tail + 1e-3 and properties[0] >= 0.95 and properties[1] >= 0.4:
            best = bound
            save(values[:42], arguments.name + "_best.json")
        if iteration % 10 == 0:
            print("Iteration", iteration, "time", time.monotonic() - started, "bound", bound, "slack", values[42], "tail", tail, "properties", properties.tolist(), flush=True)
        iteration += 1

    values = np.r_[initial, 5.0]
    initial_bound = evaluate(values)[2]
    values[42] = initial_bound
    objective_gradient = np.r_[np.zeros(42), 1.0]
    result = minimize(lambda values: values[42], values, jac=lambda values: objective_gradient, method="SLSQP", bounds=list(zip(-BOUNDS + 1e-10, BOUNDS - 1e-10)) + [(0, None)], constraints=[dict(type="ineq", fun=lambda values: evaluate(values)[0], jac=lambda values: evaluate(values)[1])], callback=callback, options=dict(maxiter=arguments.steps, ftol=1e-9, disp=True))
    save(result.x[:42], arguments.name + ".json")
    print("Final", result.message, "objective", result.fun, "minconstraint", evaluate(result.x)[0].min(), "time", time.monotonic() - started, engine.summary(result.x[:42]), flush=True)


if __name__ == "__main__":
    main()
