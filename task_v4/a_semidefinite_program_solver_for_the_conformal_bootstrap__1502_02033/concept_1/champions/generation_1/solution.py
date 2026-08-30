import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import json
import sys
import time

import numpy as np
from scipy.optimize import minimize
from scipy.special import roots_genlaguerre


def log_weight(points, scenario):
    poles = np.asarray(scenario["poles"], dtype=float)
    return -scenario["a"] * points - np.log1p(points[..., None] / poles).sum(axis=-1)


def valid_nodes(nodes):
    return (np.all(np.isfinite(nodes)) and nodes[0] >= 0.0
            and nodes[-1] <= 10000 * len(nodes)
            and np.all(np.diff(nodes) > 128 * np.finfo(float).eps * np.maximum(1.0, nodes[1:])))


def equilibrium(degree, scenarios, mixture):
    effective = sum(amount * scenario["a"] for amount, scenario in zip(mixture, scenarios))
    start = roots_genlaguerre(degree, 1.0)[0] / (2.0 * effective)
    initial = np.log(np.diff(np.r_[0.0, start]))
    triangle = np.triu_indices(degree + 1, 1)

    def objective(log_gaps):
        gaps = np.exp(log_gaps)
        nodes = np.r_[0.0, np.cumsum(gaps)]
        differences = nodes[:, None] - nodes[None, :]
        np.fill_diagonal(differences, 1.0)
        value = -np.log(np.abs(differences[triangle])).sum()
        inverse = 1.0 / differences
        np.fill_diagonal(inverse, 0.0)
        gradient = -inverse.sum(axis=1)
        for amount, scenario in zip(mixture, scenarios):
            poles = np.asarray(scenario["poles"])
            value -= amount * log_weight(nodes, scenario).sum()
            gradient += amount * (scenario["a"] + (1.0 / (nodes[:, None] + poles)).sum(axis=1))
        return float(value), np.cumsum(gradient[:0:-1])[::-1] * gaps

    result = minimize(objective, initial, jac=True, method="L-BFGS-B", bounds=[(-32, 8)] * degree,
                      options={"maxiter": 220, "ftol": 2e-12, "gtol": 2e-6, "maxls": 25})
    return np.r_[0.0, np.cumsum(np.exp(result.x))]


