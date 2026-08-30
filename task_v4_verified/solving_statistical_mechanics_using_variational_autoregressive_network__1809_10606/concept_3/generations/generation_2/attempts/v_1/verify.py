import json
from pathlib import Path

from infer import Inference
from evaluate import prediction_function
from posterior import reflective_drift
from transfer import model_from_edges
import numpy as np
from scipy.linalg import cholesky, cho_factor, cho_solve


def main():
    inference = Inference()
    posterior = np.load("chain1.npz")["samples"]
    rng = np.random.default_rng(19087)
    assert np.all(posterior >= inference.lower - 1e-12)
    assert np.all(posterior <= inference.upper + 1e-12)
    predictor, _ = prediction_function(inference)
    maximum_error = 0.0
    for index in [100, 1100, 2100]:
        theta = posterior[index]
        predicted = np.asarray(predictor(theta))
        model = model_from_edges(inference.spec, theta[:172] * inference.signs, theta[172:])
        for query_index, query in enumerate(inference.queries):
            field = np.zeros(96)
            np.add.at(field, query["field_indices"], query["field_values"])
            exact = model.joint(query["beta"], query["readout"], field_delta=field.reshape(12, 8))
            maximum_error = max(maximum_error, np.max(np.abs(predicted[query_index] - exact)))
            np.testing.assert_allclose(predicted[query_index], exact, rtol=1e-8, atol=2e-12)
        assert np.all(np.isfinite(predicted) & (predicted > 0))
    theta = posterior[1700]
    loss, gradient = inference.scipy_loss(theta)
    direction = rng.normal(size=inference.dimension)
    direction /= np.linalg.norm(direction)
    epsilon = 1e-5
    numeric = (inference.scipy_loss(theta + epsilon * direction)[0] -
               inference.scipy_loss(theta - epsilon * direction)[0]) / (2 * epsilon)
    analytic = gradient @ direction
    np.testing.assert_allclose(analytic, numeric, rtol=2e-6, atol=2e-4)
    covariance = np.load("mass_covariance.npy")
    precision = cho_solve(cho_factor(covariance, lower=True), np.eye(inference.dimension))
    momentum = cholesky(precision, lower=True) @ rng.normal(size=inference.dimension)

    def leapfrog(position, current_momentum):
        current_gradient = inference.scipy_loss(position)[1]
        current_momentum = current_momentum - .05 * current_gradient
        for step in range(15):
            position, current_momentum, _ = reflective_drift(
                position, current_momentum, .1, covariance, inference.lower, inference.upper)
            current_gradient = inference.scipy_loss(position)[1]
            current_momentum -= (.05 if step == 14 else .1) * current_gradient
        return position, current_momentum

    proposed_position, proposed_momentum = leapfrog(theta.copy(), momentum.copy())
    recovered_position, recovered_momentum = leapfrog(proposed_position, -proposed_momentum)
    position_error = np.max(np.abs(recovered_position - theta))
    momentum_error = np.max(np.abs(recovered_momentum + momentum))
    np.testing.assert_allclose(recovered_position, theta, atol=1e-9, rtol=1e-9)
    np.testing.assert_allclose(recovered_momentum, -momentum, atol=1e-6, rtol=1e-8)
    report = {"direct_field_simulator_comparisons": 144,
              "maximum_probability_error": float(maximum_error),
              "directional_gradient_error": float(abs(numeric - analytic)),
              "leapfrog_round_trip_position_error": float(position_error),
              "leapfrog_round_trip_momentum_error": float(momentum_error),
              "prior_bounds_verified": True}
    Path("numerical_checks.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
