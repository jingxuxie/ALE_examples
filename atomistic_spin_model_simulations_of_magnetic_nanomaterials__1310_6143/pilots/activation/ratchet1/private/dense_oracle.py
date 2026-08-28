import numpy as np


def energy_gradient(case, spins):
    exchange = np.asarray(case["exchange_meV"])
    anisotropy = np.asarray(case["anisotropy_meV"])
    field = np.asarray(case["field_meV"])
    energy = -sum(exchange[index] * np.dot(spins[index], spins[index + 1]) for index in range(len(exchange)))
    gradient = np.zeros_like(spins)
    for index, spin in enumerate(spins):
        energy -= spin @ anisotropy[index] @ spin + field @ spin
        gradient[index] = -2 * anisotropy[index] @ spin - field
    for index, coupling in enumerate(exchange):
        gradient[index] -= coupling * spins[index + 1]
        gradient[index + 1] -= coupling * spins[index]
    return float(energy), gradient


def tangent_basis(spins):
    axes = np.eye(3)[np.argmin(np.abs(spins), axis=1)]
    first = np.cross(spins, axes)
    first /= np.linalg.norm(first, axis=1)[:, None]
    second = np.cross(spins, first)
    return np.stack((first, second), axis=2)


def tangent_hessian(case, spins):
    count = len(spins)
    basis = tangent_basis(spins)
    _, gradient = energy_gradient(case, spins)
    hessian = np.zeros((2 * count, 2 * count))
    for index, tensor in enumerate(case["anisotropy_meV"]):
        diagonal = -2 * np.asarray(tensor) - np.dot(spins[index], gradient[index]) * np.eye(3)
        hessian[2 * index:2 * index + 2, 2 * index:2 * index + 2] = basis[index].T @ diagonal @ basis[index]
    for index, coupling in enumerate(case["exchange_meV"]):
        block = -coupling * basis[index].T @ basis[index + 1]
        hessian[2 * index:2 * index + 2, 2 * index + 2:2 * index + 4] = block
        hessian[2 * index + 2:2 * index + 4, 2 * index:2 * index + 2] = block.T
    return hessian


def diagnostics(case, spins):
    spins = np.asarray(spins, dtype=float)
    energy, gradient = energy_gradient(case, spins)
    projected = gradient - np.sum(gradient * spins, axis=1)[:, None] * spins
    eigenvalues = np.linalg.eigvalsh(tangent_hessian(case, spins))
    return {
        "energy_meV": energy,
        "residual_meV": float(np.max(np.linalg.norm(projected, axis=1))),
        "eigenvalues": eigenvalues,
        "negative_modes": int(np.sum(eigenvalues < -1e-6)),
        "zero_modes": int(np.sum(np.abs(eigenvalues) <= 1e-6)),
    }


def log_omega0(minimum_eigenvalues, saddle_eigenvalues):
    minimum_eigenvalues = np.asarray(minimum_eigenvalues)
    saddle_eigenvalues = np.asarray(saddle_eigenvalues)
    if np.any(minimum_eigenvalues <= 0) or saddle_eigenvalues[0] >= 0 or np.any(saddle_eigenvalues[1:] <= 0):
        return float("nan")
    return float(0.5 * (np.log(minimum_eigenvalues).sum() - np.log(saddle_eigenvalues[1:]).sum()))


def finite_difference_hessian(case, spins, epsilon=2e-5):
    basis = tangent_basis(spins)
    count = len(spins)
    origin_gradient = energy_gradient(case, spins)[1]
    result = np.zeros((2 * count, 2 * count))
    for coordinate in range(2 * count):
        index, component = divmod(coordinate, 2)
        direction = np.zeros_like(spins)
        direction[index] = basis[index, :, component]
        positive = spins + epsilon * direction
        negative = spins - epsilon * direction
        positive /= np.linalg.norm(positive, axis=1)[:, None]
        negative /= np.linalg.norm(negative, axis=1)[:, None]
        derivative = (energy_gradient(case, positive)[1] - energy_gradient(case, negative)[1]) / (2 * epsilon)
        derivative[index] -= np.dot(spins[index], origin_gradient[index]) * direction[index]
        result[:, coordinate] = np.einsum("nca,nc->na", basis, derivative).reshape(-1)
    return (result + result.T) / 2
