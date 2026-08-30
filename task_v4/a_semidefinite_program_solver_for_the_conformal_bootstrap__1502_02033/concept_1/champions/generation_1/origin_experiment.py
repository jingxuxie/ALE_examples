import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import json
from pathlib import Path
import time

import numpy as np
from scipy.optimize import minimize

from benchmark import accurate_loss
from solution import PeakObjective, valid_nodes


class OriginObjective(PeakObjective):
    def prepare(self, nodes):
        super().prepare(nodes)
        self.crossing = np.column_stack((np.zeros(len(nodes)), self.crossing))

    def values(self, points, gradient=False):
        if not gradient:
            return super().values(points, False)
        difference = points[:, :, None] - self.nodes[None, None, :]
        distance = np.abs(difference)
        terms = self.coefficients[:, None, :] / distance
        total = terms.sum(axis=2)
        values = self.weight(points) + np.log(distance).sum(axis=2) + self.shift[:, None] + np.log(total)
        probabilities = terms / total[:, :, None]
        potential_derivative = self.damping[:, None] + (1.0 / (self.nodes[None, :, None] + self.poles[:, None, :])).sum(axis=2)
        local_derivative = probabilities * potential_derivative[:, None, :] - (1.0 - probabilities) / difference
        derivative = np.cumsum(local_derivative[:, :, ::-1], axis=2)[:, :, ::-1] - probabilities @ self.crossing
        return values, derivative

    def peaks(self, nodes, iterations=18, gradient=False):
        result = super().peaks(nodes, iterations, gradient)
        origin = self.values(np.zeros((self.count, 1)), gradient)
        if gradient:
            return np.concatenate((origin[0], result[0]), axis=1), np.concatenate((origin[1], result[1]), axis=1)
        return np.concatenate((origin, result), axis=1)

    def evaluate(self, parameters):
        if self.cached_parameters is not None and np.array_equal(parameters, self.cached_parameters):
            return self.cached_values, self.cached_jacobian
        gaps = np.exp(parameters)
        nodes = np.cumsum(gaps)
        values, derivative = self.peaks(nodes, gradient=True)
        self.cached_parameters = parameters.copy()
        self.cached_values = values.ravel()
        self.cached_jacobian = (derivative * gaps).reshape(-1, self.degree + 1)
        return self.cached_values, self.cached_jacobian


def refine(record):
    data = record["data"]
    scale = min(scenario["a"] for scenario in data["scenarios"])
    scenarios = [{"a": scenario["a"] / scale, "poles": [pole * scale for pole in scenario["poles"]]} for scenario in data["scenarios"]]
    nodes = np.array(record["nodes"]) * scale
    best_nodes = nodes.copy()
    best_loss = float(PeakObjective(data["degree"], scenarios, free_origin=bool(nodes[0] > 0)).peaks(nodes).max())
    original_loss = best_loss
    objective = OriginObjective(data["degree"], scenarios)
    shifted = nodes + 0.15 * (nodes[1] - nodes[0])
    parameters = np.log(np.diff(np.r_[0.0, shifted]))
    values, unused = objective.evaluate(parameters)
    initial = np.r_[parameters, values.max()]
    started = time.process_time()

    def constraints(parameters):
        nonlocal best_loss, best_nodes
        values, unused = objective.evaluate(parameters[:-1])
        loss = float(values.max())
        if loss < best_loss and valid_nodes(objective.nodes):
            best_loss = loss
            best_nodes = objective.nodes.copy()
        if time.process_time() - started > 3.0:
            raise TimeoutError
        return parameters[-1] - values

    def jacobian(parameters):
        values, derivative = objective.evaluate(parameters[:-1])
        return np.column_stack((-derivative, np.ones(len(values))))

    direction = np.r_[np.zeros(len(nodes)), 1.0]
    try:
        result = minimize(lambda parameters: (parameters[-1], direction), initial, jac=True,
                          method="SLSQP", bounds=[(-60, 8)] * len(nodes) + [(0, None)],
                          constraints={"type": "ineq", "fun": constraints, "jac": jacobian},
                          options={"maxiter": 150, "ftol": 2e-8})
        status = str(result.message)
    except TimeoutError:
        status = "time limit"
    elapsed = time.process_time() - started
    actual_loss, unused = accurate_loss(best_nodes / scale, data["scenarios"])
    return {"name": record["name"], "before": original_loss, "after": actual_loss,
            "improvement": original_loss - actual_loss, "origin": float(best_nodes[0]), "cpu": elapsed, "status": status}


if __name__ == "__main__":
    records = json.loads(Path("example_results.json").read_text())
    for filename in ("stress_pole_count_2.json", "stress_pole_count_12.json", "stress_pole_count_48.json", "stress_clusters_2.json", "stress_clusters_48.json", "stress_damping_48.json", "random_31.json"):
        records.append(json.loads(Path(filename).read_text()))
    results = []
    for record in records:
        result = refine(record)
        results.append(result)
        print(json.dumps(result), flush=True)
    Path("origin_results.json").write_text(json.dumps(results, indent=2))
