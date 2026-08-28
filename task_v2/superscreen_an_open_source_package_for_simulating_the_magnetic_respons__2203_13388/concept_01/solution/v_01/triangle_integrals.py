import math

import numba
import numpy as np
from numpy.polynomial.legendre import leggauss


@numba.njit(cache=True)
def potential_and_integral(point, triangle):
    relative = triangle - point
    lengths = np.empty(3)
    for vertex in range(3):
        lengths[vertex] = math.sqrt(np.dot(relative[vertex], relative[vertex]))
    potential = 0.0
    integral_x = 0.0
    integral_y = 0.0
    for edge in range(3):
        following = (edge + 1) % 3
        delta_x = triangle[following, 0] - triangle[edge, 0]
        delta_y = triangle[following, 1] - triangle[edge, 1]
        length = math.sqrt(delta_x * delta_x + delta_y * delta_y)
        normal_x = delta_y / length
        normal_y = -delta_x / length
        radii = lengths[edge] + lengths[following]
        denominator = max(radii - length, 1e-300)
        logarithm = math.log1p(2 * length / denominator)
        distance = relative[edge, 0] * normal_x + relative[edge, 1] * normal_y
        potential += distance * logarithm
        integral_x += normal_x * logarithm
        integral_y += normal_y * logarithm
    height = point[2] - triangle[0, 2]
    solid_angle = 0.0
    if abs(height) > 1e-14:
        first, second, third = relative[0], relative[1], relative[2]
        determinant = first[0] * (second[1] * third[2] - second[2] * third[1])
        determinant -= first[1] * (second[0] * third[2] - second[2] * third[0])
        determinant += first[2] * (second[0] * third[1] - second[1] * third[0])
        denominator = lengths[0] * lengths[1] * lengths[2]
        denominator += lengths[0] * np.dot(second, third)
        denominator += lengths[1] * np.dot(first, third)
        denominator += lengths[2] * np.dot(first, second)
        solid_angle = abs(2 * math.atan2(determinant, denominator))
        potential -= abs(height) * solid_angle
    return potential, integral_x, integral_y, math.copysign(solid_angle, height)


@numba.njit(cache=True)
def _inductance(triangles, nodes, weights):
    count = len(triangles)
    result = np.empty((count, count))
    for target in range(count):
        first = triangles[target, 1] - triangles[target, 0]
        second = triangles[target, 2] - triangles[target, 0]
        jacobian = abs(first[0] * second[1] - first[1] * second[0])
        for source in range(count):
            value = 0.0
            for quadrature in range(len(weights)):
                point = (nodes[quadrature, 0] * triangles[target, 0]
                         + nodes[quadrature, 1] * triangles[target, 1]
                         + nodes[quadrature, 2] * triangles[target, 2])
                potential, _, _, _ = potential_and_integral(point, triangles[source])
                value += weights[quadrature] * potential
            result[target, source] = jacobian * value / (4 * np.pi)
    return (result + result.T) / 2


def triangle_inductance(triangles, order=6):
    nodes, weights = leggauss(order)
    nodes, weights = (nodes + 1) / 2, weights / 2
    barycentric = []
    combined = []
    for first, first_weight in zip(nodes, weights):
        for second, second_weight in zip(nodes, weights):
            barycentric.append((1 - first, first * (1 - second), first * second))
            combined.append(first_weight * second_weight * first)
    return _inductance(np.ascontiguousarray(triangles), np.array(barycentric), np.array(combined))


@numba.njit(cache=True)
def field_operators(triangles, observers):
    operators = np.empty((len(observers), len(triangles), 3))
    for observer in range(len(observers)):
        for source in range(len(triangles)):
            _, integral_x, integral_y, integral_z = potential_and_integral(observers[observer], triangles[source])
            operators[observer, source, 0] = integral_x / (4 * np.pi)
            operators[observer, source, 1] = integral_y / (4 * np.pi)
            operators[observer, source, 2] = integral_z / (4 * np.pi)
    return operators


def field_from_current(operators, current, mu0):
    field = np.empty((len(current), len(operators), 3))
    field[:, :, 0] = mu0 * (current[:, :, 1] @ operators[:, :, 2].T)
    field[:, :, 1] = -mu0 * (current[:, :, 0] @ operators[:, :, 2].T)
    field[:, :, 2] = mu0 * (current[:, :, 0] @ operators[:, :, 1].T - current[:, :, 1] @ operators[:, :, 0].T)
    return field
