import itertools
import math

import mpmath as mp
import numpy as np

from .contract import arrays, orders_for


def harmonic(degree, power=1):
    return sum(1 / index ** power for index in range(1, degree + 1))


def causal_log(invariant, scale):
    return complex(math.log(abs(invariant) / scale), -math.pi if invariant > 0 else 0)


def triangle(integral):
    masses, invariants, weights, moments, pairs, dimension = arrays(integral)
    edges = [(first, second) for first, second in itertools.combinations(range(3), 2)
             if invariants[first, second] != 0]
    if len(edges) != 1 or any(weights != 1) or pairs or dimension != 4:
        raise ValueError("Unsupported massless triangle")
    first, second = edges[0]
    remaining = 3 - first - second
    invariant = invariants[first, second]
    degree = int(sum(moments))
    left, right = int(moments[first]), int(moments[second])
    pole_order = int(left == 0) + int(right == 0)
    constant = ((-1) ** (3 + degree + pole_order)
                * math.factorial(max(left, 1) - 1) * math.factorial(max(right, 1) - 1)
                * math.factorial(int(moments[remaining])) / math.factorial(degree) / (-invariant))
    logarithm = causal_log(invariant, float(integral.get("mu2", 1)))
    linear = -harmonic(max(left, 1) - 1) - harmonic(max(right, 1) - 1) + 2 * harmonic(degree) - logarithm
    quadratic = (-math.pi ** 2 / 12 - harmonic(max(left, 1) - 1, 2) / 2
                 - harmonic(max(right, 1) - 1, 2) / 2 + 2 * harmonic(degree, 2))
    series = np.array([constant, constant * linear, constant * (linear ** 2 / 2 + quadratic)], complex)
    results = []
    for order in orders_for(integral):
        total = sum(order)
        multiplier = np.array([1.0, 0, 0], complex)
        for index in range(1, total + 1):
            multiplier = np.convolve(multiplier, [index, 1])[:3]
        direction_factor = (-1 / invariant) ** total
        for power, direction in zip(order, integral.get("directions", [])):
            if any(direction.get("masses2", [])):
                raise ValueError("Massless triangle directions must preserve masses")
            delta = np.asarray(direction.get("invariants", np.zeros((3, 3))), float)
            if any(delta[row, column] != 0 for row, column in itertools.combinations(range(3), 2)
                   if (row, column) != (first, second)):
                raise ValueError("Massless triangle directions must preserve zero invariants")
            direction_factor *= delta[first, second] ** power / math.factorial(power)
        expanded = direction_factor * np.convolve(series, multiplier)[:3]
        values = np.zeros(4, complex)
        if pole_order == 2:
            values[1:] = expanded
        elif pole_order == 1:
            values[2:] = expanded[:2]
        else:
            values[3] = expanded[0]
        results.append(values)
    return np.array(results), len(results), 4e-15, "analytic-dirichlet-IR-triangle-and-jets"


def dilog_ratio(mass, channel):
    argument = 1 - mp.mpf(mass) / mp.mpf(channel)
    value = mp.polylog(2, argument)
    if argument > 1:
        phase = (1 if channel > 0 else 0) - (1 if mass > 0 else 0)
        value = mp.mpc(mp.re(value), -phase * abs(mp.im(value)))
    return complex(value)


def box(integral):
    masses, invariants, weights, moments, pairs, dimension = arrays(integral)
    if any(weights != 1) or any(moments) or pairs or dimension != 4 or integral.get("directions"):
        raise ValueError("Only scalar massless boxes without Taylor requests are supported")
    edges = [(first, second) for first, second in itertools.combinations(range(4), 2)
             if invariants[first, second] != 0]
    pairings = [(left, right) for left, right in itertools.combinations(edges, 2)
                if len(set(left + right)) == 4]
    if len(edges) not in (2, 3) or len(pairings) != 1:
        raise ValueError("Expected zero- or one-mass box with two nonzero channels")
    left, right = pairings[0]
    first, second = invariants[left], invariants[right]
    scale = float(integral.get("mu2", 1))
    log_first, log_second = causal_log(first, scale), causal_log(second, scale)
    factor = 2 / (first * second)
    if len(edges) == 2:
        values = [0, 2 * factor, -factor * (log_first + log_second),
                  factor * (log_first * log_second - 2 * math.pi ** 2 / 3)]
    else:
        mass = invariants[next(edge for edge in edges if edge not in (left, right))]
        log_mass = causal_log(mass, scale)
        with mp.workdps(40):
            dilogs = dilog_ratio(mass, first) + dilog_ratio(mass, second)
        finite = factor * (log_first * log_second - log_mass ** 2 / 2 - dilogs - math.pi ** 2 / 4)
        values = [0, factor, -factor * (log_first + log_second - log_mass), finite]
    return np.array([values], complex), 1, 4e-15, "analytic-causal-zero-or-one-mass-IR-box"


def massless_coefficients(integral):
    count = len(integral["masses2"])
    if count == 3:
        return triangle(integral)
    if count == 4:
        return box(integral)
    raise ValueError("Unsupported or scaleless massless topology")
