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
os.environ["MKL_NUM_THREADS"] = "1"
import numpy as np


class Grid:
    def __init__(self, hello):
        self.edges = [tuple(edge) for edge in hello["edges"]]
        self.edge_count = len(self.edges)
        self.qubits = hello["qubits"]
        self.rows, self.columns = hello["shape"]
        self.coordinates = np.array([(vertex // self.columns, vertex % self.columns)
                                     for vertex in range(self.qubits)])
        self.centers = self.coordinates[np.asarray(self.edges)].mean(axis=1)
        self.pairs = np.array([(first, second) for first, second in itertools.combinations(range(self.edge_count), 2)
                               if not set(self.edges[first]).intersection(self.edges[second])], dtype=np.int32)
        self.distances = np.array([min(np.abs(self.coordinates[vertex] - self.coordinates[other]).sum()
                                       for vertex in self.edges[first] for other in self.edges[second])
                                   for first, second in self.pairs])
        self.lookup = {edge: index for index, edge in enumerate(self.edges)}
        self.near = np.flatnonzero(self.distances <= 2)
        self.far = np.flatnonzero(self.distances >= 3)

    def matching(self, generator, size, forced=()):
        occupied = {vertex for edge in forced for vertex in self.edges[edge]}
        neighbors = {}
        for first, second in self.edges:
            if first in occupied or second in occupied:
                continue
            if sum(self.coordinates[first]) % 2:
                first, second = second, first
            neighbors.setdefault(first, []).append(second)
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
        available = [self.lookup[tuple(sorted((first, second)))] for second, first in partners.items()]
        if len(available) < size - len(forced):
            return None
        chosen = generator.choice(available, size=size-len(forced), replace=False).tolist()
        return sorted([int(edge) for edge in forced] + chosen)

    def pool(self, generator, count, size, varied=False):
        result = []
        known = set()
        attempts = 0
        while len(result) < count and attempts < count*40:
            attempts += 1
            kind = len(result) % 3
            choices = self.near if kind == 1 else self.far
            forced = () if kind == 0 else self.pairs[generator.choice(choices)]
            chosen_size = size
            if varied:
                chosen_size = max(2, size-int(generator.choice([0, 0, 0, 0, 1, 2, size//2])))
            candidate = self.matching(generator, chosen_size, forced)
            if candidate is not None and tuple(candidate) not in known:
                result.append(candidate)
                known.add(tuple(candidate))
        return result

    def features(self, matchings):
        design = np.zeros((len(matchings), self.edge_count))
        for row, matching in enumerate(matchings):
            design[row, matching] = 1
        features = np.column_stack((np.ones(len(matchings)), design,
                                    design[:, self.pairs[:, 0]] * design[:, self.pairs[:, 1]]))
        return design, features


class Policy:
    sampler_name = 'sampler.so'
    sampler_tempered = False

    def __init__(self, hello):
        self.hello = hello
        self.grid = Grid(hello)
        self.generator = np.random.default_rng(72931 + self.grid.qubits)
        self.family = ["local_clusters", "distant_pairs", "anticorrelated", "spam_drift"].index(hello["family"])
        self.edge_count = self.grid.edge_count
        self.pair_count = len(self.grid.pairs)
        self.rate_dimension = 1+self.edge_count+self.pair_count
        self.dimension = self.rate_dimension+self.edge_count+6
        self.state = np.zeros(self.dimension)
        self.state[0] = 0.0025
        self.state[1:1+self.edge_count] = 0.0045
        self.state[-4:] = [0.65, 1.0, 0.0, 0.0]
        self.observations = []
        self.spent = 0
        self.temperature = 1.0
        self.odds = self.make_odds()
        self.library = ctypes.CDLL(str(Path(__file__).parent / self.sampler_name))
        double_array = np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS")
        integer_array = np.ctypeslib.ndpointer(dtype=np.int32, flags="C_CONTIGUOUS")
        self.library.sample_posterior.argtypes = [ctypes.c_int]*5 + [integer_array] + [double_array]*8 + [ctypes.c_int]*3 + [ctypes.c_uint64]
        if self.sampler_tempered:
            self.library.sample_posterior.argtypes += [ctypes.c_double]
        self.library.sample_posterior.restype = None
        self.proxy_matchings = self.grid.pool(self.generator, 192, hello["target_matching_size"])
        self.proxy_design, self.proxy_features = self.grid.features(self.proxy_matchings)

    def make_odds(self):
        distances = self.grid.distances
        if self.family == 0:
            separation = np.abs(self.grid.centers[:, None, :] - self.grid.centers[None, :, :]).sum(axis=2)
            kernels = np.exp(-(separation[:, self.grid.pairs[:, 0]] + separation[:, self.grid.pairs[:, 1]]) / 2)
            anchors = np.array(list(itertools.combinations(range(self.edge_count), 2)))
            weights = (0.002 + kernels[anchors[:, 0]] + kernels[anchors[:, 1]]) * np.exp(-(distances-1)/2)
        elif self.family == 1:
            weights = (distances[None, :] >= 3).astype(float)
        elif self.family == 2:
            weights = np.ones((1, self.pair_count))
        else:
            local = np.exp(-(distances-1)/1.3)+0.05
            weights = (0.5/self.pair_count + 0.5*local/local.sum())[None, :]
        probability = weights / weights.sum(axis=1, keepdims=True) * (round(0.30*self.edge_count)+0.5)
        probability = np.clip(probability, 1e-100, 0.95)
        return np.ascontiguousarray(np.log(probability/(1-probability)))

    def posterior(self, samples=512, burn=700, thin=3):
        design, unused = self.grid.features([record["matching"] for record in self.observations])
        depth = np.array([record["depth"] for record in self.observations], dtype=float)
        successes = np.array([record["successes"] for record in self.observations], dtype=float)
        shots = np.array([record["shots"] for record in self.observations], dtype=float)
        context = np.array([record["context"] for record in self.observations], dtype=float)
        output = np.empty((samples, self.dimension))
        self.library.sample_posterior(self.edge_count, self.pair_count, len(self.observations), self.family,
                                      len(self.odds), self.grid.pairs, self.odds, design, depth, successes,
                                      shots, context, self.state, output, samples, burn, thin,
                                      int(self.generator.integers(0, 2**63)),
                                      *((self.temperature,) if self.sampler_tempered else ()))
        return output

    def probabilities(self, posterior, design, rates, depths, context):
        spam = posterior[:, self.rate_dimension:]
        sizes = design.sum(axis=1)
        latent = spam[:, 0, None] + spam[:, 1, None] * (sizes/(self.grid.qubits//2))[None, :]
        latent += spam[:, 2:2+self.edge_count] @ design.T / np.sqrt(np.maximum(1, sizes))[None, :]
        if self.family == 3:
            latent += (spam[:, -4]*np.sin(2*np.pi*spam[:, -3]*context+spam[:, -2])
                       + spam[:, -1]*(context-0.5))[:, None]
        return (0.58+0.37/(1+np.exp(-latent))) * np.exp(-rates*depths[None, :])

    def select_batch(self, posterior, batch_size):
        candidates = self.grid.pool(self.generator, 400, self.hello["max_matching_size"], varied=True)
        design, features = self.grid.features(candidates)
        candidate_rates = posterior[:, :self.rate_dimension] @ features.T
        mean_rates = candidate_rates.mean(axis=0)
        multipliers = np.array([1.15, 1.85])
        depths = np.clip(2*np.rint(multipliers[:, None]/mean_rates[None, :]/2), 2, 256).astype(int)
        candidate_rates = np.tile(candidate_rates, (1, len(multipliers)))
        design = np.tile(design, (len(multipliers), 1))
        depths = depths.ravel()
        probabilities = self.probabilities(posterior, design, candidate_rates, depths, (self.spent+16)/2000)
        centered = probabilities-probabilities.mean(axis=0)
        noise = np.mean(probabilities*(1-probabilities), axis=0)/32
        target_rates = -np.expm1(-(posterior[:, :self.rate_dimension] @ self.proxy_features.T))
        target_centered = (target_rates-target_rates.mean(axis=0))/(0.003+0.1*target_rates.mean(axis=0))
        covariance = centered.T @ centered / len(posterior)
        target_covariance = target_centered.T @ centered / len(posterior)
        chosen = []
        forbidden = np.zeros(len(depths), dtype=bool)
        for index in range(batch_size):
            denominator = np.maximum(1e-9, np.diag(covariance)+noise)
            utilities = np.sum(target_covariance**2, axis=0)/denominator
            utilities[forbidden] = -1
            selected = int(np.argmax(utilities))
            chosen.append((candidates[selected % len(candidates)], int(depths[selected])))
            column = covariance[:, selected].copy()
            target_column = target_covariance[:, selected].copy()
            target_covariance -= np.outer(target_column, column)/denominator[selected]
            covariance -= np.outer(column, column)/denominator[selected]
            forbidden[selected % len(candidates)::len(candidates)] = True
        return chosen

    def run(self, exchange):
        while self.spent <= 2000-32:
            posterior = self.posterior()
            remaining = (2000-self.spent)//32
            batch_size = min(10, remaining)
            for matching, depth in self.select_batch(posterior, batch_size):
                shots = 48 if self.spent == 1952 else 32
                observation = exchange({"type": "experiment", "matching": matching, "depth": depth, "shots": shots})
                self.observations.append(observation)
                self.spent += shots
        targets = exchange({"type": "ready"})
        posterior = self.posterior(samples=2048, burn=1400, thin=4)
        unused, features = self.grid.features(targets["matchings"])
        rates = -np.expm1(-(posterior[:, :self.rate_dimension] @ features.T))
        weights = (0.003+0.10*rates)**-2
        predictions = np.sum(weights*rates, axis=0)/weights.sum(axis=0)
        exchange({"type": "final", "predictions": predictions.tolist()})

