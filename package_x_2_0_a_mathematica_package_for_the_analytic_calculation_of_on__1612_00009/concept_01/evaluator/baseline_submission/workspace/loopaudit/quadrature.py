import functools
import itertools

import numpy as np
from numpy.polynomial.legendre import leggauss


@functools.lru_cache(maxsize=16)
def grid(dimension, order):
    if not dimension:
        return np.ones((1, 1)), np.ones(1)
    nodes, weights = leggauss(order)
    nodes = (nodes + 1) / 2
    weights = weights / 2
    combinations = list(itertools.product(range(order), repeat=dimension))
    points = []
    measures = []
    for indices in combinations:
        remaining = 1.0
        barycentric = [0.0] * (dimension + 1)
        measure = 1.0
        for axis, index in enumerate(indices):
            barycentric[axis + 1] = remaining * nodes[index]
            remaining *= 1 - nodes[index]
            measure *= weights[index] * (1 - nodes[index]) ** (dimension - axis - 1)
        barycentric[0] = remaining
        points.append(barycentric)
        measures.append(measure)
    return np.array(points), np.array(measures)


def denominator(points, masses, invariants):
    result = points @ masses
    for first, second in itertools.combinations(range(len(masses)), 2):
        result -= invariants[first, second] * points[:, first] * points[:, second]
    return result
