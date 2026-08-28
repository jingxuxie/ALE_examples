import numpy as np
from scipy.linalg import eig_banded


def energy_gradient(case, spins):
    spins = np.asarray(spins, dtype=float)
    exchange = np.asarray(case['exchange_meV'])
    anisotropy = np.asarray(case['anisotropy_meV'])
    field = np.asarray(case['field_meV'])
    tensor_spins = np.einsum('nij,nj->ni', anisotropy, spins)
    energy = -np.sum(exchange * np.sum(spins[:-1] * spins[1:], axis=1))
    energy -= np.sum(spins * tensor_spins + spins * field)
    gradient = -2 * tensor_spins - field
    gradient[:-1] -= exchange[:, None] * spins[1:]
    gradient[1:] -= exchange[:, None] * spins[:-1]
    return float(energy), gradient


def tangent_basis(spins):
    axes = np.eye(3)[np.argmin(np.abs(spins), axis=1)]
    first = np.cross(spins, axes)
    first /= np.linalg.norm(first, axis=1)[:, None]
    second = np.cross(spins, first)
    return np.stack((first, second), axis=2)


def tangent_bands(case, spins):
    count = len(spins)
    basis = tangent_basis(spins)
    _, gradient = energy_gradient(case, spins)
    tensors = np.asarray(case['anisotropy_meV'])
    diagonal = -2 * np.einsum('nca,ncd,ndb->nab', basis, tensors, basis)
    diagonal -= np.sum(spins * gradient, axis=1)[:, None, None] * np.eye(2)
    neighbor = -np.asarray(case['exchange_meV'])[:, None, None] * np.einsum('nca,ncb->nab', basis[:-1], basis[1:])
    bands = np.zeros((4, 2 * count))
    bands[0, 0::2] = diagonal[:, 0, 0]
    bands[0, 1::2] = diagonal[:, 1, 1]
    bands[1, 0::2] = diagonal[:, 1, 0]
    bands[1, 1:-2:2] = neighbor[:, 1, 0]
    bands[2, 0:-2:2] = neighbor[:, 0, 0]
    bands[2, 1:-2:2] = neighbor[:, 1, 1]
    bands[3, 0:-2:2] = neighbor[:, 0, 1]
    return bands


def diagnostics(case, spins):
    spins = np.asarray(spins, dtype=float)
    energy, gradient = energy_gradient(case, spins)
    projected = gradient - np.sum(gradient * spins, axis=1)[:, None] * spins
    eigenvalues = eig_banded(tangent_bands(case, spins), lower=True,
                            eigvals_only=True, overwrite_a_band=True, check_finite=False)
    return dict(energy_meV=energy,
                residual_meV=float(np.max(np.linalg.norm(projected, axis=1))),
                eigenvalues=eigenvalues,
                negative_modes=int(np.sum(eigenvalues < -1e-6)),
                zero_modes=int(np.sum(np.abs(eigenvalues) <= 1e-6)))


def log_omega0(minimum_eigenvalues, saddle_eigenvalues):
    minimum_eigenvalues = np.asarray(minimum_eigenvalues)
    saddle_eigenvalues = np.asarray(saddle_eigenvalues)
    if np.any(minimum_eigenvalues <= 0) or saddle_eigenvalues[0] >= 0 or np.any(saddle_eigenvalues[1:] <= 0):
        return float('nan')
    return float(0.5 * (np.log(minimum_eigenvalues).sum() - np.log(saddle_eigenvalues[1:]).sum()))
