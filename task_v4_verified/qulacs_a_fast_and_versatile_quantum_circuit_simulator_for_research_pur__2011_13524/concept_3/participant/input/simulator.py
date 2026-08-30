import math

import numpy as np


PARAMETERS = (
    "f1", "f2", "coupling", "sigma1", "sigma2", "rho",
    "visibility1", "visibility2", "bias1", "bias2",
)
BOUNDS = np.array([
    [0.25, 2.15], [0.25, 2.15], [0.015, 0.22],
    [0.08, 0.46], [0.08, 0.46], [-0.90, 0.90],
    [0.48, 0.90], [0.48, 0.90], [-0.09, 0.09], [-0.09, 0.09],
])
SCALES = np.array([0.025, 0.025, 0.018, 0.075, 0.075, 0.32, 0.09, 0.09, 0.065, 0.065])
MODES = ("q1+", "q1-", "q2+", "q2-", "bell+", "bell-")
FAMILIES = ("resolved", "close_coupled", "low_visibility_spam")
BUDGET = {"queries": 48, "shots": 6144, "max_shots_per_query": 1024}
PROTOCOL = "correlated-ramsey-v1"


def numeric(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_action(action):
    if not isinstance(action, dict) or set(action) != {"type", "mode", "time", "phase", "shots"}:
        raise ValueError("action must have exactly type, mode, time, phase, shots")
    if action["type"] != "experiment" or action["mode"] not in MODES:
        raise ValueError("unknown experiment mode")
    if not numeric(action["time"]) or not 0 <= action["time"] <= 6:
        raise ValueError("time must be finite in [0,6]")
    if not numeric(action["phase"]) or not -math.pi <= action["phase"] <= math.pi:
        raise ValueError("phase must be finite in [-pi,pi]")
    if type(action["shots"]) is not int or not 1 <= action["shots"] <= BUDGET["max_shots_per_query"]:
        raise ValueError("shots must be an integer in [1,1024]")
    return action


def validate_estimate(message):
    if not isinstance(message, dict) or set(message) != {"type", "parameters"} or message["type"] != "estimate":
        raise ValueError("estimate must have exactly type=estimate and parameters")
    values = message["parameters"]
    if not isinstance(values, dict) or set(values) != set(PARAMETERS):
        raise ValueError("parameters must contain exactly the ten named parameters")
    if not all(numeric(values[name]) for name in PARAMETERS):
        raise ValueError("all parameters must be finite JSON numbers")
    theta = np.array([values[name] for name in PARAMETERS])
    if np.any(theta < BOUNDS[:, 0]) or np.any(theta > BOUNDS[:, 1]):
        raise ValueError("parameter out of range")
    return theta


def parameter_dict(theta):
    return dict(zip(PARAMETERS, map(float, theta)))


def encode_actions(actions):
    mode = np.array([MODES.index(action["mode"]) for action in actions])
    times = np.array([action["time"] for action in actions], dtype=float)
    phases = np.array([action["phase"] for action in actions], dtype=float)
    return mode, times, phases


def probabilities(theta, actions, jacobian=False):
    encoded = actions if isinstance(actions, tuple) else encode_actions(actions)
    mode, times, phases = encoded
    theta = np.asarray(theta, dtype=float)
    f1, f2, coupling, sigma1, sigma2, rho, vis1, vis2, bias1, bias2 = theta
    frequency = np.array([f1 + coupling, f1 - coupling, f2 + coupling, f2 - coupling, f1 + f2, f1 - f2])[mode]
    variance = np.array([
        sigma1 ** 2, sigma1 ** 2, sigma2 ** 2, sigma2 ** 2,
        sigma1 ** 2 + sigma2 ** 2 + 2 * rho * sigma1 * sigma2,
        sigma1 ** 2 + sigma2 ** 2 - 2 * rho * sigma1 * sigma2,
    ])[mode]
    visibility = np.array([vis1, vis1, vis2, vis2, vis1 * vis2, vis1 * vis2])[mode]
    bias = np.array([bias1, bias1, bias2, bias2, bias1 * bias2, bias1 * bias2])[mode]
    angle = 2 * np.pi * frequency * times - phases
    envelope = np.exp(-0.5 * variance * times ** 2)
    carrier = envelope * np.cos(angle)
    probability = 0.5 * (1 + bias + visibility * carrier)
    if not jacobian:
        return probability
    derivative = np.zeros((len(times), 10))
    frequency_gradient = np.array([[1, 0, 1], [1, 0, -1], [0, 1, 1], [0, 1, -1], [1, 1, 0], [1, -1, 0]])[mode]
    derivative[:, :3] = (-np.pi * visibility * envelope * np.sin(angle) * times)[:, None] * frequency_gradient
    variance_gradient = np.array([
        [2 * sigma1, 0, 0], [2 * sigma1, 0, 0],
        [0, 2 * sigma2, 0], [0, 2 * sigma2, 0],
        [2 * sigma1 + 2 * rho * sigma2, 2 * sigma2 + 2 * rho * sigma1, 2 * sigma1 * sigma2],
        [2 * sigma1 - 2 * rho * sigma2, 2 * sigma2 - 2 * rho * sigma1, -2 * sigma1 * sigma2],
    ])[mode]
    derivative[:, 3:6] = (-0.25 * visibility * carrier * times ** 2)[:, None] * variance_gradient
    derivative[:, 6] = 0.5 * carrier * np.array([1, 1, 0, 0, vis2, vis2])[mode]
    derivative[:, 7] = 0.5 * carrier * np.array([0, 0, 1, 1, vis1, vis1])[mode]
    derivative[:, 8] = 0.5 * np.array([1, 1, 0, 0, bias2, bias2])[mode]
    derivative[:, 9] = 0.5 * np.array([0, 0, 1, 1, bias1, bias1])[mode]
    return probability, derivative


def sample_prior(family, rng):
    if family not in FAMILIES:
        raise ValueError("unknown prior family")
    if family == "close_coupled":
        f1 = rng.uniform(0.45, 1.90)
        f2 = f1 + rng.uniform(0.025, 0.10)
        coupling = rng.uniform(0.10, 0.20)
        sigmas = rng.uniform(0.16, 0.34, 2)
        rho = rng.choice([-1, 1]) * rng.uniform(0.40, 0.85)
        visibilities = rng.uniform(0.68, 0.88, 2)
        biases = rng.uniform(-0.08, 0.08, 2)
    else:
        minimum_gap = 0.35 if family == "resolved" else 0.15
        f1, f2 = rng.uniform(0.35, 2.05, 2)
        while abs(f1 - f2) < minimum_gap:
            f1, f2 = rng.uniform(0.35, 2.05, 2)
        coupling = rng.uniform(0.025, 0.16 if family == "resolved" else 0.20)
        if family == "resolved":
            sigmas = rng.uniform(0.10, 0.28, 2)
            rho = rng.uniform(-0.65, 0.65)
            visibilities = rng.uniform(0.78, 0.90, 2)
            biases = rng.uniform(-0.06, 0.06, 2)
        else:
            sigmas = rng.uniform(0.24, 0.44, 2)
            rho = rng.uniform(-0.85, 0.85)
            visibilities = rng.uniform(0.50, 0.68, 2)
            biases = rng.uniform(-0.085, 0.085, 2)
    return np.array([f1, f2, coupling, *sigmas, rho, *visibilities, *biases])


def metadata():
    return {
        "type": "start", "protocol": PROTOCOL,
        "budget": dict(BUDGET), "wall_seconds": 45, "cpu_seconds": 40,
        "memory_mib": 1024, "bounds": dict(zip(PARAMETERS, BOUNDS.tolist())),
        "modes": list(MODES), "time_range": [0, 6], "phase_range": [-math.pi, math.pi],
        "families": list(FAMILIES),
        "remaining": {"queries": BUDGET["queries"], "shots": BUDGET["shots"]},
    }


def predictive_grid():
    return [
        {"mode": mode, "time": float(time), "phase": float(phase)}
        for mode in MODES
        for time in np.linspace(0.125, 6.0, 49)
        for phase in (0.0, np.pi / 2)
    ]


def score_estimate(truth, estimate):
    normalized = (np.asarray(estimate) - np.asarray(truth)) / SCALES
    parameter_loss = float(np.mean(np.minimum(normalized ** 2, 16)))
    difference = probabilities(truth, predictive_grid()) - probabilities(estimate, predictive_grid())
    predictive_mse = float(np.mean(difference ** 2))
    score = float(100 * np.exp(-0.45 * parameter_loss - 0.55 * predictive_mse / 0.04 ** 2))
    return {"score": score, "parameter_loss": parameter_loss, "predictive_rmse": math.sqrt(predictive_mse)}
