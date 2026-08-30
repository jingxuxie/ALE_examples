import itertools

import numpy as np
from scipy.linalg.lapack import ssyevd


def prepare_sector(length=10):
    states = sorted(sum(1 << site for site in occupied)
                    for occupied in itertools.combinations(range(length), length // 2))
    states = np.asarray(states, dtype=np.int64)
    spins = ((states[:, None] >> np.arange(length)) & 1).astype(np.float32) - 0.5
    lookup = {int(state): index for index, state in enumerate(states)}
    dimension = len(states)
    exchange = np.zeros((dimension, dimension), dtype=np.float32, order='F')
    diagonal = np.diag_indices(dimension)
    exchange[diagonal] = np.sum(spins * np.roll(spins, -1, axis=1), axis=1)
    for column, state in enumerate(states):
        for site in range(length):
            neighbor = (site + 1) % length
            if ((state >> site) & 1) != ((state >> neighbor) & 1):
                row = lookup[int(state ^ (1 << site) ^ (1 << neighbor))]
                exchange[row, column] += 0.5
    mode = spins @ np.exp(2j * np.pi * np.arange(length) / length)
    observables = np.column_stack((mode.real, mode.imag, np.abs(mode) ** 2)).astype(np.float32)
    return spins, exchange, diagonal, observables


def solve_fraction(fields, sector):
    spins, exchange, diagonal, observables = sector
    dimension = len(spins)
    centered = np.asarray(fields, dtype=np.float64) - np.mean(fields)
    matrix = exchange.copy(order='F')
    matrix[diagonal] += spins @ centered.astype(np.float32)
    energies, vectors, info = ssyevd(matrix, compute_v=1, lower=1, overwrite_a=1)
    if info != 0:
        raise RuntimeError(f'Eigensolver failed: {info}')
    probabilities = vectors[:, dimension // 3:2 * dimension // 3] ** 2
    moments = probabilities.T @ observables
    fractions = 1 - (moments[:, 0] ** 2 + moments[:, 1] ** 2) / moments[:, 2]
    return float(np.clip(np.mean(fractions, dtype=np.float64), 0, 1))
