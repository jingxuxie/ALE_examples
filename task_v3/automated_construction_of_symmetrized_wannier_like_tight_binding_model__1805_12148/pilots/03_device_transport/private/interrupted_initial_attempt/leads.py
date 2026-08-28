"""Retarded, real-energy lead modes, including rank-deficient couplings."""

import warnings

import numpy as np
from scipy import linalg


def _flux_modes(values, vectors, rank, flux, tolerance):
    on_circle = np.flatnonzero(np.abs(np.abs(values) - 1.0) < tolerance)
    outgoing = []
    incoming_count = 0
    remaining = list(on_circle)
    while remaining:
        first = remaining.pop(0)
        group = [first]
        for other in remaining[:]:
            if abs(values[other] - values[first]) < 2e-9:
                group.append(other)
                remaining.remove(other)
        modes = vectors[:, group]
        if len(group) > 1:
            modes = linalg.qr(modes, mode="economic", check_finite=False)[0]
        currents = flux(modes)
        velocities, rotation = linalg.eigh(currents, check_finite=False)
        modes = modes @ rotation
        positive = velocities > 0.0
        outgoing.append(modes[:, positive])
        incoming_count += np.count_nonzero(velocities < 0.0)
    if outgoing:
        outgoing = np.concatenate(outgoing, axis=1)
    else:
        outgoing = np.empty((2 * rank, 0), dtype=complex)
    return outgoing, incoming_count


def _outgoing_graph(lhs, rhs, rank, flux):
    homogeneous, vectors = linalg.eig(
        lhs, rhs, check_finite=False, homogeneous_eigvals=True
    )
    alpha, beta = homogeneous
    values = np.full(alpha.shape, complex(np.inf), dtype=complex)
    np.divide(alpha, beta, out=values, where=beta != 0)
    for tolerance in (1e-8, 1e-7, 1e-6):
        decaying = np.abs(alpha) < (1.0 - tolerance) * np.abs(beta)
        outgoing, incoming_count = _flux_modes(
            values, vectors, rank, flux, tolerance
        )
        if np.count_nonzero(decaying) + outgoing.shape[1] == rank:
            if incoming_count == outgoing.shape[1]:
                break
    else:
        raise linalg.LinAlgError("Could not separate incoming and outgoing lead modes")
    basis = np.column_stack((vectors[:, decaying], outgoing))
    upper = basis[:rank]
    lower = basis[rank:]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", linalg.LinAlgWarning)
        factor, pivots = linalg.lu_factor(upper, check_finite=False)
    reciprocal_condition = linalg.lapack.get_lapack_funcs("gecon", (factor,))(
        factor, linalg.norm(upper, 1)
    )[0]
    if reciprocal_condition < 1e-9:
        def select_stable(numerator, denominator):
            return np.abs(numerator) < (1.0 - tolerance) * np.abs(denominator)

        schur = linalg.ordqz(
            lhs, rhs, sort=select_stable, output="complex", check_finite=False
        )
        stable_count = np.count_nonzero(decaying)
        basis = np.column_stack((schur[-1][:, :stable_count], outgoing))
        basis = linalg.qr(basis, mode="economic", check_finite=False)[0]
        upper = basis[:rank]
        lower = basis[rank:]
        factor, pivots = linalg.lu_factor(upper, check_finite=False)
    graph = linalg.lu_solve(
        (factor, pivots), lower.T, trans=1, check_finite=False
    ).T
    return graph, incoming_count