class PeakObjective:
    def __init__(self, degree, scenarios, free_origin=False):
        self.degree = degree
        self.free_origin = free_origin
        self.variable_count = degree + int(free_origin)
        self.count = len(scenarios)
        self.damping = np.array([scenario["a"] for scenario in scenarios])
        self.poles = np.full((self.count, max(len(scenario["poles"]) for scenario in scenarios)), np.inf)
        for index, scenario in enumerate(scenarios):
            self.poles[index, :len(scenario["poles"])] = scenario["poles"]
        self.offset = 1.0 / (self.damping + (1.0 / self.poles).sum(axis=1))
        self.cached_parameters = None
        self.calls = 0

    def weight(self, points):
        return -self.damping[:, None] * points - np.log1p(points[:, :, None] / self.poles[:, None, :]).sum(axis=2)

    def prepare(self, nodes):
        self.nodes = nodes
        difference = nodes[:, None] - nodes[None, :]
        np.fill_diagonal(difference, 1.0)
        denominators = np.log(np.abs(difference)).sum(axis=1)
        inverse = 1.0 / np.abs(difference)
        np.fill_diagonal(inverse, 0.0)
        left_sum = np.cumsum(inverse, axis=1)[:, :-1]
        right_sum = np.cumsum(inverse[:, ::-1], axis=1)[:, ::-1][:, 1:]
        self.crossing = np.where(np.arange(len(nodes))[:, None] >= np.arange(1, len(nodes))[None, :], left_sum, right_sum)
        if self.free_origin:
            self.crossing = np.column_stack((np.zeros(len(nodes)), self.crossing))
        node_weight = self.weight(np.broadcast_to(nodes, (self.count, len(nodes))))
        coefficients = -denominators[None, :] - node_weight
        self.shift = coefficients.max(axis=1)
        self.coefficients = np.exp(coefficients - self.shift[:, None])

    def values(self, points, gradient=False):
        difference = points[:, :, None] - self.nodes[None, None, :]
        distance = np.abs(difference)
        terms = self.coefficients[:, None, :] / distance
        total = terms.sum(axis=2)
        values = self.weight(points) + np.log(distance).sum(axis=2) + self.shift[:, None] + np.log(total)
        if not gradient:
            return values
        probabilities = terms / total[:, :, None]
        potential_derivative = self.damping[:, None] + (1.0 / (self.nodes[None, :, None] + self.poles[:, None, :])).sum(axis=2)
        local_derivative = probabilities * potential_derivative[:, None, :] - (1.0 - probabilities) / difference
        first_variable = 0 if self.free_origin else 1
        derivative = np.cumsum(local_derivative[:, :, first_variable:][:, :, ::-1], axis=2)[:, :, ::-1] - probabilities @ self.crossing
        return values, derivative

    def peaks(self, nodes, iterations=30, gradient=False):
        self.prepare(nodes)
        origin = np.broadcast_to(nodes, (self.count, len(nodes)))
        local_scale = origin + self.offset[:, None]
        width = np.r_[np.diff(nodes), self.degree + 1]
        left = np.zeros_like(origin)
        right = np.log1p(width / local_scale)

        def coordinates(parameters):
            return origin + local_scale * np.expm1(parameters)

        ratio = 0.6180339887498949
        first = right - ratio * (right - left)
        second = left + ratio * (right - left)
        first_value = self.values(coordinates(first))
        second_value = self.values(coordinates(second))
        for iteration in range(iterations):
            choose_right = first_value < second_value
            left = np.where(choose_right, first, left)
            right = np.where(choose_right, right, second)
            old_first = first
            first = np.where(choose_right, second, right - ratio * (right - left))
            second = np.where(choose_right, left + ratio * (right - left), old_first)
            new_points = np.where(choose_right, second, first)
            new_values = self.values(coordinates(new_points))
            old_first_value = first_value
            first_value = np.where(choose_right, second_value, new_values)
            second_value = np.where(choose_right, new_values, old_first_value)
        points = coordinates(np.where(first_value >= second_value, first, second))
        left = coordinates(left)
        right = coordinates(right)
        for iteration in range(3):
            inverse = 1.0 / (points[:, :, None] - nodes[None, None, :])
            terms = self.coefficients[:, None, :] * np.abs(inverse)
            probabilities = terms / terms.sum(axis=2)[:, :, None]
            mean_inverse = (probabilities * inverse).sum(axis=2)
            pole_inverse = 1.0 / (points[:, :, None] + self.poles[:, None, :])
            derivative = inverse.sum(axis=2) - mean_inverse - self.damping[:, None] - pole_inverse.sum(axis=2)
            curvature = -(inverse * inverse).sum(axis=2) + 2 * (probabilities * inverse * inverse).sum(axis=2) - mean_inverse * mean_inverse + (pole_inverse * pole_inverse).sum(axis=2)
            proposed = points - derivative / np.minimum(curvature, -1e-100)
            points = np.where((curvature < 0) & (proposed > left) & (proposed < right), proposed, points)
        if self.free_origin:
            points = np.column_stack((np.zeros(self.count), points))
        if gradient:
            values, derivative = self.values(points, True)
            return np.maximum(values, 0.0), np.where((values > 0.0)[:, :, None], derivative, 0.0)
        return np.maximum(self.values(points), 0.0)

    def evaluate(self, parameters):
        if self.cached_parameters is not None and np.array_equal(parameters, self.cached_parameters):
            return self.cached_values, self.cached_jacobian
        gaps = np.exp(parameters)
        nodes = np.cumsum(gaps) if self.free_origin else np.r_[0.0, np.cumsum(gaps)]
        values, derivative = self.peaks(nodes, iterations=18, gradient=True)
        jacobian = derivative * gaps
        self.cached_parameters = parameters.copy()
        self.cached_values = values.ravel()
        self.cached_jacobian = jacobian.reshape(-1, self.variable_count)
        self.calls += 1
        return self.cached_values, self.cached_jacobian


