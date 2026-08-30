import functools
import itertools
import numpy as np


@functools.lru_cache(maxsize=6)
def sector(length):
    states = np.array([sum(1 << site for site in occupied)
                       for occupied in itertools.combinations(range(length), 2)])
    spins = ((states[:, None] >> np.arange(length)) & 1).astype(float) - 0.5
    lookup = {int(state): index for index, state in enumerate(states)}
    exchange = np.diag(np.sum(spins * np.roll(spins, -1, axis=1), axis=1))
    for column, state in enumerate(states):
        for site in range(length):
            neighbour = (site + 1) % length
            if ((state >> site) & 1) != ((state >> neighbour) & 1):
                row = lookup[int(state ^ (1 << site) ^ (1 << neighbour))]
                exchange[row, column] = 0.5
    modes = spins @ np.exp(2j * np.pi * np.arange(length)[:, None] * np.arange(1, 4)[None, :] / length)
    return spins, exchange, modes


def quantum_batch(values):
    count, length = values.shape
    values = values - values.mean(axis=1, keepdims=True)
    spins, exchange, modes = sector(length)
    dimension = len(spins)
    diagonal = values @ spins.T
    indices = np.arange(dimension)
    lower, upper = dimension // 3, 2 * dimension // 3
    outputs = []
    for scale in (0.35, 0.6, 1., 1.6):
        both = []
        for sign in (-1, 1):
            matrix = np.broadcast_to(exchange, (count, dimension, dimension)).copy()
            matrix[:, indices, indices] += sign * scale * diagonal
            energies, vectors = np.linalg.eigh(matrix)
            probabilities = np.swapaxes(vectors[:, :, lower:upper] ** 2, 1, 2)
            moments = probabilities @ modes
            denominators = probabilities @ (np.abs(modes) ** 2)
            fractions = 1 - np.abs(moments) ** 2 / np.maximum(denominators, 1e-14)
            local = probabilities @ spins
            local_var = np.mean((local - (2 / length - .5)) ** 2, axis=(1, 2))
            gaps = np.diff(energies[:, lower:upper], axis=1)
            ratios = np.minimum(gaps[:, :-1], gaps[:, 1:]) / np.maximum(gaps[:, :-1], gaps[:, 1:])
            features = [fractions.mean(axis=1), fractions.std(axis=1),
                        np.quantile(fractions[:, :, 0], [.1, .5, .9], axis=1).T,
                        local_var[:, None], ratios.mean(axis=1)[:, None],
                        np.mean(probabilities ** 2, axis=(1, 2))[:, None]]
            both.append(np.column_stack(features))
        outputs.extend([(both[0] + both[1]) / 2, np.abs(both[0] - both[1])])
    return np.column_stack(outputs)


def quantum_features(cases):
    output = np.empty((len(cases), 96))
    for length in sorted({len(case['fields']) for case in cases}):
        indices = [index for index, case in enumerate(cases) if len(case['fields']) == length]
        for start in range(0, len(indices), 32):
            subset = indices[start:start + 32]
            values = np.asarray([cases[index]['fields'] for index in subset])
            output[subset] = quantum_batch(values)
    return output
