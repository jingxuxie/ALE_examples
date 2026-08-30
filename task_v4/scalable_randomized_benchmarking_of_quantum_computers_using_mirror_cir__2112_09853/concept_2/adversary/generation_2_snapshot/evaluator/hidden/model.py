import itertools
import math

import numpy as np


FAMILIES = ("local_clusters", "distant_pairs", "anticorrelated", "spam_drift")
SHAPES = ((4, 4), (4, 5), (5, 5))
LIMITS = {
    "shots_budget": 12000,
    "max_experiments": 768,
    "min_shots": 32,
    "max_shots": 4096,
    "max_depth": 256,
    "target_count": 96,
}


class ProtocolError(ValueError):
    pass


class Grid:
    def __init__(self, shape):
        self.rows, self.columns = shape
        self.qubits = self.rows * self.columns
        self.coordinates = [(vertex // self.columns, vertex % self.columns)
                            for vertex in range(self.qubits)]
        edges = []
        for vertex, (row, column) in enumerate(self.coordinates):
            if column + 1 < self.columns:
                edges.append((vertex, vertex + 1))
            if row + 1 < self.rows:
                edges.append((vertex, vertex + self.columns))
        self.edges = sorted(edges)
        self.edge_lookup = {edge: index for index, edge in enumerate(self.edges)}
        self.pairs = [(first, second) for first, second in
                      itertools.combinations(range(len(self.edges)), 2)
                      if not set(self.edges[first]).intersection(self.edges[second])]
        self.centers = np.array([
            np.mean([self.coordinates[vertex] for vertex in edge], axis=0)
            for edge in self.edges
        ])
        self.distances = np.array([
            min(sum(abs(first_coord - second_coord) for first_coord, second_coord
                    in zip(self.coordinates[first_vertex], self.coordinates[second_vertex]))
                for first_vertex in self.edges[first] for second_vertex in self.edges[second])
            for first, second in self.pairs
        ])

    def matching(self, generator, size, forced=()):
        occupied = {vertex for edge in forced for vertex in self.edges[edge]}
        if len(occupied) != 2 * len(forced) or len(forced) > size:
            return None
        neighbors = {}
        for first_vertex, second_vertex in self.edges:
            if first_vertex in occupied or second_vertex in occupied:
                continue
            if sum(self.coordinates[first_vertex]) % 2:
                first_vertex, second_vertex = second_vertex, first_vertex
            neighbors.setdefault(first_vertex, []).append(second_vertex)
        for choices in neighbors.values():
            generator.shuffle(choices)
        partners = {}

        def augment(vertex, seen):
            for neighbor in neighbors.get(vertex, []):
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                if neighbor not in partners or augment(partners[neighbor], seen):
                    partners[neighbor] = vertex
                    return True
            return False

        for vertex in generator.permutation(list(neighbors)):
            augment(int(vertex), set())
        available = [self.edge_lookup[tuple(sorted((first_vertex, second_vertex)))]
                     for second_vertex, first_vertex in partners.items()]
        needed = size - len(forced)
        if len(available) < needed:
            return None
        chosen = generator.choice(available, size=needed, replace=False).tolist()
        return sorted([int(edge) for edge in forced] + chosen)

    def validate_matching(self, matching, maximum):
        if not isinstance(matching, list) or len(matching) > maximum:
            raise ProtocolError("matching_size")
        if any(type(edge) is not int or not 0 <= edge < len(self.edges) for edge in matching):
            raise ProtocolError("matching_edge_id")
        if matching != sorted(set(matching)):
            raise ProtocolError("matching_must_be_sorted_unique")
        occupied = [vertex for edge in matching for vertex in self.edges[edge]]
        if len(occupied) != len(set(occupied)):
            raise ProtocolError("matching_edges_overlap")
        return matching


def depolarizing_probabilities(qubits, contrast, rate, depth):
    polarization = contrast * math.exp(-depth * rate)
    uniform = math.ldexp(1.0, -qubits)
    other_probability = (1.0 - polarization) * uniform
    success_probability = polarization + other_probability
    return success_probability, other_probability


class Episode:
    def __init__(self, seed, family, shape):
        if family not in FAMILIES or tuple(shape) not in SHAPES:
            raise ValueError("unknown_family_or_shape")
        parameter_seed, target_seed, shot_seed = np.random.SeedSequence(seed).spawn(3)
        generator = np.random.default_rng(parameter_seed)
        self.shot_generator = np.random.default_rng(shot_seed)
        self.family = family
        self.grid = Grid(shape)
        edge_count = len(self.grid.edges)
        self.idle = float(generator.uniform(0.001, 0.004))
        if family in ("anticorrelated", "spam_drift"):
            self.base = np.exp(generator.uniform(math.log(0.0015), math.log(0.010), edge_count))
        else:
            self.base = generator.uniform(0.002, 0.007, edge_count)
        pair_indices = np.array(self.grid.pairs, dtype=int)
        distances = self.grid.distances
        weights = np.ones(len(pair_indices), dtype=float)
        if family == "local_clusters":
            anchors = generator.choice(edge_count, size=2, replace=False)
            weights.fill(0.002)
            for anchor in anchors:
                separation = np.abs(self.grid.centers - self.grid.centers[anchor]).sum(axis=1)
                weights += np.exp(-(separation[pair_indices[:, 0]] +
                                    separation[pair_indices[:, 1]]) / 2.0)
            weights *= np.exp(-(distances - 1) / 2.0)
        elif family == "distant_pairs":
            weights = (distances >= 3).astype(float)
        elif family == "anticorrelated":
            weights = (0.022 - self.base[pair_indices].sum(axis=1)) ** 2
        elif family == "spam_drift":
            local_weights = np.exp(-(distances - 1) / 1.3) + 0.05
            weights = 0.5 / len(pair_indices) + 0.5 * local_weights / local_weights.sum()
        support_size = int(round(0.30 * edge_count)) + int(generator.integers(-1, 3))
        support = generator.choice(len(pair_indices), size=support_size, replace=False,
                                   p=weights / weights.sum())
        self.crosstalk = np.zeros(len(pair_indices), dtype=float)
        if family == "anticorrelated":
            inverse_base = 1.0 - self.base[pair_indices[support]].sum(axis=1) / 0.020
            values = generator.uniform(0.010, 0.025, support_size) + 0.010 * inverse_base
        else:
            values = generator.uniform(0.010, 0.035, support_size)
        self.crosstalk[support] = values
        self.spam_intercept = float(generator.uniform(-0.4, 0.4))
        self.spam_edges = generator.uniform(-0.9, 0.9, edge_count)
        self.spam_density = float(generator.uniform(-1.0, 1.0))
        self.drift_amplitude = 0.0
        self.drift_frequency = 1.0
        self.drift_phase = 0.0
        self.drift_slope = 0.0
        if family == "spam_drift":
            self.drift_amplitude = float(generator.uniform(0.4, 0.9))
            self.drift_frequency = float(generator.uniform(0.5, 1.5))
            self.drift_phase = float(generator.uniform(0, 2 * math.pi))
            self.drift_slope = float(generator.uniform(-0.8, 0.8))
        self.targets = self.make_targets(np.random.default_rng(target_seed))
        self.shots_used = 0
        self.experiments = 0
        self.phase = "acquisition"
        self.predictions = None

    def make_targets(self, generator):
        targets = []
        occupied = set()
        nearby = [pair for pair, distance in zip(self.grid.pairs, self.grid.distances) if distance <= 2]
        distant = [pair for pair, distance in zip(self.grid.pairs, self.grid.distances) if distance >= 3]
        for target_index in range(LIMITS["target_count"]):
            for retry in range(10000):
                target_kind = target_index % 3
                choices = nearby if target_kind == 1 else distant
                forced = () if target_kind == 0 else choices[int(generator.integers(len(choices)))]
                candidate = self.grid.matching(generator, self.grid.qubits // 2 - 1, forced)
                if candidate is not None and tuple(candidate) not in occupied:
                    targets.append(candidate)
                    occupied.add(tuple(candidate))
                    break
            else:
                raise RuntimeError("target_generation_exhausted")
        return targets

    def log_rate(self, matching):
        active = set(matching)
        return float(self.idle + self.base[matching].sum() + sum(
            coefficient for (first, second), coefficient in zip(self.grid.pairs, self.crosstalk)
            if first in active and second in active
        ))

    def error_rate(self, matching):
        return (1.0 - math.ldexp(1.0, -2 * self.grid.qubits)) * (-math.expm1(-self.log_rate(matching)))

    def contrast(self, matching, context):
        density = len(matching) / (self.grid.qubits // 2)
        latent = self.spam_intercept + self.spam_edges[matching].sum() / math.sqrt(max(1, len(matching)))
        latent += self.spam_density * density
        latent += self.drift_amplitude * math.sin(2 * math.pi * self.drift_frequency * context + self.drift_phase)
        latent += self.drift_slope * (context - 0.5)
        return 0.58 + 0.37 / (1.0 + math.exp(-float(latent)))

    def hello(self):
        return {
            "type": "hello", "version": "mrb-active-v2",
            "qubits": self.grid.qubits, "shape": [self.grid.rows, self.grid.columns], "family": self.family,
            "edges": [list(edge) for edge in self.grid.edges],
            "limits": dict(LIMITS), "max_matching_size": self.grid.qubits // 2 - 2,
            "target_matching_size": self.grid.qubits // 2 - 1,
            "target_reveal": "after_ready", "families": list(FAMILIES),
        }

    def handle(self, message):
        if not isinstance(message, dict) or type(message.get("type")) is not str:
            raise ProtocolError("message_must_be_object_with_type")
        if message["type"] == "experiment":
            if self.phase != "acquisition":
                raise ProtocolError("experiments_closed")
            if set(message) != {"type", "matching", "depth", "shots"}:
                raise ProtocolError("experiment_keys")
            matching = self.grid.validate_matching(message["matching"], self.grid.qubits // 2 - 2)
            depth, shots = message["depth"], message["shots"]
            if type(depth) is not int or not 0 <= depth <= LIMITS["max_depth"] or depth % 2:
                raise ProtocolError("depth_must_be_even_integer")
            if type(shots) is not int or not LIMITS["min_shots"] <= shots <= LIMITS["max_shots"]:
                raise ProtocolError("shots_out_of_range")
            if self.experiments >= LIMITS["max_experiments"]:
                raise ProtocolError("experiment_budget_exceeded")
            if self.shots_used + shots > LIMITS["shots_budget"]:
                raise ProtocolError("shot_budget_exceeded")
            context = (self.shots_used + 0.5 * shots) / LIMITS["shots_budget"]
            success_probability, other_probability = depolarizing_probabilities(
                self.grid.qubits, self.contrast(matching, context), self.log_rate(matching), depth)
            successes = int(self.shot_generator.binomial(shots, success_probability))
            self.shots_used += shots
            self.experiments += 1
            return {"type": "observation", "matching": matching, "depth": depth,
                    "shots": shots, "successes": successes, "failures": shots - successes,
                    "experiment": self.experiments, "context": context,
                    "shots_used": self.shots_used, "shots_remaining": LIMITS["shots_budget"] - self.shots_used}
        if message["type"] == "ready":
            if set(message) != {"type"} or self.phase != "acquisition":
                raise ProtocolError("ready_out_of_order_or_keys")
            self.phase = "prediction"
            return {"type": "targets", "matchings": self.targets,
                    "quantity": "layer_entanglement_infidelity", "shots_used": self.shots_used}
        if message["type"] == "final":
            if set(message) != {"type", "predictions"} or self.phase != "prediction":
                raise ProtocolError("final_out_of_order_or_keys")
            predictions = message["predictions"]
            if not isinstance(predictions, list) or len(predictions) != len(self.targets):
                raise ProtocolError("prediction_count")
            upper_bound = 1.0 - math.ldexp(1.0, -2 * self.grid.qubits)
            if any(type(value) not in (int, float) or not math.isfinite(value) or
                   not 0.0 <= value <= upper_bound for value in predictions):
                raise ProtocolError("predictions_must_be_finite_physical_rates")
            self.predictions = [float(value) for value in predictions]
            self.phase = "finished"
            return {"type": "done"}
        raise ProtocolError("unknown_message_type")

    def metrics(self):
        if self.predictions is None:
            raise ProtocolError("missing_final")
        truths = np.array([self.error_rate(matching) for matching in self.targets])
        residuals = np.asarray(self.predictions) - truths
        squared = (residuals / (0.003 + 0.10 * truths)) ** 2
        return {"normalized_mse": float(squared.mean()),
                "normalized_rmse": float(math.sqrt(squared.mean())),
                "absolute_rmse": float(math.sqrt(np.mean(residuals ** 2))),
                "mean_true_rate": float(truths.mean()),
                "score": float(1.0 / (1.0 + squared.mean()))}
