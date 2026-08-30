import heapq
import json
import math
import time

import mpmath as mp
import numpy as np
from scipy.special import logsumexp


RELATIVE_TOLERANCE = 8e-5
ROUNDING_GUARD = 2e-10


class InvalidResult(ValueError):
    pass


def strict_json(text):
    def constant(value):
        raise InvalidResult("nonfinite JSON constant: " + value)

    def pairs(items):
        result = {}
        for name, value in items:
            if name in result:
                raise InvalidResult("duplicate JSON key")
            result[name] = value
        return result

    try:
        return json.loads(text, parse_constant=constant, object_pairs_hook=pairs)
    except (ValueError, RecursionError) as error:
        raise InvalidResult(str(error)) from error


def validate_nodes(case, output):
    if not isinstance(output, dict) or set(output) != {"nodes"}:
        raise InvalidResult("output must contain only nodes")
    raw = output["nodes"]
    if not isinstance(raw, list) or len(raw) != case["degree"] + 1:
        raise InvalidResult("incorrect node count")
    if any(type(value) not in (int, float) for value in raw):
        raise InvalidResult("nodes must be JSON numbers, not booleans or strings")
    try:
        nodes = np.asarray(raw, dtype=float)
    except (OverflowError, ValueError) as error:
        raise InvalidResult("unrepresentable nodes") from error
    if not np.isfinite(nodes).all() or nodes[0] < 0 or np.any(np.diff(nodes) <= 0):
        raise InvalidResult("nodes must be finite, nonnegative, and strictly increasing")
    scale = min(scenario["a"] for scenario in case["scenarios"])
    nodes = nodes * scale
    if not np.isfinite(nodes).all() or nodes[-1] > 1e4 * len(nodes):
        raise InvalidResult("dimensionless node range exceeds interface limit")
    separation = 64 * np.finfo(float).eps * np.maximum(1.0, nodes[1:])
    if np.any(np.diff(nodes) <= separation):
        raise InvalidResult("numerically coincident nodes")
    return nodes, scale


