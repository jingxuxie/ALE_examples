"""Embedded Fourier interpolation and gauge-invariant subspace responses."""

import warnings

import numpy as np


def hermitian_part(matrix):
    return (matrix + matrix.conj().swapaxes(-1, -2)) * 0.5


class FourierModel:
    """Fourier transform and analytic derivatives with respect to Cartesian k."""

    def __init__(self, payload):
        self.vectors = np.asarray(payload["rvec"])
        self.cartesian_vectors = self.vectors @ payload["lattice"]
        centers = np.asarray(payload["centers"])
        self.reduced_centers = centers @ np.linalg.inv(payload["lattice"])
        self.center_differences = centers[None, :, :] - centers[:, None, :]
        self.orbital_count = len(centers)
        operators = np.empty((len(self.vectors), 4, len(centers), len(centers)), complex)
        operators[:, 0] = payload["ham"]
        operators[:, 1:] = np.moveaxis(payload["connection"], -1, 1)
        self.coefficients = operators.reshape(len(self.vectors), -1)

    def evaluate(self, point):
        phases = np.exp(2j * np.pi * (self.vectors @ point))
        weights = np.empty((4, len(phases)), complex)
        weights[0] = phases
        weights[1:] = 1j * self.cartesian_vectors.T * phases[None, :]
        transformed = (weights @ self.coefficients).reshape(
            4, 4, self.orbital_count, self.orbital_count
        )
        center_phases = np.exp(2j * np.pi * (self.reduced_centers @ point))
        embedding = center_phases.conj()[:, None] * center_phases[None, :]
        values = transformed[0] * embedding[None, :, :]
        derivatives = transformed[1:] * embedding[None, None, :, :]
        derivatives += (
            1j * np.moveaxis(self.center_differences, -1, 0)[:, None, :, :] * values[None, :, :, :]
        )
        values = hermitian_part(values)
        derivatives = hermitian_part(derivatives)
        return values[0], values[1:], derivatives[:, 0], derivatives[:, 1:]


def point_response(hamiltonian, connection, hamiltonian_derivative, connection_derivative, occupied):
    """Trace curvature and the full complex I-to-J transition kernel."""
    energies, eigenvectors = np.linalg.eigh(hamiltonian)
    eigenvectors_adjoint = eigenvectors.conj().T
    connection_eigenbasis = eigenvectors_adjoint @ connection @ eigenvectors
    derivative_eigenbasis = eigenvectors_adjoint @ hamiltonian_derivative @ eigenvectors
    external_connection = connection_eigenbasis[:, :occupied, occupied:]
    gaps = energies[None, occupied:] - energies[:occupied, None]
    tolerance = 64 * np.finfo(float).eps * max(1.0, float(np.max(np.abs(energies))))
    regular = np.abs(gaps) > tolerance
    if not np.all(regular):
        warnings.warn(
            "The occupied boundary cuts a numerically degenerate eigenspace; "
            "its Berry response is not uniquely defined. Using zero inverse "
            "for unresolved cross-boundary gaps (no broadening).",
            RuntimeWarning,
        )
    eigenvector_derivative = np.zeros_like(external_connection)
    np.divide(
        derivative_eigenbasis[:, :occupied, occupied:], gaps[None, :, :],
        out=eigenvector_derivative, where=regular[None, :, :],
    )
    transition = external_connection + 1j * eigenvector_derivative
    optical = 1j * np.einsum("anm,bnm->ab", transition, transition.conj())
    occupied_vectors = eigenvectors[:, :occupied]
    berry = np.empty(3, float)
    for component, (first, second) in enumerate(((1, 2), (2, 0), (0, 1))):
        curl = connection_derivative[first, second] - connection_derivative[second, first]
        background = np.einsum("ni,nm,mi->", occupied_vectors.conj(), curl, occupied_vectors).real
        pure_eigenvectors = np.sum(
            eigenvector_derivative[first] * eigenvector_derivative[second].conj()
        )
        mixed = np.sum(
            eigenvector_derivative[first] * external_connection[second].conj()
            - eigenvector_derivative[second] * external_connection[first].conj()
        )
        berry[component] = background - 2 * pure_eigenvectors.imag - 2 * mixed.real
    return energies, berry, optical


def responses(payload, occupied):
    model = FourierModel(payload)
    if not 0 <= occupied <= model.orbital_count:
        raise ValueError("occupied must be between zero and the complete orbital count")
    points = np.asarray(payload["query_points"])
    energies = np.empty((len(points), model.orbital_count), float)
    berry = np.empty((len(points), 3), float)
    optical = np.empty((len(points), 3, 3), complex)
    for index, point in enumerate(points):
        energies[index], berry[index], optical[index] = point_response(*model.evaluate(point), occupied)
    return energies, berry, optical
