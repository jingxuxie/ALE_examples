import math
import time

import numpy as np

from .contract import arrays, encode, orders_for, order_key, prefactor
from .infrared import analytic_box, analytic_triangle
from .quadrature import simplex_batches, polynomial, deform


def integrate(integral, order, strength):
    masses, invariants, weights, moments, pairs, dimension = arrays(integral)
    scale = max(np.max(np.abs(masses)), np.max(np.abs(invariants)), 1e-100)
    normalized_masses = masses / scale
    normalized_invariants = invariants / scale
    exponent = int(sum(weights) - dimension // 2 - pairs)
    powers = weights + moments - 1
    orders = orders_for(integral)
    directions = []
    for direction in integral.get("directions", []):
        delta_masses = np.array(direction.get("masses2", np.zeros(len(masses))), dtype=float) / scale
        delta_invariants = np.array(direction.get("invariants", np.zeros_like(invariants)), dtype=float) / scale
        directions.append((delta_masses, delta_invariants))
    results = np.zeros((len(orders), 4), dtype=complex)
    scale_factor = prefactor(integral) * scale ** (-exponent)
    mu_log = math.log(float(integral.get("mu2", 1)) / scale)
    for points, measure in simplex_batches(len(masses) - 1, order):
        mapped, determinant = deform(points, normalized_masses, normalized_invariants, strength)
        denominator = polynomial(mapped, normalized_masses, normalized_invariants)
        denominator = denominator - 1j * 1e-290
        weight = measure * determinant * np.prod(mapped ** powers[None, :], axis=1)
        direction_values = [polynomial(mapped, delta_masses, delta_invariants)
                            for delta_masses, delta_invariants in directions]
        for position, multiindex in enumerate(orders):
            degree = sum(multiindex)
            alpha = exponent + degree
            multiplier = np.ones(len(points), dtype=complex)
            for power, delta in zip(multiindex, direction_values):
                if power:
                    multiplier *= delta ** power / math.factorial(power)
            common = scale_factor * (-1) ** degree * weight * multiplier
            if alpha > 0:
                results[position, 3] += math.factorial(alpha - 1) * np.sum(common / denominator ** alpha)
            else:
                power = -alpha
                harmonic = sum(1 / value for value in range(1, power + 1))
                pole = common * (-1) ** power / math.factorial(power) * denominator ** power
                results[position, 0] += np.sum(pole)
                results[position, 3] += np.sum(pole * (harmonic + mu_log - np.log(denominator)))
    return results


def evaluate(integral, settings):
    started = time.perf_counter()
    analytic = analytic_triangle(integral)
    if analytic is None:
        analytic = analytic_box(integral)
    if analytic is not None:
        return {"coefficients": {key: encode(value) for key, value in analytic.items()},
                "seconds": time.perf_counter() - started, "work": 32 * len(analytic),
                "estimated_error": 1e-14, "strategy": "analytic-laurent"}
    masses, invariants, weights, moments, pairs, dimension = arrays(integral)
    strength = float(settings.get("deformation", 0.8)) if np.max(invariants) > 0 else 0
    sequence = settings.get("orders", [16, 24, 36, 52, 76, 108, 148])
    tolerance = float(settings.get("rtol", 3e-10))
    previous = None
    error = 1.0
    work = 0
    for order in sequence:
        current = integrate(integral, order, strength)
        work += order ** (len(masses) - 1)
        if previous is not None:
            normalizer = np.maximum(np.max(np.abs(current), axis=1), 1e-100)
            error = float(np.max(np.max(np.abs(current - previous), axis=1) / normalizer))
            if error < tolerance:
                break
        previous = current
    return {"coefficients": {order_key(multiindex): encode(values) for multiindex, values in zip(orders_for(integral), current)},
            "seconds": time.perf_counter() - started, "work": work,
            "estimated_error": error, "strategy": "contour-moments" if strength else "simplex-moments"}