def solve(data):
    started = time.process_time()
    scale = min(scenario["a"] for scenario in data["scenarios"])
    scenarios = [{"a": scenario["a"] / scale, "poles": [pole * scale for pole in scenario["poles"]]}
                 for scenario in data["scenarios"]]
    degree = data["degree"]
    count = len(scenarios)
    objective = PeakObjective(degree, scenarios)
    mixtures = [np.ones(count) / count]
    for index in sorted({0, count - 1}):
        mixture = np.ones(count) * (0.4 / count)
        mixture[index] += 0.6
        mixtures.append(mixture)
    best_nodes = None
    best_loss = float("inf")
    for mixture in mixtures:
        nodes = equilibrium(degree, scenarios, mixture)
        for factor in (0.93, 1.0, 1.07):
            candidate = nodes * factor
            loss = float(objective.peaks(candidate, iterations=18).max())
            if loss < best_loss and valid_nodes(candidate):
                best_loss, best_nodes = loss, candidate
    calls = 0
    statuses = []

    def refine(peak_objective, initial_nodes, max_iterations):
        nonlocal best_loss, best_nodes, calls
        initial_gaps = np.diff(np.r_[0.0, initial_nodes]) if peak_objective.free_origin else np.diff(initial_nodes)
        initial_loss = float(peak_objective.peaks(initial_nodes, iterations=18).max())
        initial = np.r_[np.log(initial_gaps), initial_loss]

        def constraints(parameters):
            nonlocal best_loss, best_nodes
            values, jacobian = peak_objective.evaluate(parameters[:-1])
            loss = float(values.max())
            tolerance = 1e-10 if peak_objective.free_origin else 0.0
            if loss < best_loss - tolerance and valid_nodes(peak_objective.nodes):
                best_loss = loss
                best_nodes = peak_objective.nodes.copy()
            if time.process_time() - started > 5.8:
                raise TimeoutError
            return parameters[-1] - values

        def constraint_jacobian(parameters):
            values, jacobian = peak_objective.evaluate(parameters[:-1])
            return np.column_stack((-jacobian, np.ones(len(values))))

        direction = np.r_[np.zeros(peak_objective.variable_count), 1.0]
        bounds = ([(-60.0, 8.0)] if peak_objective.free_origin else []) + [(-30.0, 8.0)] * degree + [(0.0, None)]
        try:
            result = minimize(lambda parameters: (parameters[-1], direction), initial, jac=True,
                     method="SLSQP", bounds=bounds,
                     constraints={"type": "ineq", "fun": constraints, "jac": constraint_jacobian},
                     options={"maxiter": max_iterations, "ftol": 2e-8, "disp": False})
            statuses.append(str(result.message))
        except TimeoutError:
            statuses.append("time limit")
        calls += peak_objective.calls

    refine(objective, best_nodes, 140)
    if any(scenario["poles"] for scenario in scenarios) and time.process_time() - started < 4.8:
        shifted = best_nodes + 0.15 * best_nodes[1]
        refine(PeakObjective(degree, scenarios, free_origin=True), shifted, 120)
    if os.environ.get("NODE_DEBUG"):
        print(json.dumps({"cpu": time.process_time() - started, "loss": best_loss, "calls": calls, "status": statuses}), file=sys.stderr)
    return {"nodes": (best_nodes / scale).tolist()}


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as handle:
        problem = json.load(handle)
    result = solve(problem)
    with open(sys.argv[2], "w", encoding="utf-8") as handle:
        json.dump(result, handle, allow_nan=False)
