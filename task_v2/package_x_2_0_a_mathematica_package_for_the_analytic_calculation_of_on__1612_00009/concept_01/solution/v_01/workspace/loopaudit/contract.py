import itertools
import math

import numpy as np


CHANNELS = ("uv", "ir2", "ir1", "finite")


def order_key(order):
    return ",".join(map(str, order)) if order else "base"


def orders_for(integral):
    return integral.get("orders", [[]])


def arrays(integral):
    masses = np.array(integral["masses2"], dtype=float)
    invariants = np.array(integral["invariants"], dtype=float)
    count = len(masses)
    weights = np.array(integral.get("weights", [1] * count), dtype=int)
    moments = np.array(integral.get("moments", [0] * count), dtype=int)
    pairs = int(integral.get("metric_pairs", 0))
    dimension = int(integral.get("dimension", 4))
    return masses, invariants, weights, moments, pairs, dimension


def prefactor(integral):
    masses, invariants, weights, moments, pairs, dimension = arrays(integral)
    sign = (-1) ** int(sum(weights) + sum(moments) + pairs)
    return sign / (2 ** pairs * math.prod(math.factorial(int(value) - 1) for value in weights))


def encode(values):
    return {channel: [float(complex(value).real), float(complex(value).imag)]
            for channel, value in zip(CHANNELS, values)}


def decode(values):
    return np.array([complex(*values[channel]) for channel in CHANNELS])


def shifted(integral, displacements):
    result = dict(integral)
    masses, invariants, weights, moments, pairs, dimension = arrays(integral)
    for delta, direction in zip(displacements, integral.get("directions", [])):
        masses = masses + delta * np.array(direction.get("masses2", np.zeros(len(masses))), dtype=float)
        invariants = invariants + delta * np.array(direction.get("invariants", np.zeros_like(invariants)), dtype=float)
    result["masses2"] = masses.tolist()
    result["invariants"] = invariants.tolist()
    result["directions"] = []
    result["orders"] = [[]]
    return result


def all_orders(directions, degree):
    return [list(order) for order in itertools.product(range(degree + 1), repeat=directions)
            if sum(order) <= degree]
