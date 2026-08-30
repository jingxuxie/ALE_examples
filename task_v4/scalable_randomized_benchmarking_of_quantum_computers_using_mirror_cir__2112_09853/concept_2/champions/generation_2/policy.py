import ctypes
import itertools
import json
import math
import os
from pathlib import Path
import sys
import time

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np


FAMILIES = ("local_clusters", "distant_pairs", "anticorrelated", "spam_drift")


class Policy:
    def __init__(self, hello, exchange):
        self.hello = hello
        self.exchange = exchange
        self.generator = np.random.default_rng(435981)
        self.edges = hello["edges"]
        self.edge_count = len(self.edges)
        self.qubits = hello["qubits"]
        self.maximum = hello["max_matching_size"]
        self.family = FAMILIES.index(hello["family"])
        columns = hello["shape"][1]
        self.coordinates = np.array([(vertex // columns, vertex % columns) for vertex in range(self.qubits)])
        self.pairs = np.array([pair for pair in itertools.combinations(range(self.edge_count), 2)
                              if not set(self.edges[pair[0]]).intersection(self.edges[pair[1]])], dtype=int)
        self.distances = np.array([min(np.abs(self.coordinates[first] - self.coordinates[second]).sum()
                                      for first in self.edges[pair[0]] for second in self.edges[pair[1]]) for pair in self.pairs])
        self.nearby_pairs = self.pairs[self.distances <= 2]
        self.distant_pairs = self.pairs[self.distances >= 3]
        if self.family == 1:
            self.pairs = self.pairs[self.distances >= 3]
            self.distances = self.distances[self.distances >= 3]
        self.rate_count = 1 + self.edge_count + len(self.pairs)
        self.spam_count = self.edge_count + 2 + (5 if self.family == 3 else 0)
        self.parameter_count = self.rate_count + self.spam_count
        weights = np.ones(len(self.pairs))
        if self.family == 0:
            centers = self.coordinates[np.array(self.edges)].mean(axis=1)
            separation = np.abs(centers[:, None] - centers[None]).sum(axis=2)
            anchor = np.exp(-separation / 2)
            weights = (0.002 + 2 * (anchor[self.pairs[:, 0]] * anchor[self.pairs[:, 1]]).mean(axis=1)) * np.exp(-(self.distances - 1) / 2)
        if self.family == 3:
            local = np.exp(-(self.distances - 1) / 1.3) + 0.05
            weights = 0.5 / len(weights) + 0.5 * local / local.sum()
        self.prior = np.ascontiguousarray((round(0.30 * self.edge_count) + 0.5) * weights / weights.sum())
        self.state = np.zeros(self.parameter_count)
        self.state[0] = 0.0025
        self.state[1:self.edge_count + 1] = 0.0045
        self.rows = []
        self.used = 0
        self.samples = None
        self.started = time.monotonic()
        self.cpu_started = time.process_time()
        self.sweep_seconds = 0.01
        self.library = ctypes.CDLL(str(Path(__file__).with_name("sampler.so")))
        pointer = np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS")
        integer_pointer = np.ctypeslib.ndpointer(dtype=np.int64, flags="C_CONTIGUOUS")
        self.library.sample_posterior.argtypes = [ctypes.c_int] * 4 + [pointer, pointer, ctypes.c_int] + [pointer] * 4 + [integer_pointer] + [ctypes.c_int] * 3 + [ctypes.c_uint64, pointer, pointer]
        self.library.sample_posterior.restype = None
        self.lookup = {tuple(edge): index for index, edge in enumerate(self.edges)}

    def matching(self, size, forced=()):
        occupied = {vertex for edge in forced for vertex in self.edges[edge]}
        neighbors = {}
        for first, second in self.edges:
            if first in occupied or second in occupied:
                continue
            if self.coordinates[first].sum() % 2:
                first, second = second, first
            neighbors.setdefault(first, []).append(second)
        for choices in neighbors.values():
            self.generator.shuffle(choices)
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

        for vertex in self.generator.permutation(list(neighbors)):
            augment(int(vertex), set())
        available = [self.lookup[tuple(sorted((first, second)))] for second, first in partners.items()]
        needed = size - len(forced)
        if len(available) < needed:
            return None
        chosen = self.generator.choice(available, size=needed, replace=False).tolist()
        return sorted([int(edge) for edge in forced] + chosen)

    def random_matching(self, size=None):
        if size is None:
            size = self.maximum
        while True:
            forced = ()
            kind = int(self.generator.integers(3))
            if kind:
                choices = self.nearby_pairs if kind == 1 else self.distant_pairs
                pair = choices[self.generator.integers(len(choices))]
                forced = pair.tolist()
            matching = self.matching(size, forced)
            if matching is not None:
                return matching

    def features(self, matchings):
        single = np.zeros((len(matchings), self.edge_count))
        for row, matching in enumerate(matchings):
            single[row, matching] = 1.0
        pair = single[:, self.pairs[:, 0]] * single[:, self.pairs[:, 1]]
        return np.ascontiguousarray(np.column_stack((np.ones(len(matchings)), single, pair)))

    def spam_features(self, matchings, contexts):
        single = self.features(matchings)[:, 1:self.edge_count + 1]
        sizes = single.sum(axis=1)
        result = [np.ones(len(matchings)), single / np.sqrt(np.maximum(1, sizes))[:, None], sizes / (self.qubits // 2)]
        if self.family == 3:
            contexts = np.asarray(contexts)
            result.extend([np.sin(2 * math.pi * contexts), np.cos(2 * math.pi * contexts),
                           np.sin(4 * math.pi * contexts), np.cos(4 * math.pi * contexts), contexts - 0.5])
        return np.ascontiguousarray(np.column_stack(result))

    def query(self, matching, depth, shots=32):
        response = self.exchange({"type": "experiment", "matching": matching, "depth": int(depth), "shots": int(shots)})
        self.rows.append(response)
        self.used += shots

    def fit(self, sweeps=600, burn=250, thin=3):
        remaining = min(53 - (time.process_time() - self.cpu_started),
                        79 - (time.monotonic() - self.started))
        maximum_sweeps = max(80, int((remaining - 2) / (1.25 * self.sweep_seconds)))
        if sweeps > maximum_sweeps:
            sweeps = maximum_sweeps
            burn = min(burn, sweeps // 3)
        matchings = [row["matching"] for row in self.rows]
        features = self.features(matchings)
        spam = self.spam_features(matchings, [row["context"] for row in self.rows])
        depths = np.array([row["depth"] for row in self.rows], dtype=float)
        shots = np.array([row["shots"] for row in self.rows], dtype=float)
        successes = np.array([row["successes"] for row in self.rows], dtype=float)
        output = np.empty(((sweeps - burn + thin - 1) // thin, self.parameter_count))
        if self.family == 2 and self.samples is not None:
            base = self.samples[:, 1:self.edge_count + 1].mean(axis=0)
            weights = (0.022 - base[self.pairs].sum(axis=1)) ** 2
            self.prior = np.ascontiguousarray((round(0.3 * self.edge_count) + 0.5) * weights / weights.sum())
        sample_started = time.process_time()
        self.library.sample_posterior(len(self.rows), self.edge_count, len(self.pairs), self.family,
                                      features, spam, self.spam_count, depths, shots, successes, self.prior, self.pairs,
                                      sweeps, burn, thin, int(self.generator.integers(2**60)), self.state, output)
        self.sweep_seconds = (time.process_time() - sample_started) / sweeps
        self.samples = output

    def adaptive_batch(self, count):
        candidates = [self.random_matching(self.maximum) for unused in range(350)]
        candidates.extend([pair.tolist() for pair in self.pairs])
        for unused in range(150):
            size = int(self.generator.integers(3, self.maximum))
            candidates.append(self.random_matching(size))
        goals = [self.random_matching(self.maximum + 1) for unused in range(250)]
        features = self.features(candidates)
        rates = features @ self.samples[:, :self.rate_count].T
        means = rates.mean(axis=1)
        centered = (rates - means[:, None]) / math.sqrt(rates.shape[1] - 1)
        goal_rates = self.features(goals) @ self.samples[:, :self.rate_count].T
        goal_centered = (goal_rates - goal_rates.mean(axis=1)[:, None]) / math.sqrt(rates.shape[1] - 1)
        goal_centered /= (0.003 + 0.1 * (-np.expm1(-goal_rates.mean(axis=1))))[:, None]
        importance = goal_centered.T @ goal_centered / len(goals)
        depths = np.clip(2 * np.round(1.55 / means / 2), 2, 256)
        spam = self.spam_features(candidates, np.full(len(candidates), self.used / 12000)) @ self.samples[:, self.rate_count:].mean(axis=0)
        amplitudes = 0.58 + 0.37 / (1 + np.exp(-spam))
        probability = amplitudes * np.exp(-depths * means)
        noise = (1 - probability) / (32 * depths * depths * probability)
        covariance = np.eye(rates.shape[1])
        sparse_count = 0
        sparse_mask = np.array([len(matching) < self.maximum - 1 for matching in candidates])
        for unused in range(count):
            projected = centered @ covariance
            variance = np.sum(projected * centered, axis=1)
            scores = np.sum((projected @ importance) * projected, axis=1) / (variance + noise)
            if sparse_count >= count // 3:
                scores[sparse_mask] = 0.0
            chosen = int(np.argmax(scores))
            sparse_count += int(sparse_mask[chosen])
            direction = projected[chosen]
            covariance -= np.outer(direction, direction) / (variance[chosen] + noise[chosen])
            self.query(candidates[chosen], int(depths[chosen]))

    def run(self):
        self.query([], 256, 64)
        for edge in self.generator.permutation(self.edge_count):
            self.query([int(edge)], 192)
        initial = 180
        for index in range(initial):
            matching = self.random_matching()
            if index % 12 == 0:
                self.query(matching, 0)
            expected = 0.0025 + 0.0045 * len(matching) + self.features([matching])[0, self.edge_count + 1:] @ (self.prior * 0.0225)
            depth = int(2 * round(1.55 / expected / 2))
            self.query(matching, min(256, max(2, depth)))
        while (self.used + 32 <= 12000 and time.process_time() - self.cpu_started < 42
               and time.monotonic() - self.started < 66):
            self.fit()
            remaining = (12000 - self.used) // 32
            count = min(45, remaining)
            if self.family == 3 and count >= 10:
                for unused in range(4):
                    self.query(self.random_matching(), 0)
                count -= 4
            self.adaptive_batch(count)
        self.fit(1500, 500, 4)
        targets = self.exchange({"type": "ready"})["matchings"]
        rates = self.features(targets) @ self.samples[:, :self.rate_count].T
        values = -np.expm1(-rates)
        weights = 1 / (0.003 + 0.1 * values) ** 2
        predictions = (values * weights).sum(axis=1) / weights.sum(axis=1)
        self.exchange({"type": "final", "predictions": predictions.tolist()})


def exchange(message):
    print(json.dumps(message, allow_nan=False), flush=True)
    return json.loads(sys.stdin.readline())


def main():
    hello = json.loads(sys.stdin.readline())
    Policy(hello, exchange).run()


if __name__ == "__main__":
    main()
