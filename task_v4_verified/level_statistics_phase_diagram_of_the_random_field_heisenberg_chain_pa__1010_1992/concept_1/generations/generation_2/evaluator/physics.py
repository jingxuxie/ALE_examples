import functools
import itertools

import numpy as np
from scipy.linalg import eigh


@functools.lru_cache(maxsize=8)
def sector(length):
    if length < 4 or length % 2:
        raise ValueError("An even length of at least four is required")
    states = np.array(sorted(sum(1 << site for site in occupied)
                            for occupied in itertools.combinations(range(length), length // 2)), dtype=np.int64)
    spins = ((states[:, None] >> np.arange(length)) & 1).astype(float) - 0.5
    lookup = {int(state): index for index, state in enumerate(states)}
    exchange = np.zeros((len(states), len(states)), dtype=float)
    diagonal = np.sum(spins * np.roll(spins, -1, axis=1), axis=1)
    np.fill_diagonal(exchange, diagonal)
    for column, state in enumerate(states):
        for site in range(length):
            neighbour = (site + 1) % length
            if ((state >> site) & 1) != ((state >> neighbour) & 1):
                row = lookup[int(state ^ (1 << site) ^ (1 << neighbour))]
                exchange[row, column] += 0.5
    mode = spins @ np.exp(2j * np.pi * np.arange(length) / length)
    return states, spins, exchange, mode


def hamiltonian(fields):
    fields = np.asarray(fields, dtype=float)
    states, spins, exchange, mode = sector(len(fields))
    matrix = exchange.copy()
    matrix.flat[::len(states) + 1] += spins @ fields
    return matrix


def gap_ratio(energies):
    gaps = np.diff(np.asarray(energies))
    if len(gaps) < 2 or np.any(gaps <= 1e-12):
        raise ValueError("Degenerate or insufficient spectrum")
    return float(np.mean(np.minimum(gaps[:-1], gaps[1:]) / np.maximum(gaps[:-1], gaps[1:])))


def observables(fields, vectors=True, full=False, driver="evr"):
    fields = np.asarray(fields, dtype=float)
    if fields.ndim != 1 or not np.isfinite(fields).all():
        raise ValueError("Invalid fields")
    states, spins, exchange, mode = sector(len(fields))
    dimension = len(states)
    lower, upper = dimension // 3, 2 * dimension // 3
    matrix = hamiltonian(fields)
    options = {"check_finite": False, "overwrite_a": True, "driver": driver}
    if not full and driver != "evd":
        options["subset_by_index"] = [lower, upper - 1]
    output = eigh(matrix, eigvals_only=not vectors, **options)
    energies, eigenvectors = output if vectors else (output, None)
    if full or driver == "evd":
        central = energies[lower:upper]
        selected = eigenvectors[:, lower:upper] if vectors else None
    else:
        central, selected = energies, eigenvectors
    result = {"r": gap_ratio(central), "dimension": dimension,
              "min_gap": float(np.min(np.diff(central)))}
    if vectors:
        probabilities = selected ** 2
        numerator = np.abs(probabilities.T @ mode) ** 2
        denominator = probabilities.T @ np.abs(mode) ** 2
        fractions = 1 - numerator / denominator
        result["f"] = float(np.mean(fractions))
    if full:
        result["energies"] = energies
        if vectors:
            result["eigenvectors"] = eigenvectors
    return result
