import numpy as np
from scipy.optimize import minimize
from scipy.signal import find_peaks

from simulator import BOUNDS, MODES, encode_actions, probabilities


def fixed_design(shots=128):
    actions = []
    times = [0.0, 0.37, 0.91, 1.57, 2.43, 3.61, 4.79, 5.93]
    for mode in MODES[:4]:
        for index, time in enumerate(times):
            phase = (index % 2) * np.pi / 2
            actions.append({"type": "experiment", "mode": mode, "time": time, "phase": float(phase), "shots": shots})
    for mode in ("q1+", "q2+"):
        for phase in (np.pi, np.pi / 2):
            actions.append({"type": "experiment", "mode": mode, "time": 0.0, "phase": float(phase), "shots": shots})
    for mode in MODES[4:]:
        for index, time in enumerate([0.41, 1.19, 2.17, 3.23, 4.47, 5.77]):
            actions.append({"type": "experiment", "mode": mode, "time": time, "phase": float((index % 2) * np.pi / 2), "shots": shots})
    return actions


def frequency_candidates(mode_index, encoded, counts, shots):
    modes, times, phases = encoded
    sensor = mode_index // 2
    mask = (modes == mode_index) | ((modes // 2 == sensor) & (times == 0))
    times, phases = times[mask], phases[mask]
    response = 2 * (counts[mask] + 0.5) / (shots[mask] + 1) - 1
    weights = shots[mask] / np.maximum(1 - response ** 2, 0.08)
    frequencies = np.linspace(0.03, 2.37, 1171)
    gammas = np.linspace(0.08, 0.46, 7)
    carrier = np.cos(2 * np.pi * frequencies[:, None, None] * times - phases) * np.exp(-0.5 * gammas[None, :, None] ** 2 * times ** 2)
    sum_weight = weights.sum()
    sum_carrier = (weights * carrier).sum(axis=-1)
    sum_squared = (weights * carrier ** 2).sum(axis=-1)
    sum_response = (weights * response).sum()
    sum_product = (weights * carrier * response).sum(axis=-1)
    determinant = np.maximum(sum_weight * sum_squared - sum_carrier ** 2, 1e-9)
    visibility = np.clip((sum_weight * sum_product - sum_carrier * sum_response) / determinant, 0.48, 0.90)
    bias = np.clip((sum_response - visibility * sum_carrier) / sum_weight, -0.09, 0.09)
    cost = np.sum(weights * (response - bias[..., None] - visibility[..., None] * carrier) ** 2, axis=-1)
    gamma_index = cost.argmin(axis=1)
    best_cost = cost[np.arange(len(frequencies)), gamma_index]
    peaks = find_peaks(-best_cost, distance=15)[0]
    peaks = np.unique(np.concatenate(([0, len(frequencies) - 1, best_cost.argmin()], peaks)))
    best = peaks[np.argsort(best_cost[peaks])[:18]]
    return [
        (float(best_cost[index]), float(frequencies[index]), float(gammas[gamma_index[index]]),
         float(visibility[index, gamma_index[index]]), float(bias[index, gamma_index[index]]))
        for index in best
    ]


def starting_points(encoded, counts, shots):
    candidates = [frequency_candidates(mode, encoded, counts, shots) for mode in range(4)]
    sensor_candidates = []
    for sensor in range(2):
        pairs = []
        for plus in candidates[2 * sensor]:
            for minus in candidates[2 * sensor + 1]:
                frequency = (plus[1] + minus[1]) / 2
                coupling = (plus[1] - minus[1]) / 2
                if 0.25 <= frequency <= 2.15 and 0.005 <= coupling <= 0.235:
                    pairs.append((plus[0] + minus[0], frequency, coupling,
                                  (plus[2] + minus[2]) / 2, (plus[3] + minus[3]) / 2, (plus[4] + minus[4]) / 2))
        sensor_candidates.append(sorted(pairs)[:24])
    starts = []
    for first in sensor_candidates[0]:
        for second in sensor_candidates[1]:
            cost = first[0] + second[0] + ((first[2] - second[2]) / 0.01) ** 2
            theta = np.array([first[1], second[1], (first[2] + second[2]) / 2, first[3], second[3],
                              0.0, first[4], second[4], first[5], second[5]])
            starts.append((cost, theta))
    if not starts:
        return [(BOUNDS[:, 0] + BOUNDS[:, 1]) / 2]
    starts.sort(key=lambda entry: entry[0])
    return [np.clip(theta, BOUNDS[:, 0] + 1e-7, BOUNDS[:, 1] - 1e-7) for _, theta in starts[:32]]


def fit(history, initial=None, multistart=True, return_candidates=False):
    actions = [entry["action"] for entry in history]
    encoded = encode_actions(actions)
    counts = np.array([entry["counts"][0] for entry in history])
    shots = np.array([sum(entry["counts"]) for entry in history])
    width = BOUNDS[:, 1] - BOUNDS[:, 0]

    def objective(unit_theta):
        theta = BOUNDS[:, 0] + width * unit_theta
        probability, gradient = probabilities(theta, encoded, jacobian=True)
        probability = np.clip(probability, 1e-10, 1 - 1e-10)
        loss = -np.sum(counts * np.log(probability) + (shots - counts) * np.log1p(-probability))
        derivative = gradient.T @ ((shots * probability - counts) / (probability * (1 - probability)))
        return loss, derivative * width

    starts = starting_points(encoded, counts, shots) if multistart else []
    if initial is not None:
        starts.insert(0, np.asarray(initial))
    if not starts:
        starts = [(BOUNDS[:, 0] + BOUNDS[:, 1]) / 2]
    fitted = []
    for theta in starts:
        result = minimize(objective, (theta - BOUNDS[:, 0]) / width, method="L-BFGS-B", jac=True,
                          bounds=[(0, 1)] * 10, options={"maxiter": 240, "ftol": 1e-11, "gtol": 1e-5})
        fitted.append((float(result.fun), BOUNDS[:, 0] + width * result.x))
    fitted.sort(key=lambda entry: entry[0])
    if return_candidates:
        return fitted
    return fitted[0][1]
