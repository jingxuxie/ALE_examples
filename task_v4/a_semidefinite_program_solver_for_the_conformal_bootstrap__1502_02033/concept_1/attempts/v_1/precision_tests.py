import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import json
from pathlib import Path

import mpmath as mp
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.optimize._numdiff import approx_derivative
from scipy.special import logsumexp

from solution import PeakObjective, log_weight


def precision_check(record):
    nodes = np.asarray(record["nodes"])
    difference = np.abs(nodes[:, None] - nodes[None, :])
    np.fill_diagonal(difference, 1.0)
    denominator = np.log(difference).sum(axis=1)
    greatest = -np.inf
    selected = None
    for scenario in record["data"]["scenarios"]:
        coefficients = -denominator - log_weight(nodes, scenario)

        def value(point):
            distances = np.log(np.abs(point - nodes))
            return float(log_weight(np.asarray(point), scenario) + logsumexp(distances.sum() - distances + coefficients))

        if nodes[0] > 0 and value(0.0) > greatest:
            greatest = value(0.0)
            selected = scenario, 0.0
        edges = np.r_[nodes, nodes[-1] + len(nodes) / scenario["a"]]
        offset = 1.0 / (scenario["a"] + sum(1.0 / pole for pole in scenario["poles"]))
        for left, right in zip(edges[:-1], edges[1:]):
            local_scale = left + offset
            width = np.log1p((right - left) / local_scale)
            positions = np.linspace(width * 1e-7, width * (1 - 1e-7), 81)
            values = np.array([value(left + local_scale * np.expm1(position)) for position in positions])
            for index in range(1, len(positions) - 1):
                if values[index] >= values[index - 1] and values[index] >= values[index + 1]:
                    result = minimize_scalar(lambda position: -value(left + local_scale * np.expm1(position)), bounds=(positions[index - 1], positions[index + 1]), method="bounded", options={"xatol": 1e-13})
                    if -result.fun > greatest:
                        greatest = -result.fun
                        selected = scenario, left + local_scale * np.expm1(result.x)
    scenario, point = selected
    mp.mp.dps = 90
    high_nodes = [mp.mpf(float(node)) for node in nodes]
    high_point = mp.mpf(float(point))
    damping = mp.mpf(scenario["a"])
    poles = [mp.mpf(pole) for pole in scenario["poles"]]
    total = mp.mpf(0)
    for index, node in enumerate(high_nodes):
        cardinal = mp.mpf(1)
        for other_index, other in enumerate(high_nodes):
            if index != other_index:
                cardinal *= (high_point - other) / (node - other)
        ratio = mp.exp(-damping * (high_point - node))
        for pole in poles:
            ratio *= (node + pole) / (high_point + pole)
        total += abs(cardinal) * ratio
    error = abs(float(mp.log(total)) - greatest)
    assert error < 1e-9
    scale = min(scenario["a"] for scenario in record["data"]["scenarios"])
    scenarios = [{"a": scenario["a"] / scale, "poles": [pole * scale for pole in scenario["poles"]]} for scenario in record["data"]["scenarios"]]
    free_origin = bool(nodes[0] > 0)
    objective = PeakObjective(record["data"]["degree"], scenarios, free_origin=free_origin)
    parameters = np.log(np.diff(np.r_[0.0, nodes * scale]) if free_origin else np.diff(nodes * scale))
    values, analytic = objective.evaluate(parameters)
    numeric = approx_derivative(lambda parameters: objective.evaluate(parameters)[0], parameters, method="3-point", abs_step=1e-5)
    gradient_error = float(np.max(np.abs(analytic - numeric) / np.maximum(1.0, np.abs(numeric))))
    assert gradient_error < 2e-5
    assert abs(float(values.max()) - greatest) < 1e-8
    return {"name": record["name"], "high_precision_log_error": error, "gradient_relative_error": gradient_error}


if __name__ == "__main__":
    records = json.loads(Path("example_results.json").read_text())
    for filename in ("stress_damping_48.json", "stress_pole_count_48.json", "stress_clusters_2.json", "stress_clusters_48.json", "random_6.json", "random_25.json"):
        records.append(json.loads(Path(filename).read_text()))
    results = []
    for record in records:
        result = precision_check(record)
        results.append(result)
        print(json.dumps(result), flush=True)
    Path("precision_results.json").write_text(json.dumps(results, indent=2))
