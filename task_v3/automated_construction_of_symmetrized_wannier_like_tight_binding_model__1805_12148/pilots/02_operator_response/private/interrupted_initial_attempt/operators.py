"""Real-space magnetic-group projection of H and the affine position operator."""

import numpy as np


def project_operators(payload):
    """Project full position coefficients, then extract their Wannier centers."""
    lattice = np.asarray(payload["lattice"], dtype=float)
    vectors = np.asarray(payload["rvec"], dtype=np.int64)
    hopping = np.asarray(payload["ham"], dtype=complex)
    connection = np.asarray(payload["connection"], dtype=complex)
    centers = np.asarray(payload["centers"], dtype=float)
    orbital_count = hopping.shape[1]
    diagonal = np.arange(orbital_count)
    origin_matches = np.flatnonzero(np.all(vectors == 0, axis=1))
    if len(origin_matches):
        origin = int(origin_matches[0])
    else:
        origin = len(vectors)
        vectors = np.concatenate((vectors, np.zeros((1, 3), dtype=np.int64)))
        hopping = np.concatenate((hopping, np.zeros_like(hopping[:1])))
        connection = np.concatenate((connection, np.zeros_like(connection[:1])))

    coefficients = np.empty((4, len(vectors), orbital_count, orbital_count), dtype=complex)
    coefficients[0] = hopping
    coefficients[1:] = connection.transpose(3, 0, 1, 2)
    coefficients[1:, origin, diagonal, diagonal] += centers.T

    operation_data = []
    support = {tuple(vector) for vector in vectors}
    for rotation, unitary, shifts in zip(
        payload["fractional_rotations"], payload["unitary"], payload["orbital_shifts"]
    ):
        image_vectors = vectors @ rotation.T
        distinct_shifts, labels = np.unique(shifts, axis=0, return_inverse=True)
        groups = []
        for label, shift in enumerate(distinct_shifts):
            sources = np.flatnonzero(labels == label)
            targets = np.flatnonzero(np.any(unitary[:, sources] != 0, axis=1))
            groups.append((shift, sources, targets, unitary[np.ix_(targets, sources)]))
        for left_shift, _, _, _ in groups:
            for right_shift, _, _, _ in groups:
                support.update(tuple(vector) for vector in image_vectors + right_shift - left_shift)
        operation_data.append((image_vectors, groups))

    output_vectors = np.array(sorted(support), dtype=np.int64)
    lookup = {tuple(vector): index for index, vector in enumerate(output_vectors)}
    output_origin = lookup[(0, 0, 0)]
    accumulated = np.zeros((4, len(output_vectors), orbital_count, orbital_count), dtype=complex)
    operation_count = len(operation_data)

    for operation, (image_vectors, groups) in enumerate(operation_data):
        values = coefficients.conj() if payload["antiunitary"][operation] else coefficients.copy()
        cartesian_rotation = payload["cartesian_rotations"][operation]
        values[1:] = np.einsum("ab,brnm->arnm", cartesian_rotation, values[1:])
        for left_shift, left_sources, left_targets, left_unitary in groups:
            for right_shift, right_sources, right_targets, right_unitary in groups:
                images = image_vectors + right_shift - left_shift
                image_indices = np.array([lookup[tuple(vector)] for vector in images])
                block = values[:, :, left_sources[:, None], right_sources]
                transformed = left_unitary @ block @ right_unitary.conj().T
                destination = (
                    slice(None),
                    image_indices[:, None, None],
                    left_targets[None, :, None],
                    right_targets[None, None, :],
                )
                accumulated[destination] += transformed / operation_count

        unitary = payload["unitary"][operation]
        offsets = (payload["translations"][operation] - payload["orbital_shifts"][operation]) @ lattice
        affine_term = (unitary[None, :, :] * offsets.T[:, None, :]) @ unitary.conj().T
        accumulated[1:, output_origin] += affine_term / operation_count

    repaired_centers = accumulated[1:, output_origin, diagonal, diagonal].real.T.copy()
    accumulated[1:, output_origin, diagonal, diagonal] -= repaired_centers.T
    return {
        "rvec": output_vectors,
        "ham": accumulated[0],
        "connection": accumulated[1:].transpose(1, 2, 3, 0),
        "centers": repaired_centers,
    }
