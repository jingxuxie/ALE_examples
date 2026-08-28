import itertools
import math

import numpy as np

from .contract import shifted


def coefficient(integral, order, settings, function):
    if not any(order):
        return function(shifted(integral, [0] * len(order)))
    step = settings["difference_step"]
    nodes = []
    stencils = []
    for degree in order:
        if degree == 0:
            nodes.append(np.array([0.0]))
            stencils.append(np.array([1.0]))
            continue
        locations = np.arange(-degree, degree + 1, dtype=float)
        vandermonde = np.array([locations ** power for power in range(len(locations))])
        target = np.zeros(len(locations))
        target[degree] = 1
        nodes.append(locations * step)
        stencils.append(np.linalg.solve(vandermonde, target) / step ** degree)
    result = np.zeros(4, dtype=complex)
    for indices in itertools.product(*(range(len(axis)) for axis in nodes)):
        displacement = [nodes[axis][index] for axis, index in enumerate(indices)]
        weight = math.prod(stencils[axis][index] for axis, index in enumerate(indices))
        result += weight * function(shifted(integral, displacement))
    return result
