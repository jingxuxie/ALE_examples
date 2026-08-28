import numpy as np
from scipy.linalg import ordqz, solve
from scipy.special import expit


def fermi(energies, chemical_potential, temperature):
    if temperature == 0:
        return (np.asarray(energies) < chemical_potential).astype(float)
    return expit((chemical_potential - np.asarray(energies)) / temperature)


def surface(energy, cell, hop, eta=1e-9):
    size = len(cell)
    identity = np.eye(size, dtype=complex)
    zeros = np.zeros_like(identity)
    spectral = complex(energy, eta) * identity - cell
    first = np.block([[spectral, -hop], [identity, zeros]])
    second = np.block([[hop.conj().T, zeros], [zeros, identity]])
    schur_first, schur_second, alpha, beta, left, right = ordqz(
        first, second, sort='iuc', output='complex', check_finite=False)
    if np.sum(abs(alpha) < abs(beta)) != size:
        if eta < 1e-6:
            return surface(energy, cell, hop, eta=eta * 10)
        raise np.linalg.LinAlgError('retarded invariant-subspace dimension mismatch')
    upper, lower = right[:size, :size], right[size:, :size]
    transfer = solve(lower.T, upper.T, check_finite=False).T
    return solve(spectral - hop.conj().T @ transfer, identity, check_finite=False)


def band_samples(cell, hop, count=257):
    momenta = np.linspace(-np.pi, np.pi, count)
    values = [np.linalg.eigvalsh(cell + np.exp(-1j * momentum) * hop + np.exp(1j * momentum) * hop.conj().T) for momentum in momenta]
    return momenta, np.asarray(values)
