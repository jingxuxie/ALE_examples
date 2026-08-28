import itertools
import math

import mpmath as mp
import numpy as np

from .contract import arrays, orders_for, order_key, prefactor


def boundary_log(value):
    return mp.log(mp.mpc(-value, -mp.mpf("1e-90")))


def laurent(function, ultraviolet=False):
    radius = mp.mpf("0.007")
    count = 32
    values = [mp.mpc(0) for index in range(3)]
    for index in range(count):
        phase = mp.exp(2j * mp.pi * (index + mp.mpf("0.37")) / count)
        epsilon = radius * phase
        current = function(epsilon) * epsilon ** 2
        for power in range(3):
            values[power] += current / phase ** power / count / radius ** power
    if ultraviolet:
        return np.array([complex(values[1]), 0j, 0j, complex(values[2])])
    return np.array([0j, complex(values[0]), complex(values[1]), complex(values[2])])


def analytic_triangle(integral):
    masses, invariants, weights, moments, pairs, dimension = arrays(integral)
    if len(masses) != 3 or np.any(masses):
        return None
    edges = [(first, second) for first, second in itertools.combinations(range(3), 2)
             if invariants[first, second] != 0]
    if len(edges) != 1:
        return None
    first, second = edges[0]
    channel = mp.mpf(str(invariants[first, second]))
    exponent = int(sum(weights) - dimension // 2 - pairs)
    parameters = weights + moments
    mu_squared = mp.mpf(str(integral.get("mu2", 1)))
    result = {}
    with mp.workdps(60):
        for order in orders_for(integral):
            degree = sum(order)
            derivatives = mp.mpf(1)
            for power, direction in zip(order, integral.get("directions", [])):
                delta_invariant = direction.get("invariants", np.zeros_like(invariants))[first][second]
                derivatives *= (mp.mpf(str(delta_invariant)) / channel) ** power / math.factorial(power)

            def integrand(epsilon):
                alpha = exponent + epsilon
                numerator = mp.gamma(alpha)
                for index, parameter in enumerate(parameters):
                    numerator *= mp.gamma(int(parameter) - (alpha if index in (first, second) else 0))
                denominator = mp.gamma(int(sum(parameters)) - 2 * alpha)
                expansion = (-1) ** degree * mp.rf(alpha, degree) * derivatives
                scale = mp.exp(epsilon * (mp.euler + mp.log(mu_squared)) - alpha * boundary_log(channel))
                return prefactor(integral) * numerator / denominator * scale * expansion

            result[order_key(order)] = laurent(integrand, exponent <= 0)
    return result


def analytic_box(integral):
    masses, invariants, weights, moments, pairs, dimension = arrays(integral)
    if len(masses) != 4 or np.any(masses) or np.any(weights != 1) or np.any(moments) or pairs or dimension != 4:
        return None
    selected = None
    for permutation in itertools.permutations(range(4)):
        matrix = invariants[np.ix_(permutation, permutation)]
        if matrix[0, 1] == matrix[1, 2] == matrix[2, 3] == 0 and matrix[0, 2] != 0 and matrix[1, 3] != 0:
            selected = permutation
            break
    if selected is None:
        return None
    matrix = invariants[np.ix_(selected, selected)]
    first = mp.mpf(str(matrix[0, 2]))
    second = mp.mpf(str(matrix[1, 3]))
    external = mp.mpf(str(matrix[0, 3]))
    mu_squared = mp.mpf(str(integral.get("mu2", 1)))
    with mp.workdps(60):
        first_log = boundary_log(first) - mp.log(mu_squared)
        second_log = boundary_log(second) - mp.log(mu_squared)
        if external == 0:
            values = [0, 4 / (first * second), -2 * (first_log + second_log) / (first * second),
                      2 / (first * second) * (first_log * second_log - 2 * mp.pi ** 2 / 3)]
        else:
            external_log = boundary_log(external) - mp.log(mu_squared)
            first_dilog = mp.polylog(2, 1 - mp.exp(boundary_log(external) - boundary_log(first)))
            second_dilog = mp.polylog(2, 1 - mp.exp(boundary_log(external) - boundary_log(second)))
            values = [0, 2 / (first * second), 2 * (-first_log - second_log + external_log) / (first * second),
                      2 / (first * second) * (first_log * second_log - external_log ** 2 / 2
                                              - first_dilog - second_dilog - mp.pi ** 2 / 4)]
    return {"base": np.array(list(map(complex, values)))}
