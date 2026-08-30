import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.optimize import minimize_scalar

import solution


ASSETS = Path(__file__).resolve().parent / "scratch" / "assets"
specification = importlib.util.spec_from_file_location("reference", ASSETS / "baseline" / "solution.py")
reference = importlib.util.module_from_spec(specification)
previous_bytecode_setting = sys.dont_write_bytecode
sys.dont_write_bytecode = True
specification.loader.exec_module(reference)
sys.dont_write_bytecode = previous_bytecode_setting


def accurate_loss(nodes, scenarios):
    nodes = np.asarray(nodes)
    degree = len(nodes) - 1
    difference = np.abs(nodes[:, None] - nodes[None, :])
    np.fill_diagonal(difference, 1.0)
    denominator = np.log(difference).sum(axis=1)
    greatest = 0.0
    peaks = []
    edges = np.r_[nodes, nodes[-1] + (degree + 1) / min(scenario["a"] for scenario in scenarios)]
    for scenario in scenarios:
        coefficients = -denominator - reference.log_weight(nodes, scenario)

        def value(point):
            distance = np.log(np.maximum(np.abs(point - nodes), np.finfo(float).tiny))
            return float(reference.log_weight(np.asarray(point), scenario) + reference.logsumexp(distance.sum() - distance + coefficients))

        if nodes[0] > 0:
            greatest = max(greatest, value(0.0))
        for left, right in zip(edges[:-1], edges[1:]):
            fractions = np.r_[np.geomspace(1e-8, 0.02, 12), np.linspace(0.025, 0.975, 49), 1 - np.geomspace(1e-8, 0.02, 12)[::-1]]
            local_scale = left + 1.0 / (scenario["a"] + sum(1.0 / pole for pole in scenario["poles"]))
            log_width = np.log1p((right - left) / local_scale)
            points = np.unique(np.r_[left + (right - left) * fractions,
                                     left + local_scale * np.expm1(log_width * np.linspace(0.00001, 0.99999, 129))])
            values = np.array([value(point) for point in points])
            local_maximum = float(values.max())
            for index in range(1, len(points) - 1):
                if values[index] >= values[index - 1] and values[index] >= values[index + 1]:
                    result = minimize_scalar(lambda point: -value(point), bounds=(points[index - 1], points[index + 1]), method="bounded", options={"xatol": max(1e-25, (points[index+1]-points[index-1])*1e-12)})
                    local_maximum = max(local_maximum, -result.fun)
            greatest = max(greatest, local_maximum)
            peaks.append(local_maximum)
    return greatest, peaks


def run(data, name):
    started = time.process_time()
    baseline_nodes = reference.solve(data)["nodes"]
    baseline_time = time.process_time() - started
    started = time.process_time()
    nodes = solution.solve(data)["nodes"]
    elapsed = time.process_time() - started
    normalized = np.asarray(nodes) * min(scenario["a"] for scenario in data["scenarios"])
    assert len(nodes) == data["degree"] + 1
    assert np.all(np.isfinite(normalized)) and normalized[0] >= 0
    assert normalized[-1] <= 10000 * (data["degree"] + 1)
    assert np.all(np.diff(normalized) > 64 * 2.0**-52 * np.maximum(1.0, normalized[1:]))
    baseline_loss, unused = accurate_loss(baseline_nodes, data["scenarios"])
    loss, peaks = accurate_loss(nodes, data["scenarios"])
    print(json.dumps({"name": name, "degree": data["degree"], "baseline_log": baseline_loss,
                      "solution_log": loss, "ratio": float(np.exp(min(700, baseline_loss-loss))),
                      "cpu": elapsed, "baseline_cpu": baseline_time}), flush=True)
    return {"name": name, "data": data, "nodes": nodes, "baseline_nodes": baseline_nodes, "log_loss": loss, "baseline_log": baseline_loss, "cpu": elapsed}


if __name__ == "__main__":
    results = []
    for path in sorted((ASSETS / "input").glob("*.json")):
        if path.name != "schema.json":
            results.append(run(json.loads(path.read_text()), path.stem))
    Path("example_results.json").write_text(json.dumps(results, indent=2))
