import itertools

import numpy as np
from scipy.linalg.lapack import dsyevd, ssyevd


class SmallRing:
    def __init__(self):
        length = 10
        states = np.array(sorted(sum(1 << site for site in occupied)
                                 for occupied in itertools.combinations(range(length), length // 2)))
        self.spins = ((states[:, None] >> np.arange(length)) & 1).astype(np.float64) - 0.5
        lookup = {int(state): index for index, state in enumerate(states)}
        self.exchange = np.zeros((len(states), len(states)), dtype=np.float32, order='F')
        np.fill_diagonal(self.exchange, np.sum(self.spins * np.roll(self.spins, -1, axis=1), axis=1))
        for column, state in enumerate(states):
            for site in range(length):
                neighbour = (site + 1) % length
                if ((state >> site) & 1) != ((state >> neighbour) & 1):
                    row = lookup[int(state ^ (1 << site) ^ (1 << neighbour))]
                    self.exchange[row, column] += 0.5
        mode = self.spins @ np.exp(2j * np.pi * np.arange(length) / length)
        self.moments = np.array([mode.real, mode.imag, np.abs(mode) ** 2]).T

    def predict(self, fields):
        fields = np.asarray(fields, dtype=np.float64)
        fields = fields - fields.mean()
        matrix = self.exchange.copy(order='F')
        matrix.flat[::253] += self.spins @ fields
        energies, vectors, info = ssyevd(matrix, compute_v=1, lower=1, overwrite_a=1)
        if info != 0:
            return None
        if np.min(np.diff(energies[83:169])) < 1e-4:
            matrix = np.array(self.exchange, dtype=np.float64, order='F')
            matrix.flat[::253] += self.spins @ fields
            energies, vectors, info = dsyevd(matrix, compute_v=1, lower=1, overwrite_a=1)
            if info != 0:
                return None
        moments = (vectors[:, 84:168] ** 2).T @ self.moments
        fractions = 1 - (moments[:, 0] ** 2 + moments[:, 1] ** 2) / moments[:, 2]
        return float(np.clip(np.mean(fractions), 0.0, 1.0))


_ring = None


def initialize_worker():
    global _ring
    _ring = SmallRing()
    _ring.predict(np.linspace(-2.0, 2.0, 10))


def predict_small(job):
    index, fields = job
    return index, _ring.predict(fields)
