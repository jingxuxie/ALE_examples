import functools
import itertools

import numpy as np
from numpy.polynomial.legendre import leggauss


@functools.lru_cache(maxsize=32)
def nodes(order):
    points, weights = leggauss(order)
    return (points + 1) / 2, weights / 2


def simplex_batches(dimension, order):
    if dimension == 0:
        yield np.ones((1, 1)), np.ones(1)
        return
    points, weights = nodes(order)
    for offset in range(0, order, 8):
        point_axes = [points[offset:offset + 8]] + [points] * (dimension - 1)
        weight_axes = [weights[offset:offset + 8]] + [weights] * (dimension - 1)
        grids = np.meshgrid(*point_axes, indexing="ij")
        weight_grids = np.meshgrid(*weight_axes, indexing="ij")
        count = grids[0].size
        result = np.empty((count, dimension + 1))
        product = np.ones(count)
        remaining = np.ones(count)
        for axis in range(dimension):
            coordinate = grids[axis].ravel()
            result[:, axis + 1] = remaining * coordinate
            product *= weight_grids[axis].ravel() * (1 - coordinate) ** (dimension - axis - 1)
            remaining *= 1 - coordinate
        result[:, 0] = remaining
        yield result, product


def polynomial(points, masses, invariants):
    result = points @ masses
    for first, second in itertools.combinations(range(len(masses)), 2):
        result = result - invariants[first, second] * points[:, first] * points[:, second]
    return result


def deform(points, masses, invariants, strength):
    dimension = len(masses) - 1
    if not strength or dimension == 0:
        return points.astype(complex), np.ones(len(points), dtype=complex)
    coordinates = points[:, 1:]
    hessian = invariants[0, 1:, None] + invariants[0, None, 1:] - invariants[1:, 1:]
    linear = masses[1:] - masses[0] - invariants[0, 1:]
    gradient = coordinates @ hessian + linear
    average = np.sum(coordinates * gradient, axis=1)
    displacement = coordinates * (gradient - average[:, None])
    complex_points = points.astype(complex)
    complex_points[:, 1:] -= 1j * strength * displacement
    complex_points[:, 0] += 1j * strength * np.sum(displacement, axis=1)
    identity = np.eye(dimension)
    average_gradient = gradient + coordinates @ hessian
    derivative = (gradient - average[:, None])[:, :, None] * identity[None, :, :]
    derivative += coordinates[:, :, None] * (hessian[None, :, :] - average_gradient[:, None, :])
    determinant = np.linalg.det(identity[None, :, :] - 1j * strength * derivative)
    return complex_points, determinant
