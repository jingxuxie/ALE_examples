import math

import numpy as np
from scipy.special import gamma

from .contract import arrays, prefactor
from .quadrature import grid, denominator


def estimate_laurent(integral, settings):
    masses, invariants, weights, moments, pairs, dimension = arrays(integral)
    points, measure = grid(len(masses) - 1, settings["quadrature_order"])
    alpha = int(sum(weights) - dimension // 2 - pairs)
    quadratic = denominator(points, masses, invariants).astype(complex) + 1j * settings["regulator"]
    powers = weights + moments - 1
    numerator = measure * np.prod(points ** powers, axis=1)
    epsilons = settings["epsilon_step"] * np.array([1.0, 1.6, 2.4])
    sampled = []
    for epsilon in epsilons:
        scale = math.exp(np.euler_gamma * epsilon) * float(integral.get("mu2", 1)) ** epsilon
        sampled.append(prefactor(integral) * gamma(alpha + epsilon) * scale
                       * np.sum(numerator * quadratic ** (-alpha - epsilon)))
    fit = np.array([epsilons ** -2, epsilons ** -1, np.ones(3)]).T
    double, single, finite = np.linalg.solve(fit, sampled)
    if alpha <= 0:
        return np.array([single, 0, 0, finite]), len(points) * 3
    return np.array([0, double, single, finite]), len(points) * 3
