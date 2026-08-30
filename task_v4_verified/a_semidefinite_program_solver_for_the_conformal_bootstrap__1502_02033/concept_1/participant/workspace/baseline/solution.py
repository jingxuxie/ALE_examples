import json
import sys

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp, roots_genlaguerre


def log_weight(points, scenario):
    poles = np.asarray(scenario["poles"], dtype=float)
    return -scenario["a"] * points - np.log1p(points[..., None] / poles).sum(axis=-1)


def equilibrium(degree, scenarios, mixture):
    start = roots_genlaguerre(degree, 1.0)[0] / 2.0
    effective = sum(amount * scenario["a"] for amount, scenario in zip(mixture, scenarios))
    initial = np.log(np.diff(np.r_[0.0, start / effective]))

    def objective(log_gaps):
        gaps = np.exp(log_gaps)
        nodes = np.r_[0.0, np.cumsum(gaps)]
        differences = nodes[:, None] - nodes[None, :]
        np.fill_diagonal(differences, 1.0)
        value = -np.log(np.abs(differences[np.triu_indices(degree + 1, 1)])).sum()
        inverse = 1.0 / differences
        np.fill_diagonal(inverse, 0.0)
        gradient = -inverse.sum(axis=1)
        for amount, scenario in zip(mixture, scenarios):
            poles = np.asarray(scenario["poles"])
            value -= amount * log_weight(nodes, scenario).sum()
            gradient += amount * (scenario["a"] + (1.0 / (nodes[:, None] + poles)).sum(axis=1))
        return float(value), np.cumsum(gradient[:0:-1])[::-1] * gaps

    result = minimize(objective, initial, jac=True, method="L-BFGS-B", bounds=[(-25, 8)] * degree,
                      options={"maxiter": 220, "ftol": 2e-12, "gtol": 2e-6, "maxls": 25})
    return np.r_[0.0, np.cumsum(np.exp(result.x))]


def sampled_loss(nodes, scenarios):
    degree = len(nodes) - 1
    fractions = (np.arange(1, 20) - 0.5) / 19
    edges = np.r_[nodes, nodes[-1] + 2 * degree + 4]
    points = (edges[:-1, None] + np.diff(edges)[:, None] * fractions).ravel()
    differences = np.abs(nodes[:, None] - nodes[None, :])
    np.fill_diagonal(differences, 1.0)
    denominators = np.log(differences).sum(axis=1)
    distances = np.log(np.abs(points[:, None] - nodes))
    cardinal = distances.sum(axis=1)[:, None] - distances - denominators
    worst = 0.0
    for scenario in scenarios:
        values = log_weight(points, scenario) + logsumexp(cardinal - log_weight(nodes, scenario), axis=1)
        worst = max(worst, float(values.max()))
    return worst


def solve(data):
    scale = min(scenario["a"] for scenario in data["scenarios"])
    scenarios = [{"a": scenario["a"] / scale,
                  "poles": [pole * scale for pole in scenario["poles"]]}
                 for scenario in data["scenarios"]]
    count = len(scenarios)
    mixtures = [np.ones(count) / count]
    for index in {0, count - 1}:
        mixture = np.ones(count) * (0.4 / count)
        mixture[index] += 0.6
        mixtures.append(mixture)
    best_nodes = None
    best_loss = float("inf")
    for mixture in mixtures:
        nodes = equilibrium(data["degree"], scenarios, mixture)
        for factor in (0.93, 1.0, 1.07):
            candidate = nodes * factor
            loss = sampled_loss(candidate, scenarios)
            if loss < best_loss:
                best_loss, best_nodes = loss, candidate
    return {"nodes": (best_nodes / scale).tolist()}


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as handle:
        problem = json.load(handle)
    with open(sys.argv[2], "w", encoding="utf-8") as handle:
        json.dump(solve(problem), handle, allow_nan=False)
