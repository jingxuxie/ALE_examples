"""Real-axis outgoing subspaces for singular periodic lead couplings."""

import warnings

import numpy as np
import scipy.linalg as la
import scipy.sparse as sp
from scipy.sparse.csgraph import structural_rank


def _outgoing_subspace(pencil, metric, tolerance=1e-7):
    """Keep decaying Schur vectors and positive-current propagating modes."""
    first, second = pencil
    half = first.shape[0] // 2

    def decaying(alpha, beta):
        return np.abs(alpha) < (1.0 - tolerance) * np.abs(beta)

    schur = la.get_lapack_funcs("gges", (first, second))
    workspace = schur(decaying, first, second, jobvsl=0, jobvsr=1,
                      sort_t=1, lwork=-1)[-2]
    decomposition = schur(
        decaying, first, second, jobvsl=0, jobvsr=1, sort_t=1,
        lwork=int(workspace[0].real), overwrite_a=1, overwrite_b=1)
    schur_first, schur_second, decay_count, alpha, beta, unused_left, right = decomposition[:7]
    if decomposition[-1] != 0:
        raise la.LinAlgError("Lead generalized Schur decomposition failed")
    del unused_left
    unit = np.abs(np.abs(alpha) - np.abs(beta)) <= tolerance * np.abs(beta)
    unit &= np.abs(beta) > 0
    propagating_count = int(np.count_nonzero(unit))
    if 2 * decay_count + propagating_count != 2 * half:
        raise la.LinAlgError("Unresolved reciprocal pairs in the lead pencil")
    if not propagating_count:
        return right[:, :half], 0

    selected = np.asarray(decaying(alpha, beta) | unit, dtype=np.int32)
    reorder = la.get_lapack_funcs("tgsen", (schur_first,))
    left = np.empty_like(schur_first)
    reordered = reorder(
        selected, schur_first, schur_second, left, right, ijob=0,
        wantq=0, wantz=1, overwrite_a=1, overwrite_b=1,
        overwrite_q=1, overwrite_z=1)
    schur_first, schur_second, alpha, beta, left, right = reordered[:6]
    if reordered[-1] != 0:
        raise la.LinAlgError("Unable to separate propagating lead modes")

    start, stop = decay_count, decay_count + propagating_count
    values, vectors = la.eig(
        schur_first[start:stop, start:stop],
        schur_second[start:stop, start:stop], check_finite=False)
    extension = np.empty((decay_count, propagating_count), dtype=complex)
    if decay_count:
        for index, value in enumerate(values):
            forcing = -(schur_first[:start, start:stop]
                        - value * schur_second[:start, start:stop]) @ vectors[:, index]
            extension[:, index] = la.solve_triangular(
                schur_first[:start, :start] - value * schur_second[:start, :start],
                forcing, check_finite=False)
    modes = right[:, :start] @ extension + right[:, start:stop] @ vectors
    modes /= np.linalg.norm(modes, axis=0)

    unused = np.ones(propagating_count, dtype=bool)
    outgoing = []
    for index in range(propagating_count):
        if not unused[index]:
            continue
        group = np.flatnonzero(unused & (np.abs(values - values[index]) < 1e-8))
        unused[group] = False
        group_modes = modes[:, group]
        current = metric(group_modes)
        velocities, rotation = la.eigh((current + current.conj().T) * 0.5,
                                       check_finite=False)
        outgoing.append(group_modes @ rotation[:, velocities > 0])
    outgoing = np.hstack(outgoing)
    mode_count = outgoing.shape[1]
    if decay_count + mode_count != half:
        raise la.LinAlgError("Unbalanced incoming and outgoing lead currents")
    return np.hstack((right[:, :decay_count], outgoing)), mode_count