class Lead:
    """A periodic lead with B = H(outward layer, inward layer).

    Factor B = left @ right.H. Eliminating the isolated principal layer
    gives a 2*rank(B) pencil for (right.H psi[m-1], left.H psi[m]).
    Its outgoing graph yields Sigma = right @ graph @ right.H.
    The conserved outward current is -2 Im(x.H y). All mode calculations
    use real E: there is no finite imaginary onsite potential.
    """

    def __init__(self, onsite, coupling):
        self.onsite = np.asarray(onsite, dtype=complex)
        self.coupling = np.asarray(coupling, dtype=complex)
        self.size = len(onsite)
        active_rows = np.flatnonzero(np.any(coupling != 0, axis=1))
        self.active = np.flatnonzero(np.any(coupling != 0, axis=0))
        if not len(self.active):
            self.rank = 0
            return
        left, singular, right_adjoint = linalg.svd(
            coupling[np.ix_(active_rows, self.active)],
            full_matrices=False,
            check_finite=False,
        )
        threshold = np.finfo(float).eps * max(coupling.shape) * singular[0]
        self.rank = np.count_nonzero(singular > threshold)
        root = np.sqrt(singular[:self.rank])
        self.left = np.zeros((self.size, self.rank), dtype=complex)
        self.right = np.zeros_like(self.left)
        self.left[active_rows] = left[:, :self.rank] * root
        self.right[self.active] = right_adjoint[:self.rank].conj().T * root
        self.factors = np.column_stack((self.left, self.right))

    def _reduced(self, energy):
        isolated = -self.onsite.copy()
        isolated.flat[::self.size + 1] += energy
        with warnings.catch_warnings():
            warnings.simplefilter("error", linalg.LinAlgWarning)
            propagated = linalg.solve(
                isolated, self.factors, assume_a="her", check_finite=False
            )
        green_left = propagated[:, :self.rank]
        green_right = propagated[:, self.rank:]
        identity = np.eye(self.rank, dtype=complex)
        zero = np.zeros_like(identity)
        lhs = np.block([
            [self.right.conj().T @ green_left, zero],
            [self.left.conj().T @ green_left, -identity],
        ])
        rhs = np.block([
            [identity, -self.right.conj().T @ green_right],
            [zero, -self.left.conj().T @ green_right],
        ])

        def flux(modes):
            cross = modes[:self.rank].conj().T @ modes[self.rank:]
            return 1j * (cross - cross.conj().T)

        graph, count = _outgoing_graph(lhs, rhs, self.rank, flux)
        return self.right @ graph @ self.right.conj().T, count

    def _full(self, energy):
        identity = np.eye(self.size, dtype=complex)
        zero = np.zeros_like(identity)
        lhs = np.block([
            [zero, identity],
            [-self.coupling, energy * identity - self.onsite],
        ])
        rhs = np.block([[identity, zero], [zero, self.coupling.conj().T]])

        def flux(modes):
            cross = modes[:self.size].conj().T @ (
                self.coupling.conj().T @ modes[self.size:]
            )
            return 1j * (cross - cross.conj().T)

        graph, count = _outgoing_graph(lhs, rhs, self.size, flux)
        return self.coupling.conj().T @ graph, count

    def evaluate(self, energy):
        if self.rank == 0:
            return np.zeros_like(self.onsite), np.empty((self.size, 0), complex), 0
        try:
            sigma, count = self._reduced(energy)
        except (linalg.LinAlgError, linalg.LinAlgWarning, ValueError):
            sigma, count = self._full(energy)
        active_sigma = sigma[np.ix_(self.active, self.active)]
        gamma = 1j * (active_sigma - active_sigma.conj().T)
        weights, vectors = linalg.eigh(gamma, check_finite=False)
        scale = max(1.0, linalg.norm(active_sigma))
        if weights[0] < -1e-7 * scale or (count and weights[-count] <= 0):
            sigma, count = self._full(energy)
            active_sigma = sigma[np.ix_(self.active, self.active)]
            gamma = 1j * (active_sigma - active_sigma.conj().T)
            weights, vectors = linalg.eigh(gamma, check_finite=False)
        injection = np.zeros((self.size, count), dtype=complex)
        if count:
            injection[self.active] = vectors[:, -count:] * np.sqrt(
                np.maximum(weights[-count:], 0.0)
            )
        hermitian = 0.5 * (active_sigma + active_sigma.conj().T)
        active_injection = injection[self.active]
        cleaned = hermitian - 0.5j * (active_injection @ active_injection.conj().T)
        sigma = np.zeros_like(self.onsite)
        sigma[np.ix_(self.active, self.active)] = cleaned
        return sigma, injection, count
