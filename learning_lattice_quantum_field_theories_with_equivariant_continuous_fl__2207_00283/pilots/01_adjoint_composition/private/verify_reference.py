"""Independent analytic and finite-difference checks of official outputs."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "private/reference/implementation"))

import jax.numpy as jnp
import numpy as np

from api import evaluate_case, make_map


def main():
    pool = ROOT / "private/challenge_pool/standard"
    request = json.loads((pool / "request.json").read_text())
    reference = json.loads((pool / "reference.json").read_text())["results"]
    linear = request["cases"][0]
    inputs = np.asarray(linear["x"])
    parameters = np.asarray(linear["parameters"])
    duration = linear["times"][1] - linear["times"][0]
    expected_state = np.fft.irfft(np.fft.rfft(inputs) * np.exp(parameters[4:]), n=inputs.size)
    expected_state *= np.exp(parameters[0] * duration)
    weights = np.full(parameters.size - 4, 2.0)
    weights[0] = 1.0
    if inputs.size % 2 == 0:
        weights[-1] = 1.0
    expected_density = linear["log_density"] - np.dot(weights, parameters[4:]) - inputs.size * parameters[0] * duration
    linear_error = max(float(np.max(np.abs(expected_state - reference[linear["id"]]["state"]))),
                       abs(expected_density - reference[linear["id"]]["log_density"]))
    case = dict(request["cases"][1])
    case["steps"] *= 4
    result = evaluate_case(case)
    transform = make_map(case["direction"], case["steps"])
    epsilon = 1e-5

    def objective(candidate):
        state, density = transform(
            jnp.asarray(candidate["x"]), jnp.asarray(candidate["parameters"]),
            jnp.asarray(candidate["times"]), jnp.asarray(candidate["log_density"]),
        )
        return float(jnp.vdot(jnp.asarray(candidate["cotangent"]), state) + candidate["density_weight"] * density)

    finite_difference_errors = {}
    for input_field, gradient_field in (("x", "input_gradient"), ("parameters", "parameter_gradient"), ("times", "time_gradient")):
        numeric = []
        for index in range(len(case[input_field])):
            upper = json.loads(json.dumps(case))
            lower = json.loads(json.dumps(case))
            upper[input_field][index] += epsilon
            lower[input_field][index] -= epsilon
            numeric.append((objective(upper) - objective(lower)) / (2 * epsilon))
        numeric = np.asarray(numeric)
        finite_difference_errors[gradient_field] = float(np.max(np.abs(numeric - result[gradient_field]) / (1 + np.abs(numeric))))
    evidence = {"linear_analytic_max_error": linear_error,
                "inverse_finite_difference_max_relative_errors": finite_difference_errors,
                "finite_difference_epsilon": epsilon,
                "reference_implementation": "official fixed source; analytic FFT/linear ODE and primal-only finite differences used as independent checks"}
    if linear_error > 1e-8 or max(finite_difference_errors.values()) > 2e-6:
        raise RuntimeError(json.dumps(evidence))
    (ROOT / "private/reference_validation.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence))


if __name__ == "__main__":
    main()
