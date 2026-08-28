"""Embedded Fourier interpolation and spectral-subspace geometric responses."""

import warnings

import numpy as np


def hermitian(matrix):
    return (matrix + matrix.swapaxes(-1, -2).conj()) * 0.5


class FourierModel:
    """Fourier interpolation with Cartesian derivatives and no R truncation."""

    def __init__(self, payload):
        self.lattice = np.asarray(payload["lattice"], dtype=float)
        self.vectors = np.asarray(payload["rvec"])
        self.hopping = np.asarray(payload["ham"], dtype=complex)
        self.connection = np.asarray(payload["connection"], dtype=complex)
        self.centers = np.asarray(payload["centers"], dtype=float)
        self.reduced_centers = self.centers @ np.linalg.inv(self.lattice)
        self.translations = self.vectors @ self.lattice
        self.center_differences = self.centers[None, :, :] - self.centers[:, None, :]

    def at(self, point):
        """Return H, dH[a], A[a], and dA[a,b] = partial_a A_b."""
        cell_phases = np.exp(2j * np.pi * (self.vectors @ point))
        orbital_phases = np.exp(2j * np.pi * (self.reduced_centers @ point))
        embedding = orbital_phases.conj()[:, None] * orbital_phases[None, :]
        hopping = np.einsum("r,rnm->nm", cell_phases, self.hopping) * embedding
        connection = np.einsum("r,rnmb->bnm", cell_phases, self.connection) * embedding
        differentiated_phases = 1j * self.translations.T * cell_phases
        hopping_derivative = (
            np.einsum("ar,rnm->anm", differentiated_phases, self.hopping) * embedding
            + 1j * self.center_differences.transpose(2, 0, 1) * hopping
        )
        connection_derivative = (
            np.einsum("ar,rnmb->abnm", differentiated_phases, self.connection) * embedding
            + 1j * self.center_differences.transpose(2, 0, 1)[:, None, :, :] * connection[None, :, :, :]
        )
        return tuple(hermitian(matrix) for matrix in (
            hopping, hopping_derivative, connection, connection_derivative
        ))


def point_response(hopping, hopping_derivative, connection, connection_derivative, occupied):
    """Use only I--J denominators; degeneracies internal to either space are safe."""
    eigenvalues, eigenvectors = np.linalg.eigh(hopping)
    orbital_count = len(eigenvalues)
    if not 0 <= occupied <= orbital_count:
        raise ValueError("occupied must be between zero and the complete band count")
    filled = eigenvectors[:, :occupied]
    empty = eigenvectors[:, occupied:]
    connection_cross = filled.conj().T @ connection @ empty
    derivative_cross = filled.conj().T @ hopping_derivative @ empty
    gaps = eigenvalues[None, occupied:] - eigenvalues[:occupied, None]
    tolerance = 32 * np.finfo(float).eps * max(1.0, float(np.ptp(eigenvalues)))
    inverse_gaps = np.zeros_like(gaps)
    separated = np.abs(gaps) > tolerance
    if np.any(~separated):
        warnings.warn(
            "The occupied boundary splits an exactly degenerate eigenspace; "
            "its response is not uniquely defined. Using zero inverse gaps "
            "on the unresolved pairs.",
            RuntimeWarning,
        )
    np.divide(1.0, gaps, out=inverse_gaps, where=separated)
    hamiltonian_connection = connection_cross + 1j * derivative_cross * inverse_gaps
    transition = np.einsum("anm,bnm->ab", hamiltonian_connection, hamiltonian_connection.conj())
    connection_transition = np.einsum("anm,bnm->ab", connection_cross, connection_cross.conj())
    optical = 1j * transition
    berry = np.empty(3, dtype=float)
    for component, (first, second) in enumerate(((1, 2), (2, 0), (0, 1))):
        curl = connection_derivative[first, second] - connection_derivative[second, first]
        curl_trace = np.einsum("ni,nm,mi->", filled.conj(), curl, filled).real
        berry[component] = curl_trace - 2 * (transition[first, second] - connection_transition[first, second]).imag
    return eigenvalues, berry, optical


def responses(payload, occupied):
    model = FourierModel(payload)
    query_points = payload["query_points"]
    band_count = payload["ham"].shape[1]
    energies = np.empty((len(query_points), band_count), dtype=float)
    berry = np.empty((len(query_points), 3), dtype=float)
    optical = np.empty((len(query_points), 3, 3), dtype=complex)
    for index, point in enumerate(query_points):
        energies[index], berry[index], optical[index] = point_response(*model.at(point), occupied)
    return energies, berry, optical
