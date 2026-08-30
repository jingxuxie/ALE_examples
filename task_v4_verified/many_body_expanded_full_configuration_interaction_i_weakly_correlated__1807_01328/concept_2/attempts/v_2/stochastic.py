import argparse
import json
import time

import numpy as np
from scipy.optimize import least_squares

from search import BOUNDS, Engine, ROOT, load, save


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start")
    parser.add_argument("--samples", type=int, default=512)
    parser.add_argument("--limit", type=float, default=0.9)
    parser.add_argument("--tail", type=float, default=105)
    parser.add_argument("--steps", type=int, default=350)
    parser.add_argument("--name", default="sample")
    arguments = parser.parse_args()
    engine = Engine()
    uniforms = np.random.default_rng(89347023).random((arguments.samples, 42))
    started = time.monotonic()

    def predict(coefficients):
        increments, jacobian, tail, tail_gradient, properties, hessian = engine.evaluate(coefficients, second_order=True)
        lower = np.maximum(-BOUNDS, coefficients - 0.001)
        upper = np.minimum(BOUNDS, coefficients + 0.001)
        noise = lower + (upper - lower) * uniforms - coefficients
        slopes = (1 - uniforms) * (coefficients - 0.001 > -BOUNDS) + uniforms * (coefficients + 0.001 < BOUNDS)
        correction_gradient = np.einsum("tij,sj->sti", hessian, noise, optimize=True)
        predicted = increments + noise @ jacobian.T + 0.5 * np.einsum("sti,si->st", correction_gradient, noise)
        predicted_gradient = (jacobian + correction_gradient) * slopes[:, None, :]
        return increments, jacobian, tail, tail_gradient, properties, predicted, predicted_gradient

    if arguments.start:
        starts = [(0, arguments.start)]
    else:
        starts = []
        for path in sorted(ROOT.glob("box_??.json")):
            coefficients = load(path)
            increments, jacobian, tail, tail_gradient, properties, predicted, predicted_gradient = predict(coefficients)
            maximum = np.max(np.abs(predicted), axis=1)
            quantile = max(float(np.quantile(maximum, 0.99)), float(np.max(np.abs(increments))))
            starts.append((quantile, str(path)))
        starts.sort()
        print("RANKING", starts, flush=True)
        starts = starts[:4]

    for index, (quantile, path) in enumerate(starts):
        coefficients = load(path)
        name = arguments.name + "_%02d" % index
        print("START", name, path, engine.summary(coefficients), flush=True)
        cache_coefficients = None
        cache_result = None
        calls = 0

        def objective(values, derivative=False):
            nonlocal cache_coefficients, cache_result, calls
            if cache_coefficients is None or not np.array_equal(values, cache_coefficients):
                increments, jacobian, tail, tail_gradient, properties, predicted, predicted_gradient = predict(values)
                excess = np.maximum(np.abs(predicted) - arguments.limit, 0)
                sample_gradient = predicted_gradient * (np.sign(predicted) * (excess > 0))[:, :, None]
                nominal_excess = np.maximum(np.abs(increments) - arguments.limit, 0)
                nominal_gradient = jacobian * (np.sign(increments) * (nominal_excess > 0))[:, None]
                residual = np.r_[excess.ravel() / np.sqrt(arguments.samples), nominal_excess, (tail + arguments.tail) * 0.2]
                derivatives = np.vstack([sample_gradient.reshape(-1, 42) / np.sqrt(arguments.samples), nominal_gradient, tail_gradient * 0.2])
                cache_coefficients = values.copy()
                cache_result = residual, derivatives
                if calls % 20 == 0:
                    maximum = np.max(np.abs(predicted), axis=1)
                    print(name, "CALL", calls, "cost", float(residual @ residual), "nominal", float(np.max(np.abs(increments))), "success", float(np.mean(maximum <= 1)), "quantiles", np.quantile(maximum, [0.5, 0.95, 0.99, 1]).tolist(), "tail", tail, "elapsed", time.monotonic() - started, flush=True)
                    save(values, name + "_checkpoint.json")
                calls += 1
            return cache_result[int(derivative)]

        result = least_squares(objective, coefficients, jac=lambda values: objective(values, True), bounds=(-BOUNDS + 1e-12, BOUNDS - 1e-12), max_nfev=arguments.steps, ftol=1e-7, xtol=1e-9, gtol=1e-7)
        save(result.x, name + ".json")
        print("FINAL", name, result.message, "cost", result.cost, engine.summary(result.x), flush=True)


if __name__ == "__main__":
    main()
