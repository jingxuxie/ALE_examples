import os
import sys

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize

sys.path.insert(0, "/stress_public")
from local_model import LocalModel


def information(model, point):
    channel_count = len(point)
    result = np.zeros((len(model.spec["actions"]), channel_count, channel_count))
    for block in model.blocks:
        indices = block[0]
        probability, derivative = model.block_distribution(point, block, gradient=True)
        contribution = np.einsum("ais,ajs,as->aij", derivative, derivative, 1.0 / probability)
        result[:, indices[:, None], indices[None, :]] += contribution
    return result


def design(model, point, used, remaining, policy):
    matrices = information(model, point)
    families = np.array([channel["family"] for channel in model.spec["channels"]])
    groups = np.array([families == family for family in sorted(set(families))], dtype=float)
    groups /= groups.sum(axis=1, keepdims=True)
    base = np.einsum("a,aij->ij", used, matrices) + np.eye(len(point)) * 0.03

    def objective(weights):
        precision = base + remaining * np.einsum("a,aij->ij", weights, matrices)
        inverse = cho_solve(cho_factor(precision, lower=True), np.eye(len(point)))
        variance = groups @ np.diag(inverse)
        scale = np.maximum(variance, 1e-20) ** 0.5
        coefficient = (1.0 / (2.0 * scale)) @ groups
        objective_value = scale.sum()
        if policy == "robust":
            largest = int(np.argmax(scale))
            objective_value += scale[largest]
            coefficient += groups[largest] / (2.0 * scale[largest])
        sensitivity = (inverse * coefficient[None, :]) @ inverse
        gradient = -remaining * np.einsum("ij,aji->a", sensitivity, matrices)
        return objective_value, gradient

    action_count = len(matrices)
    start = np.full(action_count, 1.0 / action_count)
    result = minimize(objective, start, jac=True, method="SLSQP", bounds=[(0.0, 1.0)] * action_count,
                      constraints={"type": "eq", "fun": lambda weights: weights.sum() - 1.0,
                                   "jac": lambda weights: np.ones(action_count)},
                      options={"maxiter": 90, "ftol": 1e-10})
    weights = np.maximum(result.x, 0.0)
    return weights / weights.sum()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", choices=("adaptive", "robust", "static", "uniform"), default="adaptive")
    arguments = parser.parse_args()
    spec = json.loads(sys.stdin.readline())["spec"]
    model = LocalModel(spec)
    used = np.zeros(len(spec["actions"]), dtype=int)
    queries = 0

    def query(action, shots):
        nonlocal queries
        print(json.dumps({"type": "query", "action": int(action), "shots": int(shots)}), flush=True)
        observation = json.loads(sys.stdin.readline())
        model.observe(action, observation["syndromes"], observation["multiplicities"])
        used[action] += shots
        queries += 1

    def allocate(weights, total, maximum_actions=None):
        order = np.argsort(weights)[::-1]
        available = spec["max_queries"] - queries
        support = max(1, available - int(np.ceil(total / spec["max_shots_per_query"])))
        if maximum_actions is not None:
            support = min(support, maximum_actions)
        selected = order[:support]
        weights = weights.copy()
        weights[np.setdiff1d(np.arange(len(weights)), selected)] = 0.0
        allocation = np.floor(total * weights / weights.sum()).astype(int)
        allocation[np.argmax(weights)] += total - allocation.sum()
        for action in np.argsort(allocation)[::-1]:
            count = int(allocation[action])
            while count:
                shots = min(count, spec["max_shots_per_query"])
                query(action, shots)
                count -= shots

    point = model.bounds.mean(axis=1)
    if arguments.policy == "uniform":
        remaining = spec["shot_budget"]
        for action in range(len(used)):
            count = remaining // (len(used) - action)
            while count:
                shots = min(count, spec["max_shots_per_query"])
                query(action, shots)
                count -= shots
                remaining -= shots
    elif arguments.policy == "static":
        weights = design(model, point, used, spec["shot_budget"], "adaptive")
        allocate(weights, spec["shot_budget"])
    else:
        pilot_actions = list(range(13))
        pilot_actions += [action for action in range(13, len(used)) if (action - 13) % 4 in (1, 3)]
        for action in pilot_actions:
            query(action, 80)
        point = model.fit(iterations=120)
        weights = design(model, point, used, spec["shot_budget"] - used.sum(), arguments.policy)
        allocate(weights, 6500, maximum_actions=8)
        point = model.fit(point, iterations=120)
        weights = design(model, point, used, spec["shot_budget"] - used.sum(), arguments.policy)
        allocate(weights, int(spec["shot_budget"] - used.sum()))
    point = model.fit(point, iterations=180)
    print(json.dumps({"type": "final", "rates": np.exp(point).tolist()}), flush=True)


if __name__ == "__main__":
    main()
