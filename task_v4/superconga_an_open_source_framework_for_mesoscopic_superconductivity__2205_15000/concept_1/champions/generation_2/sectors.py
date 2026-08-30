import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu

from numerics import Topology


class HarmonicSectors:
    def __init__(self, model, field):
        self.model = model
        topology = Topology(model)
        self.centers = topology.holes
        self.sources = model.sources
        self.targets = model.targets
        edge_count = len(self.sources)
        self.incidence = coo_matrix(
            (np.tile([-1., 1.], edge_count),
             (np.repeat(np.arange(edge_count), 2),
              np.column_stack((self.sources, self.targets)).ravel())),
            shape=(edge_count, model.size)).tocsr()
        self.angles = np.angle(topology.points[:, None] - self.centers[None, :])
        self.raw = self.angles[self.targets] - self.angles[self.sources]
        self.raw -= 2 * np.pi * np.rint(self.raw / (2 * np.pi))
        self.build(field)
        distances = abs(self.centers[:, None] - self.centers[None, :])
        neighbors = np.argsort(distances, axis=1)[:, 1:9]
        connected = np.zeros(distances.shape, dtype=bool)
        connected[np.arange(len(self.centers))[:, None], neighbors] = True
        self.pair_first, self.pair_second = np.nonzero(np.triu(connected | connected.T, 1))

    def build(self, field):
        self.field = field
        weights = self.model.stiffness * abs(field[self.sources]) * abs(field[self.targets])
        weights = np.maximum(weights, 1e-12 * np.max(weights))
        self.weights = weights
        phase = self.model.phase(field)
        incidence = self.incidence[:, 1:]
        weighted_incidence = incidence.multiply(weights[:, None])
        laplacian = (incidence.T @ weighted_incidence).tocsc()
        factor = splu(laplacian)
        right = incidence.T @ (weights[:, None] * np.column_stack((self.raw, phase)))
        correction = factor.solve(right)
        projected = self.raw - incidence @ correction[:, :-1]
        self.phase = phase - incidence @ correction[:, -1]
        self.rotation = self.angles.copy()
        self.rotation[1:] -= correction[:, :-1]
        self.offset = np.zeros(self.model.size)
        self.offset[1:] = -correction[:, -1]
        self.hessian = projected.T @ (weights[:, None] * projected)
        self.hessian = (self.hessian + self.hessian.T) / 2
        self.linear = projected.T @ (weights * self.phase)
        self.center = np.linalg.solve(self.hessian, -self.linear)
        self.lower = np.floor(self.center)
        self.projected = projected

    def candidate(self, change):
        return self.field * np.exp(1j * (self.rotation @ change + self.offset))

    def corrected(self, archive, strength=1.0):
        states = np.asarray(list(archive.keys()))
        values = np.asarray(list(archive.values()))
        count = len(self.linear)
        offsets = -2 * self.lower - 1
        spins = 2 * states + offsets
        first, second = self.pair_first, self.pair_second
        features = np.column_stack((2 * states,
                                    spins[:, first] * spins[:, second] - offsets[first] * offsets[second]))
        residuals = values - np.einsum('ij,ij->i', states, states @ self.hessian) - 2 * states @ self.linear
        ridge = 2.0
        if len(values) < features.shape[1]:
            coefficients = features.T @ np.linalg.solve(
                features @ features.T + ridge * np.eye(len(values)), residuals)
        else:
            coefficients = np.linalg.solve(
                features.T @ features + ridge * np.eye(features.shape[1]), features.T @ residuals)
        coefficients = np.clip(coefficients, -0.12, 0.12) * strength
        linear = self.linear + coefficients[:count]
        hessian = self.hessian.copy()
        pairs = coefficients[count:]
        np.add.at(linear, first, pairs * offsets[second])
        np.add.at(linear, second, pairs * offsets[first])
        hessian[first, second] += 2 * pairs
        hessian[second, first] += 2 * pairs
        return hessian, linear


def anneal(hessian, linear, lower, centers, budget, replicas=256, sweeps=250,
           seed=4, starts=None, expanded=False):
    rng = np.random.default_rng(seed)
    count = len(linear)
    bias = linear + hessian @ lower
    diagonal = hessian.diagonal()
    states = rng.integers(0, 2, (replicas, count)).astype(float)
    if starts is not None:
        initial_count = min(len(starts), replicas)
        states[:initial_count] = np.clip(np.asarray(starts[:initial_count]) - lower, 0, 1)
    states[0] = np.clip(-lower, 0, 1)
    states[1] = 1 - states[0]
    fields = states @ hessian + bias
    scale = np.median(diagonal)
    temperatures = np.geomspace(0.7 * scale, 0.001 * scale, sweeps)
    distances = abs(centers[:, None] - centers[None, :])
    neighbors = np.argsort(distances, axis=1)[:, 1:7]
    complement = np.sum(hessian, axis=0) + 2 * bias
    for sweep, temperature in enumerate(temperatures):
        if budget.remaining() < 4.5:
            break
        for index in rng.permutation(count):
            change = 1 - 2 * states[:, index]
            costs = 2 * change * fields[:, index] + diagonal[index]
            change *= costs < -temperature * np.log(rng.random(replicas))
            states[:, index] += change
            fields += change[:, None] * hessian[index]
        if expanded and count > 1:
            for first in rng.permutation(count):
                second = rng.choice(neighbors[first])
                change_first = 1 - 2 * states[:, first]
                change_second = 1 - 2 * states[:, second]
                costs = (2 * change_first * fields[:, first] + diagonal[first]
                         + 2 * change_second * fields[:, second] + diagonal[second]
                         + 2 * change_first * change_second * hessian[first, second])
                accept = costs < -temperature * np.log(rng.random(replicas))
                change_first *= accept
                change_second *= accept
                states[:, first] += change_first
                states[:, second] += change_second
                fields += change_first[:, None] * hessian[first] + change_second[:, None] * hessian[second]
            if count > 3:
                for move in range(3):
                    size = int(rng.integers(3, min(35, count + 1)))
                    indices = np.argsort(distances[rng.integers(count)])[:size]
                    changes = 1 - 2 * states[:, indices]
                    increments = changes @ hessian[indices]
                    costs = np.sum(changes * (2 * fields[:, indices] + increments[:, indices]), axis=1)
                    accept = costs < -temperature * np.log(rng.random(replicas))
                    states[:, indices] += changes * accept[:, None]
                    fields += increments * accept[:, None]
            costs = np.sum(complement) - 2 * states @ complement
            accept = costs < -temperature * np.log(rng.random(replicas))
            states[accept] = 1 - states[accept]
            fields[accept] = complement - fields[accept]
    for sweep in range(10):
        improved = False
        for index in rng.permutation(count):
            change = 1 - 2 * states[:, index]
            costs = 2 * change * fields[:, index] + diagonal[index]
            change *= costs < -1e-10
            improved |= np.any(change)
            states[:, index] += change
            fields += change[:, None] * hessian[index]
        if not improved:
            break
    changes = np.unique(states + lower, axis=0)
    energies = np.einsum('ij,ij->i', changes, changes @ hessian) + 2 * changes @ linear
    order = np.argsort(energies)
    return energies[order], changes[order]
