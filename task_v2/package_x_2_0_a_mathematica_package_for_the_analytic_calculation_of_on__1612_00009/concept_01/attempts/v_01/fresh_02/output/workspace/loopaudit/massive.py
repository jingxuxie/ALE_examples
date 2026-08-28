import functools
import heapq
import itertools
import math

import numpy as np
from numpy.polynomial.legendre import leggauss

from .contract import arrays, orders_for, prefactor


@functools.lru_cache(maxsize=2)
def simplex_grid(dimension, order):
    if dimension == 0:
        return np.ones((1, 1)), np.ones(1)
    nodes, weights = leggauss(order)
    nodes, weights = (nodes + 1) / 2, weights / 2
    indices = np.indices((order,) * dimension).reshape(dimension, -1)
    remaining = np.ones(indices.shape[1])
    measure = remaining.copy()
    points = np.empty((len(remaining), dimension + 1))
    for axis in range(dimension):
        coordinate = nodes[indices[axis]]
        points[:, axis + 1] = remaining * coordinate
        remaining = remaining * (1 - coordinate)
        measure *= weights[indices[axis]] * (1 - coordinate) ** (dimension - axis - 1)
    points[:, 0] = remaining
    return points, measure


def denominator(points, masses, invariants):
    return points @ masses - np.sum((points @ invariants) * points, axis=1) / 2


def minimum_denominator(masses, invariants):
    minimum = min(masses)
    count = len(masses)
    for size in range(2, count + 1):
        for subset in itertools.combinations(range(count), size):
            indices = list(subset)
            matrix = np.ones((size + 1, size + 1))
            matrix[:size, :size] = invariants[np.ix_(indices, indices)]
            matrix[-1, -1] = 0
            target = np.r_[masses[indices], 1]
            solution = np.linalg.lstsq(matrix, target, rcond=None)[0]
            if np.max(abs(matrix @ solution - target)) < 1e-11 and min(solution[:size]) >= -1e-12:
                point = np.zeros(count)
                point[indices] = solution[:size]
                minimum = min(minimum, denominator(point[None, :], masses, invariants)[0])
    return minimum


def deform(points, masses, invariants, strength):
    gradient = masses - points @ invariants
    average = np.sum(points * gradient, axis=1)
    tangent = gradient - average[:, None]
    complex_points = points - 1j * strength * points * tangent
    dimension = len(masses) - 1
    average_derivative = (masses[1:] - masses[0]
                          - 2 * (points @ invariants[:, 1:] - (points @ invariants[:, 0])[:, None]))
    derivative = points[:, 1:, None] * (invariants[1:, 0, None] - invariants[1:, 1:]
                                       - average_derivative[:, None, :])
    for axis in range(dimension):
        derivative[:, axis, axis] += tangent[:, axis + 1]
    jacobian = np.linalg.det(np.eye(dimension)[None, :, :] - 1j * strength * derivative)
    return complex_points, jacobian


@functools.lru_cache(maxsize=32)
def gauss_rule(order):
    return leggauss(order)


def region_grid(dimension, order, bounds):
    axis_orders = (order,) * dimension if isinstance(order, int) else order
    indices = np.indices(axis_orders).reshape(dimension, -1)
    remaining = np.ones(indices.shape[1])
    measure = remaining.copy()
    points = np.empty((len(remaining), dimension + 1))
    for axis, (lower, upper) in enumerate(bounds):
        nodes, weights = gauss_rule(axis_orders[axis])
        coordinate = lower + (upper - lower) * (nodes[indices[axis]] + 1) / 2
        points[:, axis + 1] = remaining * coordinate
        remaining = remaining * (1 - coordinate)
        measure *= (upper - lower) * weights[indices[axis]] / 2 * (1 - coordinate) ** (dimension - axis - 1)
    points[:, 0] = remaining
    return points, measure


