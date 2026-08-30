"""Weak fixed-design two-pole fit. Deliberately does not model the positive tail."""

import json
import math
import sys

import numpy as np
from scipy.optimize import least_squares

from model import TARGETS, canonical_angle, noise_std


def predict(parameters, times, probes, jacobian=False):
    delta0, log_gap, log_a0, theta0, log_a1, theta1 = parameters
    gap = np.exp(log_gap)
    projection0 = probes[:, 0] * np.cos(theta0) + probes[:, 1] * np.sin(theta0)
    projection1 = probes[:, 0] * np.cos(theta1) + probes[:, 1] * np.sin(theta1)
    weight0 = np.exp(log_a0 - delta0 * times)
    weight1 = np.exp(log_a1 - (delta0 + gap) * times)
    term0, term1 = weight0 * projection0 ** 2, weight1 * projection1 ** 2
    values = term0 + term1
    if not jacobian:
        return values
    tangent0 = -probes[:, 0] * np.sin(theta0) + probes[:, 1] * np.cos(theta0)
    tangent1 = -probes[:, 0] * np.sin(theta1) + probes[:, 1] * np.cos(theta1)
    derivatives = np.column_stack([
        -times * values, -times * gap * term1, term0,
        2 * weight0 * projection0 * tangent0, term1,
        2 * weight1 * projection1 * tangent1,
    ])
    return values, derivatives


def fixed_design():
    return [
        (time, [math.cos(angle), math.sin(angle)])
        for time in (0.4, 1.3, 2.4, 3.3, 4.5, 5.8)
        for angle in (0.0, math.pi / 4, math.pi / 2, 3 * math.pi / 4)
        for repeat in range(3)
    ]


def fit(records):
    selected = [record for record in records if record[0] >= 2.4]
    times = np.array([record[0] for record in selected])
    probes = np.array([record[1] for record in selected])
    values = np.array([record[2] for record in selected])
    sigma = noise_std(times)
    lower = [0.65, math.log(0.025), math.log(0.02), -2 * math.pi, math.log(0.02), -2 * math.pi]
    upper = [1.35, math.log(1.0), math.log(3.5), 2 * math.pi, math.log(3.5), 2 * math.pi]
    rng = np.random.default_rng(2917)
    best = None
    for restart in range(8):
        initial = [0.95, math.log(0.1 if restart < 2 else 0.55), math.log(0.5),
                   rng.uniform(-math.pi / 2, math.pi / 2), math.log(0.8),
                   rng.uniform(-math.pi / 2, math.pi / 2)]
        result = least_squares(
            lambda parameters: (predict(parameters, times, probes) - values) / sigma,
            initial, bounds=(lower, upper),
            jac=lambda parameters: predict(parameters, times, probes, True)[1] / sigma[:, None],
            max_nfev=450, ftol=1e-8, xtol=1e-8, gtol=1e-8,
        )
        if best is None or result.cost < best.cost:
            best = result
    estimate = best.x[:4].copy()
    estimate[3] = canonical_angle(estimate[3])
    covariance = np.linalg.pinv(best.jac.T @ best.jac, rcond=1e-12)
    radii = 1.645 * np.sqrt(np.maximum(0, covariance.diagonal()[:4]))
    radii += np.array([0.02, 0.18, 0.16, 0.07])
    radii = np.minimum(radii, [0.3, 2.0, 2.0, math.pi / 2])
    return estimate, radii


def main():
    hello = json.loads(sys.stdin.readline())
    if hello.get("type") != "hello" or hello.get("budget") != 72:
        raise RuntimeError("unsupported experiment")
    records = []
    for time, probe in fixed_design():
        print(json.dumps({"type": "measure", "t": time, "u": probe}), flush=True)
        response = json.loads(sys.stdin.readline())
        if response.get("type") != "observation":
            raise RuntimeError("oracle did not return observation")
        records.append((time, probe, response["y"]))
    estimate, radii = fit(records)
    print(json.dumps({
        "type": "answer", "estimate": dict(zip(TARGETS, estimate.tolist())),
        "radius90": dict(zip(TARGETS, radii.tolist())),
    }, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
