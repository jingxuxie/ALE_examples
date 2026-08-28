import numpy as np
from scipy.linalg import eigh


def davidson(effective, initial, tolerance, fallback):
    if effective.size < 8:
        return fallback(effective, initial, tolerance)
    capacity = min(24, effective.size)
    basis = np.empty((capacity, effective.size))
    images = np.empty_like(basis)
    projected = np.zeros((capacity, capacity))
    diagonal_blocks = [np.diag(left)[:, None] + np.diag(right)[None, :]
                       for left, right in zip(effective.hleft, effective.hright)]
    for destination, source, left, right, _ in effective.cross:
        if destination == source:
            diagonal_blocks[source] += np.diag(left)[:, None] * np.diag(right)[None, :]
    diagonal = np.concatenate([block.ravel() for block in diagonal_blocks])
    basis[0] = initial
    images[0] = effective.matvec(initial)
    energy = float(np.dot(initial, images[0]))
    projected[0, 0] = energy
    vector = initial
    residual = images[0] - energy * vector
    size = 1
    for iteration in range(100):
        if np.linalg.norm(residual) <= tolerance * max(1., abs(energy)):
            if iteration == 0:
                return fallback(effective, initial, tolerance)
            return energy, vector
        correction = residual / np.maximum(diagonal - energy, 0.05)
        for _ in range(2):
            correction -= (basis[:size] @ correction) @ basis[:size]
        norm = np.linalg.norm(correction)
        if norm < 1e-13:
            return fallback(effective, vector, tolerance)
        basis[size] = correction / norm
        images[size] = effective.matvec(basis[size])
        overlap = basis[:size + 1] @ images[size]
        projected[size, :size + 1] = overlap
        projected[:size + 1, size] = overlap
        size += 1
        retained = min(3, size) if size == capacity else 1
        energies, coefficients = eigh(projected[:size, :size], subset_by_index=[0, retained - 1],
                                      check_finite=False, driver='evr')
        energy = float(energies[0])
        vector = coefficients[:, 0] @ basis[:size]
        residual = coefficients[:, 0] @ images[:size] - energy * vector
        if size == capacity:
            new_basis = coefficients.T @ basis[:size]
            new_images = coefficients.T @ images[:size]
            basis[:retained] = new_basis
            images[:retained] = new_images
            projected[:retained, :retained] = np.diag(energies)
            size = retained
    return fallback(effective, vector, tolerance)