class LebesgueOracle:
    def __init__(self, case, output):
        self.nodes, self.scale = validate_nodes(case, output)
        self.degree = case["degree"]
        self.rates = np.array([scenario["a"] / self.scale for scenario in case["scenarios"]])
        self.poles = [np.asarray(scenario["poles"], dtype=float) * self.scale for scenario in case["scenarios"]]
        differences = np.abs(self.nodes[:, None] - self.nodes)
        np.fill_diagonal(differences, 1.0)
        self.denominators = np.log(differences).sum(axis=1)
        self.coefficients = -self.weights(self.nodes) - self.denominators

    def weights(self, points):
        points = np.atleast_1d(points)
        return np.asarray([-rate * points - np.log1p(points[:, None] / poles).sum(axis=1)
                           for rate, poles in zip(self.rates, self.poles)])

    def values(self, points):
        points = np.atleast_1d(points)
        distances = np.abs(points[:, None] - self.nodes)
        exact = np.any(distances == 0, axis=1)
        safe = distances.copy()
        safe[exact] = 1.0
        logs = np.log(safe)
        products = logs.sum(axis=1)[:, None] - logs
        result = self.weights(points) + logsumexp(products[None, :, :] + self.coefficients[:, None, :], axis=2)
        result[:, exact] = 0.0
        return result

    def upper_bound(self, left, right, left_values, right_values):
        distances = np.maximum(np.abs(left - self.nodes), np.abs(right - self.nodes))
        logs = np.log(distances)
        inverse = 1.0 / distances
        sums = inverse.sum() - inverse
        squares = np.maximum(0.0, (inverse * inverse).sum() - inverse * inverse)
        products = logs.sum() - logs
        bounds = []
        for index, (rate, poles) in enumerate(zip(self.rates, self.poles)):
            pole_inverse = 1.0 / (left + poles)
            potential_first = rate + pole_inverse.sum()
            potential_second = (pole_inverse * pole_inverse).sum()
            curvature = np.maximum((potential_first + sums) ** 2 + potential_second - squares, np.finfo(float).tiny)
            weight_left = -rate * left - np.log1p(left / poles).sum()
            log_second = weight_left + logsumexp(products + self.coefficients[index] + np.log(curvature))
            bound = np.logaddexp(max(left_values[index], right_values[index]),
                                 log_second + 2 * math.log(right - left) - math.log(8.0))
            bounds.append(float(bound + ROUNDING_GUARD))
        return max(bounds)

    def mp_value(self, point, scenario_index):
        with mp.workdps(80):
            position = mp.mpf(float(point))
            nodes = [mp.mpf(float(node)) for node in self.nodes]
            if position in nodes:
                return 0.0
            rate = mp.mpf(float(self.rates[scenario_index]))
            poles = [mp.mpf(float(pole)) for pole in self.poles[scenario_index]]
            terms = []
            for index, node in enumerate(nodes):
                term = mp.exp(-rate * (position - node))
                for pole in poles:
                    term *= (node + pole) / (position + pole)
                for other_index, other_node in enumerate(nodes):
                    if index != other_index:
                        term *= abs((position - other_node) / (node - other_node))
                terms.append(term)
            return float(mp.log(mp.fsum(terms)))

    def supremum(self, tolerance=RELATIVE_TOLERANCE, cpu_limit=8.0, max_splits=50000):
        started = time.process_time()
        tail = self.nodes[-1] + 2 * self.degree + 4.0
        boundaries = np.unique(np.r_[0.0, self.nodes, tail])
        refined = []
        for left, right in zip(boundaries[:-1], boundaries[1:]):
            refined.extend(np.linspace(left, right, 5)[:-1])
        boundaries = np.r_[refined, tail]
        values = self.values(boundaries)
        flat_index = int(values.argmax())
        scenario_index, point_index = np.unravel_index(flat_index, values.shape)
        best = float(values[scenario_index, point_index])
        witness = float(boundaries[point_index])
        scenario_best = values.max(axis=1)
        heap = []
        serial = 0
        for index in range(len(boundaries) - 1):
            left, right = boundaries[index:index + 2]
            upper = self.upper_bound(left, right, values[:, index], values[:, index + 1])
            heapq.heappush(heap, (-upper, serial, left, right, values[:, index], values[:, index + 1]))
            serial += 1
        splits = 0
        threshold = math.log1p(tolerance)
        while heap and -heap[0][0] > best + threshold:
            if splits >= max_splits or (splits % 128 == 0 and time.process_time() - started > cpu_limit):
                raise InvalidResult("supremum enclosure unresolved within evaluator budget")
            if not math.isfinite(best) or best > 650:
                raise InvalidResult("catastrophic weighted amplification")
            negative_upper, _, left, right, left_values, right_values = heapq.heappop(heap)
            middle = (left + right) / 2
            if middle == left or middle == right:
                raise InvalidResult("supremum interval exhausted floating-point resolution")
            middle_values = self.values([middle])[:, 0]
            scenario_best = np.maximum(scenario_best, middle_values)
            winner = int(middle_values.argmax())
            if middle_values[winner] > best:
                best, witness, scenario_index = float(middle_values[winner]), middle, winner
            for lower, upper, lower_values, upper_values in (
                    (left, middle, left_values, middle_values), (middle, right, middle_values, right_values)):
                bound = self.upper_bound(lower, upper, lower_values, upper_values)
                if bound > best:
                    heapq.heappush(heap, (-bound, serial, lower, upper, lower_values, upper_values))
                    serial += 1
            splits += 1
        upper = max(best, -heap[0][0] if heap else best) + ROUNDING_GUARD
        precise = self.mp_value(witness, scenario_index)
        if abs(precise - best) > 2e-8 * max(1.0, abs(best)):
            raise InvalidResult("independent high-precision peak check disagrees")
        lower = max(0.0, precise - ROUNDING_GUARD)
        if not math.isfinite(upper) or upper - lower > threshold + 1e-7:
            raise InvalidResult("nonfinite or inconsistent supremum enclosure")
        return {"log_lower": lower, "log_upper": upper,
                "lebesgue_lower": math.exp(lower), "lebesgue_upper": math.exp(upper),
                "peak_x": witness / self.scale, "peak_scenario": int(scenario_index),
                "scenario_log_witnesses": scenario_best.tolist(),
                "tail_start": tail / self.scale, "tail_log_derivative_bound": -0.5 * self.scale,
                "relative_enclosure": math.expm1(upper - lower), "splits": splits,
                "oracle_cpu_seconds": time.process_time() - started}
