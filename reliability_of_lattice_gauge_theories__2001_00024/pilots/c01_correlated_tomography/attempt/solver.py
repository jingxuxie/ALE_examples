"""Weighted readout reconstruction and sharp correlated-population bounds."""

import json
import math
import sys

import numpy as np
from scipy.optimize import linprog


def _oscillation(time_ms, calibration):
    times = np.asarray(time_ms, dtype=float)
    angle = 2.0 * np.pi * times / float(calibration["period_ms"])
    angle += float(calibration["phase_rad"])
    return (
        1.0 - np.exp(-times / float(calibration["decay_ms"])) * np.cos(angle)
    ) / 2.0


def _fit_track(track):
    response = _oscillation(track["time_ms"], track["calibration"])
    signal = np.asarray(track["signal"], dtype=float)
    sigma = np.asarray(track["sigma"], dtype=float)
    sigma_scale = float(np.min(sigma))
    weights = np.square(sigma_scale / sigma)
    weight_sum = float(np.sum(weights))
    response_shift = response - response[0]
    signal_shift = signal - signal[0]
    response_mean = float(np.dot(weights, response_shift) / weight_sum)
    signal_mean = float(np.dot(weights, signal_shift) / weight_sum)
    centered_response = response_shift - response_mean
    centered_signal = signal_shift - signal_mean
    information = float(np.dot(weights, np.square(centered_response)))
    if not information > 0.0:
        raise ValueError("Track does not have an identifiable offset and amplitude")
    amplitude = float(
        np.dot(weights * centered_response, centered_signal) / information
    )
    offset = float(
        signal[0] + signal_mean - amplitude * (response[0] + response_mean)
    )
    amplitude_se = sigma_scale / math.sqrt(information)
    query_response = _oscillation(track["query_time_ms"], track["calibration"])
    return {
        "offset": offset,
        "amplitude": amplitude,
        "amplitude_se": amplitude_se,
        "prediction": (offset + amplitude * query_response).tolist(),
    }


def _observation_arrays(occupation, fits):
    responses = []
    centers = []
    radii = []
    for observation in occupation["observations"]:
        responses.append(observation["response"])
        if "center" in observation:
            center = float(observation["center"])
            radius = float(observation["radius"])
        else:
            amplitude_weights = observation["amplitude_weights"]
            center = math.fsum(
                float(weight) * fits[track_id]["amplitude"]
                for track_id, weight in amplitude_weights.items()
            )
            standard_error = math.hypot(
                *(
                    float(weight) * fits[track_id]["amplitude_se"]
                    for track_id, weight in amplitude_weights.items()
                )
            )
            radius = (
                float(observation["sigma_multiplier"]) * standard_error
                + float(observation["systematic_radius"])
            )
        if not radius > 0.0:
            raise ValueError("Observation radii must be strictly positive")
        centers.append(center)
        radii.append(radius)
    state_count = len(occupation["states"])
    return (
        np.asarray(responses, dtype=float).reshape(-1, state_count),
        np.asarray(centers, dtype=float),
        np.asarray(radii, dtype=float),
    )


def _linear_program(objective, inequalities, limits, equality):
    options = {
        "primal_feasibility_tolerance": 1e-10,
        "dual_feasibility_tolerance": 1e-10,
        "ipm_optimality_tolerance": 1e-12,
    }
    result = linprog(
        objective,
        A_ub=inequalities,
        b_ub=limits,
        A_eq=equality,
        b_eq=np.ones(1),
        bounds=(0.0, None),
        method="highs-ds",
        options=options,
    )
    if not result.success:
        result = linprog(
            objective,
            A_ub=inequalities,
            b_ub=limits,
            A_eq=equality,
            b_eq=np.ones(1),
            bounds=(0.0, None),
            method="highs-ipm",
            options=dict(options, presolve=False),
        )
    if not result.success:
        raise RuntimeError("Population linear program failed: " + result.message)
    return result.x


def _distribution(values):
    probabilities = np.maximum(values, 0.0)
    return probabilities / np.sum(probabilities)


def solve(case: dict) -> dict:
    """Solve one independent case using only its supplied numerical model."""
    fits = {track["id"]: _fit_track(track) for track in case["tracks"]}
    occupation = case["occupation"]
    state_count = len(occupation["states"])
    responses, centers, radii = _observation_arrays(occupation, fits)
    bounds = {}
    witnesses = {}
    if len(radii) == 0:
        for target in occupation["targets"]:
            coefficients = np.asarray(target["coefficients"], dtype=float)
            lower_index = int(np.argmin(coefficients))
            upper_index = int(np.argmax(coefficients))
            lower_witness = np.zeros(state_count)
            upper_witness = np.zeros(state_count)
            lower_witness[lower_index] = 1.0
            upper_witness[upper_index] = 1.0
            bounds[target["id"]] = [
                float(coefficients[lower_index]),
                float(coefficients[upper_index]),
            ]
            witnesses[target["id"]] = {
                "lower": lower_witness.tolist(),
                "upper": upper_witness.tolist(),
            }
        return {
            "fits": fits,
            "inflation": 0.0,
            "bounds": bounds,
            "witnesses": witnesses,
        }

    normalized_responses = (responses - centers[:, None]) / radii[:, None]
    signed_responses = np.vstack((normalized_responses, -normalized_responses))
    band_count = len(signed_responses)
    inflation_constraints = np.column_stack(
        (signed_responses, -np.ones(band_count))
    )
    inflation_objective = np.zeros(state_count + 1)
    inflation_objective[-1] = 1.0
    inflation_equality = np.ones((1, state_count + 1))
    inflation_equality[0, -1] = 0.0
    inflation_solution = _linear_program(
        inflation_objective,
        inflation_constraints,
        np.ones(band_count),
        inflation_equality,
    )
    inflation = max(0.0, float(inflation_solution[-1]))
    band_limit = 1.0 + inflation + float(occupation["feasibility_pad"])
    limits = np.full(band_count, band_limit)
    equality = np.ones((1, state_count))
    for target in occupation["targets"]:
        coefficients = np.asarray(target["coefficients"], dtype=float)
        objective = coefficients - float(np.min(coefficients))
        objective_scale = float(np.max(np.abs(objective)))
        if objective_scale > 0.0:
            objective = objective / objective_scale
        lower_witness = _distribution(
            _linear_program(objective, signed_responses, limits, equality)
        )
        upper_witness = _distribution(
            _linear_program(-objective, signed_responses, limits, equality)
        )
        bounds[target["id"]] = [
            float(np.dot(coefficients, lower_witness)),
            float(np.dot(coefficients, upper_witness)),
        ]
        witnesses[target["id"]] = {
            "lower": lower_witness.tolist(),
            "upper": upper_witness.tolist(),
        }
    return {
        "fits": fits,
        "inflation": inflation,
        "bounds": bounds,
        "witnesses": witnesses,
    }


def _main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as input_file:
            case = json.load(input_file)
    else:
        case = json.load(sys.stdin)
    json.dump(solve(case), sys.stdout, allow_nan=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    _main()
