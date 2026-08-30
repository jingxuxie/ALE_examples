import json
import sys
from pathlib import Path

import numpy as np


root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / "input"))

from estimation import fit, fixed_design
from simulator import BOUNDS, MODES, SCALES, parameter_dict, predictive_grid, probabilities


def next_action(history, candidates, next_shots=128):
    theta = candidates[0][1]
    observed_actions = [entry["action"] for entry in history]
    shots = np.array([sum(entry["counts"]) for entry in history])
    probability, gradient = probabilities(theta, observed_actions, jacobian=True)
    width = BOUNDS[:, 1] - BOUNDS[:, 0]
    information = gradient.T @ ((shots / (probability * (1 - probability)))[:, None] * gradient)
    covariance = np.linalg.inv(information + np.diag(12 / width ** 2))
    _, prediction_gradient = probabilities(theta, predictive_grid(), jacobian=True)
    weight = 0.45 * np.diag(1 / SCALES ** 2) / 10 + 0.55 * prediction_gradient.T @ prediction_gradient / len(prediction_gradient) / 0.04 ** 2
    frequencies = [theta[0] + theta[2], theta[0] - theta[2], theta[1] + theta[2], theta[1] - theta[2], theta[0] + theta[1], theta[0] - theta[1]]
    actions = []
    for mode, frequency in zip(MODES, frequencies):
        for time in np.linspace(0, 6, 41):
            for shift in (0, np.pi / 2, np.pi):
                phase = (2 * np.pi * frequency * time + shift + np.pi) % (2 * np.pi) - np.pi
                actions.append({"type": "experiment", "mode": mode, "time": float(time), "phase": float(phase), "shots": next_shots})
    prediction, derivative = probabilities(theta, actions, jacobian=True)
    projected = derivative @ covariance
    variance = np.einsum("ij,ij->i", projected, derivative)
    reduction = next_shots * np.einsum("ij,ij->i", projected @ weight, projected) / (prediction * (1 - prediction) + next_shots * variance)
    distinct = []
    for cost, candidate in candidates:
        if cost - candidates[0][0] > 12:
            continue
        if not any(np.linalg.norm((candidate[:3] - other[1][:3]) / 0.02) < 1 for other in distinct):
            distinct.append((cost, candidate))
    if len(distinct) > 1:
        weights = np.exp(-np.array([entry[0] - distinct[0][0] for entry in distinct]))
        weights /= weights.sum()
        predictions = np.array([probabilities(candidate, actions) for _, candidate in distinct])
        average = weights @ predictions
        disagreement = weights @ (predictions - average) ** 2
        reduction += 3 * np.log1p(next_shots * disagreement / (average * (1 - average)))
    return actions[int(np.argmax(reduction))]


def main():
    history = []
    policy_path = root / "policy.json"
    policy = json.loads(policy_path.read_text()) if policy_path.exists() else {}
    design = fixed_design(policy.get("initial_shots", 128))[:36]
    if policy.get("drop_duplicate_zero", False):
        design = [action for action in design if not (action["time"] == 0 and action["mode"] in ("q1-", "q2-"))]
    candidates = None
    for line in sys.stdin:
        message = json.loads(line)
        if message["type"] == "observation":
            history.append(message)
        if len(history) < len(design):
            output = design[len(history)]
        elif len(history) < 48:
            if candidates is None or (len(history) - len(design)) % 4 == 0:
                candidates = fit(history, initial=None if candidates is None else candidates[0][1],
                                 multistart=candidates is None, return_candidates=True)
            used_shots = sum(sum(entry["counts"]) for entry in history)
            next_shots = (6144 - used_shots) // (48 - len(history))
            output = next_action(history, candidates, next_shots)
        else:
            estimate = fit(history, initial=candidates[0][1], multistart=True)
            output = {"type": "estimate", "parameters": parameter_dict(estimate)}
        print(json.dumps(output, allow_nan=False), flush=True)
        if output["type"] == "estimate":
            return


if __name__ == "__main__":
    main()
