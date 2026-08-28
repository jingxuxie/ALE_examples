import numpy as np


def project_hamiltonian(payload):
    hopping = payload["ham"]
    count = hopping.shape[1]
    accumulated = {}
    operation_count = len(payload["unitary"])
    for operation_index in range(operation_count):
        rotation = payload["fractional_rotations"][operation_index]
        orbital_rotation = payload["unitary"][operation_index]
        shifts = payload["orbital_shifts"][operation_index]
        transformed_vectors = payload["rvec"] @ rotation.T
        values = hopping.conj() if payload["antiunitary"][operation_index] else hopping
        unique_shifts, labels = np.unique(shifts, axis=0, return_inverse=True)
        for left_label, left_shift in enumerate(unique_shifts):
            left = np.flatnonzero(labels == left_label)
            for right_label, right_shift in enumerate(unique_shifts):
                right = np.flatnonzero(labels == right_label)
                block = values[:, left][:, :, right]
                rotated = orbital_rotation[:, left] @ block @ orbital_rotation[:, right].conj().T
                images = transformed_vectors + right_shift - left_shift
                for vector, matrix in zip(images, rotated):
                    if not np.any(matrix):
                        continue
                    key = tuple(int(value) for value in vector)
                    if key not in accumulated:
                        accumulated[key] = np.zeros((count, count), dtype=complex)
                    accumulated[key] += matrix / operation_count
    vectors = np.array(sorted(accumulated), dtype=np.int64)
    matrices = np.array([accumulated[tuple(vector)] for vector in vectors])
    return vectors, matrices


def energies(payload):
    reduced_centers = payload["centers"] @ np.linalg.inv(payload["lattice"])
    displacements = payload["rvec"][:, None, None, :] + reduced_centers[None, None, :, :] - reduced_centers[None, :, None, :]
    values = []
    for point in payload["query_points"]:
        phases = np.exp(2j * np.pi * np.einsum("rmna,a->rmn", displacements, point))
        matrix = np.einsum("rmn,rmn->mn", payload["ham"], phases)
        values.append(np.linalg.eigvalsh((matrix + matrix.conj().T) / 2))
    return np.array(values)
