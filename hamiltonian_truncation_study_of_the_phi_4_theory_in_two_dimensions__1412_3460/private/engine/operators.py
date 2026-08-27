import itertools
import math
from collections import Counter, defaultdict

import numba
import numpy as np
from scipy import sparse


def monomials(modes, frequencies, length, degree, transfer):
    groups = {}
    for count in range(degree + 1):
        by_momentum = defaultdict(list)
        for indices in itertools.combinations_with_replacement(range(len(modes)), count):
            by_momentum[int(sum(modes[index] for index in indices))].append(indices)
        groups[count] = by_momentum
    creations, annihilations, coefficients = [], [], []
    for count in range(degree + 1):
        for momentum, incoming in groups[count].items():
            outgoing = groups[degree - count].get(momentum + transfer, [])
            for annihilation in incoming:
                for creation in outgoing:
                    multiplicity = math.prod(math.factorial(value) for value in Counter(annihilation).values())
                    multiplicity *= math.prod(math.factorial(value) for value in Counter(creation).values())
                    coefficient = length * math.factorial(degree) / multiplicity
                    coefficient /= math.prod(math.sqrt(2 * length * frequencies[index])
                                             for index in creation + annihilation)
                    creations.append(creation + (-1,) * (4 - len(creation)))
                    annihilations.append(annihilation + (-1,) * (4 - len(annihilation)))
                    coefficients.append(coefficient)
    return (np.asarray(creations, dtype=np.int64).reshape(-1, 4),
            np.asarray(annihilations, dtype=np.int64).reshape(-1, 4),
            np.asarray(coefficients))


@numba.njit(cache=True)
def assemble(states, hashes, weights, order, creations, annihilations, coefficients):
    rows = [0]
    columns = [0]
    values = [0.0]
    sorted_hashes = hashes[order]
    for operator_index in range(len(coefficients)):
        delta_hash = np.uint64(0)
        for mode in creations[operator_index]:
            if mode >= 0:
                delta_hash += weights[mode]
        for mode in annihilations[operator_index]:
            if mode >= 0:
                delta_hash -= weights[mode]
        for column in range(len(states)):
            destination_hash = hashes[column] + delta_hash
            position = np.searchsorted(sorted_hashes, destination_hash)
            if position == len(states) or sorted_hashes[position] != destination_hash:
                continue
            row = order[position]
            state = states[column].copy()
            amplitude = 1.0
            for mode in annihilations[operator_index]:
                if mode >= 0:
                    amplitude *= state[mode]
                    state[mode] -= 1
                    if state[mode] < 0:
                        amplitude = 0.0
                        break
            if amplitude == 0:
                continue
            for mode in creations[operator_index]:
                if mode >= 0:
                    state[mode] += 1
                    amplitude *= state[mode]
            if np.any(state != states[row]):
                continue
            rows.append(row)
            columns.append(column)
            values.append(coefficients[operator_index] * math.sqrt(amplitude))
    return np.asarray(rows), np.asarray(columns), np.asarray(values)


def operator_matrix(modes, frequencies, states, length, degree, transfer=0):
    if degree == 0:
        return sparse.eye(len(states), format='csr') * length if transfer == 0 else sparse.csr_matrix((len(states), len(states)))
    weights = np.random.default_rng(78125).integers(0, 2**63, len(modes), dtype=np.uint64)
    hashes = np.sum(states.astype(np.uint64) * weights[None, :], axis=1, dtype=np.uint64)
    if len(np.unique(hashes)) != len(hashes):
        raise RuntimeError('State-key collision')
    creations, annihilations, coefficients = monomials(modes, frequencies, length, degree, transfer)
    rows, columns, values = assemble(states, hashes, weights, np.argsort(hashes),
                                    creations, annihilations, coefficients)
    result = sparse.coo_matrix((values, (rows, columns)), shape=(len(states), len(states))).tocsr()
    result.eliminate_zeros()
    return result
