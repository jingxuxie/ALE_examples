"""Real-space Reynolds projection of scalar and affine polar operators."""

import numpy as np


def project_operators(payload):
    """Project H and the full position, retaining non-Hermitian coefficients."""
    lattice = np.asarray(payload["lattice"], dtype=float)
    vectors = np.asarray(payload["rvec"], dtype=np.int64)
    centers = np.asarray(payload["centers"], dtype=float)
    orbital_count = len(centers)
    diagonal = np.arange(orbital_count)
    unique_vectors, inverse = np.unique(vectors, axis=0, return_inverse=True)
    coefficients = np.zeros((4, len(unique_vectors), orbital_count, orbital_count), complex)
    np.add.at(coefficients[0], inverse, payload["ham"])
    for component in range(3):
        np.add.at(coefficients[component + 1], inverse, payload["connection"][..., component])
    vectors = unique_vectors
    origin_rows = np.flatnonzero(np.all(vectors == 0, axis=1))
    if not len(origin_rows):
        vectors = np.concatenate((vectors, np.zeros((1, 3), dtype=np.int64)))
        coefficients = np.concatenate(
            (coefficients, np.zeros((4, 1, orbital_count, orbital_count), complex)), axis=1
        )
        origin = len(vectors) - 1
    else:
        origin = int(origin_rows[0])
    for component in range(3):
        coefficients[component + 1, origin, diagonal, diagonal] += centers[:, component]

    support = {tuple(vector) for vector in vectors}
    operations = []
    for operation_index, unitary in enumerate(payload["unitary"]):
        rotation = payload["fractional_rotations"][operation_index]
        shifts = payload["orbital_shifts"][operation_index]
        images = np.rint(vectors @ rotation.T).astype(np.int64)
        unique_shifts, labels = np.unique(shifts, axis=0, return_inverse=True)
        groups = []
        for label, shift in enumerate(unique_shifts):
            sources = np.flatnonzero(labels == label)
            targets = np.flatnonzero(np.any(unitary[:, sources] != 0, axis=1))
            groups.append((shift, sources, targets, unitary[np.ix_(targets, sources)]))
        differences = np.unique(
            (unique_shifts[None, :, :] - unique_shifts[:, None, :]).reshape(-1, 3), axis=0
        )
        for difference in differences:
            support.update(map(tuple, images + difference))
        operations.append((images, groups))

    result_vectors = np.array(sorted(support), dtype=np.int64)
    lookup = {tuple(vector): index for index, vector in enumerate(result_vectors)}
    result = np.zeros((4, len(result_vectors), orbital_count, orbital_count), complex)
    origin = lookup[(0, 0, 0)]
    component_indices = np.arange(4)
    operation_count = len(operations)
    for operation_index, (images, groups) in enumerate(operations):
        unitary = payload["unitary"][operation_index]
        cartesian_rotation = payload["cartesian_rotations"][operation_index]
        values = coefficients.conj() if payload["antiunitary"][operation_index] else coefficients
        rotated_components = np.empty_like(values)
        rotated_components[0] = values[0]
        rotated_components[1:] = np.einsum("ab,brnm->arnm", cartesian_rotation, values[1:])
        for left_shift, left_sources, left_targets, left_matrix in groups:
            for right_shift, right_sources, right_targets, right_matrix in groups:
                block = rotated_components[:, :, left_sources][:, :, :, right_sources]
                rotated = left_matrix @ block @ right_matrix.conj().T
                indices = np.fromiter(
                    (lookup[tuple(vector)] for vector in images + right_shift - left_shift),
                    dtype=np.int64, count=len(images),
                )
                result[np.ix_(component_indices, indices, left_targets, right_targets)] += rotated
        offsets = (
            payload["translations"][operation_index] - payload["orbital_shifts"][operation_index]
        ) @ lattice
        for component in range(3):
            result[component + 1, origin] += (
                unitary * offsets[None, :, component]
            ) @ unitary.conj().T

    result /= operation_count
    repaired_centers = np.stack(
        [result[component + 1, origin].diagonal().real for component in range(3)], axis=1
    )
    for component in range(3):
        result[component + 1, origin, diagonal, diagonal] -= repaired_centers[:, component]
    return {
        "rvec": result_vectors,
        "ham": result[0],
        "connection": np.moveaxis(result[1:], 0, -1),
        "centers": repaired_centers,
    }