def integrate(integral, order, strength, bounds=None):
    masses, invariants, weights, moments, pairs, dimension = arrays(integral)
    scale = max(max(masses), np.max(abs(invariants)))
    masses, invariants = masses / scale, invariants / scale
    alpha = int(sum(weights) - dimension // 2 - pairs)
    orders = orders_for(integral)
    directions = [(np.asarray(direction.get("masses2", np.zeros(len(masses))), float) / scale,
                   np.asarray(direction.get("invariants", np.zeros_like(invariants)), float) / scale)
                  for direction in integral.get("directions", [])]
    points, measures = (simplex_grid(len(masses) - 1, order) if bounds is None
                        else region_grid(len(masses) - 1, order, bounds))
    results = np.zeros((len(orders), 4), complex)
    log_scale = math.log(float(integral.get("mu2", 1)) / scale)
    for start in range(0, len(points), 32768):
        coordinates = points[start:start + 32768]
        measure = measures[start:start + 32768]
        if strength:
            coordinates, jacobian = deform(coordinates, masses, invariants, strength)
            measure = measure * jacobian
        quadratic = denominator(coordinates, masses, invariants).astype(complex)
        if strength:
            quadratic.imag = -np.abs(quadratic.imag)
        numerator = measure * np.prod(coordinates ** (weights + moments - 1), axis=1)
        variations = [denominator(coordinates, delta_mass, delta_invariant)
                      for delta_mass, delta_invariant in directions]
        for index, powers in enumerate(orders):
            degree = sum(powers)
            exponent = alpha + degree
            multiplier = (-1) ** degree / math.prod(math.factorial(power) for power in powers)
            insertion = numerator * multiplier
            for power, variation in zip(powers, variations):
                if power:
                    insertion = insertion * variation ** power
            if exponent > 0:
                results[index, 3] += math.factorial(exponent - 1) * np.sum(insertion / quadratic ** exponent)
            else:
                degree_uv = -exponent
                residue = (-1) ** degree_uv / math.factorial(degree_uv) * insertion * quadratic ** degree_uv
                results[index, 0] += np.sum(residue)
                harmonic = sum(1 / number for number in range(1, degree_uv + 1))
                results[index, 3] += np.sum(residue * (harmonic + log_scale - np.log(quadratic)))
    return results * prefactor(integral) * scale ** (-alpha), len(points)


def adaptive_integrate(integral, settings, strength):
    dimension = len(integral["masses2"]) - 1
    low_order, high_order = settings.get("adaptive_orders", [8, 12])
    tolerance = settings["relative_tolerance"]
    work = 0

    def cell(bounds):
        nonlocal work
        high, high_work = integrate(integral, high_order, strength, bounds)
        work += high_work
        if settings.get("adaptive_split", "directional") == "cyclic":
            low, low_work = integrate(integral, low_order, strength, bounds)
            work += low_work
            return high, abs(high - low), 0
        axis_errors = []
        for axis in range(dimension):
            axis_orders = [high_order] * dimension
            axis_orders[axis] = low_order
            low, low_work = integrate(integral, tuple(axis_orders), strength, bounds)
            work += low_work
            axis_errors.append(abs(high - low))
        magnitude = np.maximum(np.max(abs(high), axis=1), 1e-280)[:, None]
        selected = int(np.argmax([np.max(axis_error / magnitude) for axis_error in axis_errors]))
        return high, np.sum(axis_errors, axis=0), selected

    bounds = [(0.0, 1.0)] * dimension
    total, errors, axis = cell(bounds)
    scale = np.maximum(np.max(abs(total), axis=1), 1e-280)[:, None]
    serial = 0
    queue = [(-float(np.max(errors / scale)), serial, bounds, total.copy(), errors.copy(), 0, axis)]
    converged = False
    for iteration in range(settings.get("adaptive_max_cells", 1024)):
        magnitude = np.maximum(np.max(abs(total), axis=1), 1e-280)[:, None]
        error = float(np.max(errors / magnitude))
        if error < tolerance:
            converged = True
            break
        priority, identifier, bounds, old_value, old_error, depth, axis = heapq.heappop(queue)
        if settings.get("adaptive_split", "directional") == "cyclic":
            axis = depth % dimension
        midpoint = sum(bounds[axis]) / 2
        children = []
        for interval in [(bounds[axis][0], midpoint), (midpoint, bounds[axis][1])]:
            child_bounds = list(bounds)
            child_bounds[axis] = interval
            value, child_error, child_axis = cell(child_bounds)
            serial += 1
            children.append((value, child_error))
            heapq.heappush(queue, (-float(np.max(child_error / scale)), serial,
                                  child_bounds, value, child_error, depth + 1, child_axis))
        total += children[0][0] + children[1][0] - old_value
        errors = np.maximum(0, errors + children[0][1] + children[1][1] - old_error)
    magnitude = np.maximum(np.max(abs(total), axis=1), 1e-280)[:, None]
    return total, work, float(np.max(errors / magnitude)), converged, len(queue)


def massive_coefficients(integral, settings):
    masses, invariants, weights, moments, pairs, dimension = arrays(integral)
    scale = max(max(masses), np.max(abs(invariants)))
    minimum = minimum_denominator(masses / scale, invariants / scale)
    cut = minimum < 0
    strength = float(settings.get("contour_strength", 3.0)) if cut else 0.0
    orders = settings["cut_orders"] if cut else settings["smooth_orders"]
    previous = None
    work = 0
    error = 1.0
    converged = False
    for order in orders:
        values, cost = integrate(integral, order, strength)
        work += cost
        if previous is not None:
            magnitudes = np.maximum(np.max(abs(values), axis=1), 1e-280)
            error = float(np.max(np.max(abs(values - previous), axis=1) / magnitudes))
            if error < settings["relative_tolerance"]:
                converged = True
                break
        previous = values
    strategy = ("causal-simplex-contour" if cut else "real-simplex") + ";analytic-Laurent-and-jets"
    strategy += f";Gauss={order};lambda={strength}"
    if not converged and settings.get("adaptive", False) and len(masses) > 1:
        values, cost, error, converged, cells = adaptive_integrate(integral, settings, strength)
        work += cost
        strategy += f";adaptive-cells={cells}"
    strategy += ";" + ("refined" if converged else "UNCONVERGED")
    return values, work, error, strategy