class PeriodicLead:
    """An ordered layer with exact-support and structural-nullspace reduction."""

    def __init__(self, onsite, coupling):
        self.onsite = np.asarray(onsite, dtype=complex)
        self.coupling = np.asarray(coupling, dtype=complex)
        self.size = len(onsite)
        self.active = np.flatnonzero(np.any(coupling != 0, axis=0))
        nonzero_rows = np.flatnonzero(np.any(coupling != 0, axis=1))
        if len(nonzero_rows) <= len(self.active):
            self.left_factor = np.eye(self.size, dtype=complex)[:, nonzero_rows]
            self.right_factor = coupling[nonzero_rows, :].conj().T.copy()
        else:
            self.left_factor = coupling[:, self.active].copy()
            self.right_factor = np.eye(self.size, dtype=complex)[:, self.active]
        self.rank_bound = self.left_factor.shape[1]
        support = coupling[np.ix_(nonzero_rows, self.active)]
        structural_bound = structural_rank(sp.csr_matrix(support))
        if structural_bound < self.rank_bound:
            left, strengths, right = la.svd(support, full_matrices=False,
                                            check_finite=False)
            roots = np.sqrt(strengths[:structural_bound])
            self.left_factor = np.zeros((self.size, structural_bound), complex)
            self.right_factor = np.zeros((self.size, structural_bound), complex)
            self.left_factor[nonzero_rows] = left[:, :structural_bound] * roots
            self.right_factor[self.active] = right[:structural_bound].conj().T * roots
            self.rank_bound = structural_bound
        elif self.rank_bound:
            scaling = np.sqrt(np.linalg.norm(self.right_factor, axis=0)
                              / np.linalg.norm(self.left_factor, axis=0))
            self.left_factor *= scaling
            self.right_factor /= scaling
        self.active_right = self.right_factor[self.active, :]
        self.active_coupling = self.coupling[:, self.active]

    def _compressed(self, energy):
        rank = self.rank_bound
        inverse_onsite = la.solve(
            energy * np.eye(self.size) - self.onsite,
            np.hstack((self.left_factor, self.right_factor)),
            assume_a="her", check_finite=False)
        inverse_left = inverse_onsite[:, :rank]
        inverse_right = inverse_onsite[:, rank:]
        left_adjoint = self.left_factor.conj().T
        right_adjoint = self.right_factor.conj().T
        left_left = left_adjoint @ inverse_left
        left_right = left_adjoint @ inverse_right
        right_left = right_adjoint @ inverse_left
        right_right = right_adjoint @ inverse_right
        first = np.block([[right_left, np.zeros((rank, rank))],
                          [-left_left, np.eye(rank)]])
        second = np.block([[np.eye(rank), -right_right],
                           [np.zeros((rank, rank)), left_right]])

        def metric(vectors):
            product = vectors[:rank].conj().T @ vectors[rank:]
            return 1j * (product - product.conj().T)

        subspace, count = _outgoing_subspace((first, second), metric)
        reduced_surface = la.solve(subspace[:rank].T, subspace[rank:].T,
                                   check_finite=False).T
        sigma = self.active_right @ reduced_surface @ self.active_right.conj().T
        return sigma, count

    def _uncompressed(self, energy):
        size = self.size
        identity = np.eye(size)
        first = np.block([[energy * identity - self.onsite, -self.coupling],
                          [identity, np.zeros((size, size))]])
        second = la.block_diag(self.coupling.conj().T, identity)

        def metric(vectors):
            product = vectors[size:].conj().T @ self.coupling.conj().T @ vectors[:size]
            return 1j * (product - product.conj().T)

        subspace, count = _outgoing_subspace((first, second), metric)
        transfer_active = la.solve(subspace[size:].T,
                                   subspace[:size, :].T, check_finite=False).T
        sigma = self.active_coupling.conj().T @ transfer_active[:, self.active]
        return sigma, count

    def _residual(self, energy, sigma):
        operator = energy * np.eye(self.size, dtype=complex) - self.onsite
        operator[np.ix_(self.active, self.active)] -= sigma
        propagated = la.solve(operator, self.active_coupling, check_finite=False)
        defect = sigma - self.active_coupling.conj().T @ propagated
        return la.norm(defect) / max(1.0, la.norm(sigma))

    def selfenergy(self, energy):
        """Return the retarded selfenergy and a flux-channel factor of Gamma."""
        if not self.rank_bound:
            return np.zeros((0, 0), complex), np.zeros((0, 0), complex), 0
        with warnings.catch_warnings():
            warnings.simplefilter("error", la.LinAlgWarning)
            try:
                sigma, count = self._compressed(energy)
                if self._residual(energy, sigma) > 2e-8:
                    raise la.LinAlgError("Inaccurate compressed surface resolvent")
            except (la.LinAlgError, la.LinAlgWarning, ValueError):
                sigma, count = self._uncompressed(energy)
        gamma = 1j * (sigma - sigma.conj().T)
        strengths, vectors = la.eigh(gamma, check_finite=False)
        if count:
            factor = vectors[:, -count:] * np.sqrt(np.maximum(strengths[-count:], 0))
        else:
            factor = np.zeros((len(self.active), 0), complex)
        sigma = 0.5 * (sigma + sigma.conj().T) - 0.5j * (factor @ factor.conj().T)
        return sigma, factor, count
