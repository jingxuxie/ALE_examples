#!/usr/bin/env python3
"""Periodic integer grids, closest reciprocal images, and tetrahedron spectra."""

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import math
import sys

import numpy as np


TETRAHEDRA = np.array(
    [
        [[0, 1, 7, 3], [0, 1, 7, 5], [0, 2, 7, 3],
         [0, 2, 7, 6], [0, 4, 7, 5], [0, 4, 7, 6]],
        [[1, 6, 0, 2], [1, 6, 0, 4], [1, 6, 2, 3],
         [1, 6, 3, 7], [1, 6, 4, 5], [1, 6, 5, 7]],
        [[2, 5, 0, 1], [2, 5, 0, 4], [2, 5, 1, 3],
         [2, 5, 3, 7], [2, 5, 4, 6], [2, 5, 6, 7]],
        [[3, 4, 0, 1], [3, 4, 0, 2], [3, 4, 1, 5],
         [3, 4, 2, 6], [3, 4, 5, 7], [3, 4, 6, 7]],
    ], dtype=np.int64,
)


def adjugate(matrix):
    values = np.asarray(matrix, dtype=object)
    result = np.empty((3, 3), dtype=object)
    for row in range(3):
        for column in range(3):
            rows = [index for index in range(3) if index != column]
            columns = [index for index in range(3) if index != row]
            result[row, column] = ((-1) ** (row + column)) * (
                values[rows[0], columns[0]] * values[rows[1], columns[1]]
                - values[rows[0], columns[1]] * values[rows[1], columns[0]]
            )
    determinant = sum(values[0, index] * result[index, 0] for index in range(3))
    return result, int(determinant)


def reduced_basis(lattice):
    original = np.asarray(lattice, dtype=np.longdouble)
    transform = np.eye(3, dtype=object)

    def orthogonalize():
        basis = original @ np.asarray(transform, dtype=np.longdouble)
        orthogonal = basis.copy()
        coefficients = np.zeros((3, 3), dtype=np.longdouble)
        lengths = np.empty(3, dtype=np.longdouble)
        for column in range(3):
            for previous in range(column):
                coefficients[column, previous] = (
                    np.dot(basis[:, column], orthogonal[:, previous]) / lengths[previous]
                )
                orthogonal[:, column] -= (
                    coefficients[column, previous] * orthogonal[:, previous]
                )
            lengths[column] = np.dot(orthogonal[:, column], orthogonal[:, column])
        return basis, coefficients, lengths

    column = 1
    basis, coefficients, lengths = orthogonalize()
    while column < 3:
        for previous in range(column - 1, -1, -1):
            multiple = int(np.rint(coefficients[column, previous]))
            if multiple:
                transform[:, column] -= multiple * transform[:, previous]
                basis, coefficients, lengths = orthogonalize()
        if lengths[column] >= (
            np.longdouble("0.99") - coefficients[column, column - 1] ** 2
        ) * lengths[column - 1]:
            column += 1
        else:
            transform[:, [column - 1, column]] = transform[:, [column, column - 1]]
            basis, coefficients, lengths = orthogonalize()
            column = max(1, column - 1)
    return basis, transform


def closest_images(lattice, grid_adjugate, determinant, queries, tolerance):
    basis, transform = reduced_basis(lattice)
    inverse_transform, sign = adjugate(transform)
    inverse_transform *= sign
    numerator_transform = inverse_transform @ grid_adjugate
    scale = np.sqrt(np.max(np.sum(basis * basis, axis=0)))
    normalized = basis / scale
    triangular = np.linalg.qr(np.asarray(normalized, dtype=np.float64))[1]
    normalized_tolerance = np.longdouble(tolerance) / (scale * scale)
    offsets = [0]
    shifts = []
    distances = np.empty(len(queries), dtype=np.float64)
    cache = {}
    epsilon = np.finfo(np.float64).eps
    precise_epsilon = np.finfo(np.longdouble).eps

    def enumerate_images(residue):
        fractional = np.asarray(residue, dtype=np.longdouble) / determinant
        approximate = np.asarray(fractional, dtype=np.float64)
        babai = np.zeros(3, dtype=np.int64)
        for axis in (2, 1, 0):
            remainder = np.dot(
                triangular[axis, axis + 1:],
                approximate[axis + 1:] + babai[axis + 1:],
            )
            babai[axis] = int(np.rint(-approximate[axis] - remainder / triangular[axis, axis]))
        cartesian = normalized @ (fractional + babai)
        best = np.dot(cartesian, cartesian)
        candidates = []
        margin = 128 * epsilon * (1 + float(best + normalized_tolerance))
        radius = float(best + normalized_tolerance) + margin
        last_center = -approximate[2]
        last_radius = math.sqrt(max(0.0, radius)) / abs(triangular[2, 2])
        for last in range(math.ceil(last_center - last_radius), math.floor(last_center + last_radius) + 1):
            last_value = approximate[2] + last
            last_distance = (triangular[2, 2] * last_value) ** 2
            middle_center = -approximate[1] - triangular[1, 2] * last_value / triangular[1, 1]
            middle_radius = math.sqrt(max(0.0, radius - last_distance)) / abs(triangular[1, 1])
            for middle in range(math.ceil(middle_center - middle_radius), math.floor(middle_center + middle_radius) + 1):
                middle_value = approximate[1] + middle
                partial = last_distance + (
                    triangular[1, 1] * middle_value + triangular[1, 2] * last_value
                ) ** 2
                if partial > radius:
                    continue
                first_center = -approximate[0] - (
                    triangular[0, 1] * middle_value + triangular[0, 2] * last_value
                ) / triangular[0, 0]
                first_radius = math.sqrt(max(0.0, radius - partial)) / abs(triangular[0, 0])
                for first in range(math.ceil(first_center - first_radius), math.floor(first_center + first_radius) + 1):
                    candidate = (first, middle, last)
                    cartesian = normalized @ (fractional + candidate)
                    distance = np.dot(cartesian, cartesian)
                    candidates.append((candidate, distance))
                    if distance < best:
                        best = distance
                        radius = float(best + normalized_tolerance) + margin
        tie_margin = 16 * precise_epsilon * max(best, np.longdouble("1e-30"))
        images = [candidate for candidate, distance in candidates
                  if distance <= best + normalized_tolerance + tie_margin]
        return images, float(best * scale * scale)

    for index, address in enumerate(queries):
        numerator = numerator_transform @ np.asarray(address, dtype=object)
        quotient = np.array([int(value) // determinant for value in numerator], dtype=object)
        residue = tuple(int(value) % determinant for value in numerator)
        if residue not in cache:
            cache[residue] = enumerate_images(residue)
        images, distances[index] = cache[residue]
        translated = [tuple(int(value) for value in transform @ (np.asarray(image, dtype=object) - quotient))
                      for image in images]
        translated.sort()
        shifts.extend(translated)
        offsets.append(len(shifts))
    return (np.asarray(offsets, dtype=np.int64),
            np.asarray(shifts, dtype=np.int64).reshape(-1, 3), distances)


def periodic_vertices(addresses, grid_adjugate, determinant):
    count = len(addresses)
    moduli = []
    coefficients = []
    for row in grid_adjugate:
        divisor = math.gcd(determinant, math.gcd(int(row[0]), math.gcd(int(row[1]), int(row[2]))))
        moduli.append(determinant // divisor)
        coefficients.append([int(value // divisor) % (determinant // divisor) for value in row])
    moduli = np.asarray(moduli, dtype=np.int64)
    coefficients = np.asarray(coefficients, dtype=np.int64)
    residues = ((addresses % determinant) @ coefficients.T) % moduli
    product = math.prod(int(value) for value in moduli)

    if product <= np.iinfo(np.uint64).max:
        def encode(values):
            unsigned = values.astype(np.uint64)
            return (unsigned[:, 0] * np.uint64(moduli[1]) + unsigned[:, 1]) * np.uint64(moduli[2]) + unsigned[:, 2]
    else:
        def encode(values):
            return np.ascontiguousarray(values).view(
                np.dtype([("first", np.int64), ("second", np.int64), ("third", np.int64)])
            ).ravel()

    keys = encode(residues)
    order = np.argsort(keys)
    sorted_keys = keys[order]
    vertices = np.empty((count, 8), dtype=np.int64)
    vertices[:, 0] = np.arange(count)
    for vertex in range(1, 8):
        displacement = coefficients @ np.array([vertex & 1, (vertex >> 1) & 1, (vertex >> 2) & 1])
        vertex_keys = encode((residues + displacement) % moduli)
        vertices[:, vertex] = order[np.searchsorted(sorted_keys, vertex_keys)]
    return vertices


def tree_coordinates(samples):
    count = len(samples)
    base = 1 << (max(1, count) - 1).bit_length()
    lower = np.empty(2 * base)
    upper = np.empty(2 * base)
    lower[base:base + count] = samples
    lower[base + count:] = samples[-1]
    upper[base:] = lower[base:]
    start = base // 2
    while start:
        stop = 2 * start
        lower[start:stop] = lower[2 * start:2 * stop:2]
        upper[start:stop] = upper[2 * start + 1:2 * stop:2]
        start //= 2
    lower[0] = 0
    upper[0] = 0
    centers = lower
    radii = upper - lower
    return base, centers, radii


def interval_coefficients(energies, centers, radii, region):
    first, second, third, fourth = energies.T
    span = fourth - first
    if region == 0:
        gap_first = second - first
        gap_second = third - first
        distance = centers - first
        ratio_first = distance / gap_first
        ratio_second = distance / gap_second
        scaled_first = radii / gap_first
        scaled_second = radii / gap_second
        cumulative = ratio_first * ratio_second * (distance / span)
        density = 3 * ratio_first * ratio_second / span
        derivative = 6 * scaled_first * ratio_second / span
        curvature = 3 * scaled_first * scaled_second / span
    elif region == 2:
        gap_first = fourth - third
        gap_second = fourth - second
        distance = fourth - centers
        ratio_first = distance / gap_first
        ratio_second = distance / gap_second
        scaled_first = radii / gap_first
        scaled_second = radii / gap_second
        cumulative = ((centers - third) / gap_first
                      + ratio_first * (centers - second) / gap_second
                      + ratio_first * ratio_second * (centers - first) / span)
        density = 3 * ratio_first * ratio_second / span
        derivative = -6 * scaled_first * ratio_second / span
        curvature = 3 * scaled_first * scaled_second / span
    else:
        gap = third - second
        gap_lower = third - first
        gap_upper = fourth - second
        lower = (centers - first) / gap_lower
        outer = (centers - first) / span
        middle = (centers - second) / gap
        upper = (centers - second) / gap_upper
        lower_complement = (third - centers) / gap_lower
        outer_complement = (fourth - centers) / span
        middle_complement = (third - centers) / gap
        upper_complement = (fourth - centers) / gap_upper
        cumulative = (lower * outer + middle * outer * lower_complement
                      + middle * upper * outer_complement)
        density = 3 * (lower * middle_complement + upper_complement * middle) / span
        derivative = 3 * ((radii / gap_lower) * middle_complement
                          - lower * (radii / gap) - (radii / gap_upper) * middle
                          + upper_complement * (radii / gap)) / span
        curvature = -3 * (radii / gap) * (radii / gap_lower + radii / gap_upper) / span
    return (cumulative, radii * density, radii * derivative * 0.5,
            radii * curvature / 3, density, derivative, curvature)


def integrate_tetrahedra(energies, samples):
    count = len(samples)
    base, centers, radii = tree_coordinates(samples)
    coefficients = np.zeros((7, 2 * base))
    positions = np.searchsorted(samples, energies, side="right")
    completed = np.cumsum(np.bincount(positions[:, 3], minlength=count + 1)[:count])

    for region in range(3):
        active = np.flatnonzero(positions[:, region] < positions[:, region + 1])
        lower = positions[active, region] + base
        upper = positions[active, region + 1] + base
        while len(active):
            left = (lower & 1).astype(bool)
            right = (upper & 1).astype(bool)
            for selection, nodes in ((left, lower[left]), (right, upper[right] - 1)):
                if len(nodes):
                    values = interval_coefficients(
                        energies[active[selection]], centers[nodes], radii[nodes], region,
                    )
                    for component, value in enumerate(values):
                        coefficients[component] += np.bincount(nodes, weights=value, minlength=2 * base)
            lower = (lower + left) // 2
            upper = (upper - right) // 2
            remaining = lower < upper
            active = active[remaining]
            lower = lower[remaining]
            upper = upper[remaining]

    start = 1
    while start < base:
        parents = np.arange(start, 2 * start)
        children = np.arange(2 * start, 4 * start)
        parent_radii = np.repeat(radii[parents], 2)
        displacement = np.divide(
            centers[children] - np.repeat(centers[parents], 2), parent_radii,
            out=np.zeros(len(children)), where=parent_radii != 0,
        )
        ratio = np.divide(radii[children], parent_radii,
                          out=np.zeros(len(children)), where=parent_radii != 0)
        values = np.repeat(coefficients[:, parents], 2, axis=1)
        coefficients[0, children] += values[0] + displacement * (
            values[1] + displacement * (values[2] + displacement * values[3]))
        coefficients[1, children] += ratio * (
            values[1] + displacement * (2 * values[2] + 3 * displacement * values[3]))
        coefficients[2, children] += ratio ** 2 * (values[2] + 3 * displacement * values[3])
        coefficients[3, children] += ratio ** 3 * values[3]
        coefficients[4, children] += values[4] + displacement * (values[5] + displacement * values[6])
        coefficients[5, children] += ratio * (values[5] + 2 * displacement * values[6])
        coefficients[6, children] += ratio ** 2 * values[6]
        start *= 2
    cumulative = (coefficients[0, base:base + count] + completed) / len(energies)
    density = coefficients[4, base:base + count] / len(energies)
    return np.clip(cumulative, 0, 1), np.maximum(density, 0)


def spectral_integrals(lattice, grid_matrix, grid_adjugate, determinant,
                       addresses, frequencies, samples):
    branches = frequencies.shape[1]
    cumulative = np.empty((len(samples), branches))
    density = np.empty_like(cumulative)
    if len(samples) == 0:
        return cumulative, density
    vertices = periodic_vertices(addresses, grid_adjugate, determinant)
    microcell = lattice @ (np.asarray(grid_adjugate, dtype=np.float64) / determinant)
    diagonals = np.array([[1, 1, 1], [-1, 1, 1], [1, -1, 1], [1, 1, -1]]) @ microcell.T
    diagonal = np.argmin(np.einsum("ij,ij->i", diagonals, diagonals))
    tetrahedra = vertices[:, TETRAHEDRA[diagonal]].reshape(-1, 4)
    del vertices
    for branch in range(branches):
        branch_frequencies = frequencies[:, branch]
        origin = branch_frequencies.min()
        width = branch_frequencies.max() - origin
        if width == 0:
            cumulative[:, branch] = samples > origin
            density[:, branch] = 0
            continue
        energies = np.sort(branch_frequencies[tetrahedra], axis=1)
        cumulative[:, branch], density[:, branch] = integrate_tetrahedra(energies, samples)
    return cumulative, density


def solve(data):
    grid_matrix = data["grid_matrix"]
    lattice = data["reciprocal_lattice"]
    grid_adjugate, determinant = adjugate(grid_matrix)
    offsets, shifts, distances = closest_images(
        lattice, grid_adjugate, determinant, data["query_addresses"],
        float(data["tie_tolerance"]),
    )
    cumulative, density = spectral_integrals(
        lattice, grid_matrix, grid_adjugate, determinant, data["grid_addresses"],
        data["frequencies"], data["sampling_points"],
    )
    return {"image_offsets": offsets, "image_shifts": shifts,
            "distance2": distances, "dos": density, "cumulative": cumulative}


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python solve.py INPUT.npz OUTPUT.npz")
    with np.load(sys.argv[1], allow_pickle=False) as data:
        result = solve(data)
    np.savez_compressed(sys.argv[2], **result)


if __name__ == "__main__":
    main()
