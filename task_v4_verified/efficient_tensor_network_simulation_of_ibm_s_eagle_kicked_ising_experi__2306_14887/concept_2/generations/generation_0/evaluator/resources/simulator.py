"""Physical kicked-Ising circuit and layer-compressed, open-boundary MPS."""

import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.linalg import qr, svd


N_SITES = 12
CHIS = (4, 8, 16)
OBSERVABLES = ("magnetization", "zz1", "zz3", "zz6")


def diagonals(n_sites=N_SITES):
    indices = np.arange(1 << n_sites)
    signs = 1 - 2 * ((indices[:, None] >> np.arange(n_sites - 1, -1, -1)) & 1)
    values = {"magnetization": signs.mean(axis=1)}
    for distance in (1, 3, 6):
        values[f"zz{distance}"] = (signs * np.roll(signs, -distance, axis=1)).mean(axis=1)
    phase = np.exp(0.25j * np.pi * np.sum(signs * np.roll(signs, -1, axis=1), axis=1))
    return values, phase


def rx(angle):
    cosine, sine = np.cos(angle / 2), -1j * np.sin(angle / 2)
    return np.array([[cosine, sine], [sine, cosine]], dtype=np.complex128)


def exact_state(angles, n_sites=N_SITES):
    state = np.zeros(1 << n_sites, dtype=np.complex128)
    state[0] = 1
    phase = diagonals(n_sites)[1]
    for angle in angles:
        gate = rx(angle)
        for site in range(n_sites):
            shaped = state.reshape(1 << site, 2, -1)
            state = np.einsum("ab,ibj->iaj", gate, shaped).reshape(-1)
        state *= phase
    return state


def measure(state, n_sites=N_SITES):
    probabilities = np.abs(state) ** 2
    probabilities /= probabilities.sum()
    return {name: float(probabilities @ diagonal) for name, diagonal in diagonals(n_sites)[0].items()}


def entangle_ring(tensors):
    phase_zero, phase_one = np.sqrt(0.5), 1j * np.sqrt(0.5)
    signs = np.array([1, -1])[None, :, None]
    for site in range(len(tensors) - 1):
        left, right = tensors[site], tensors[site + 1]
        tensors[site] = np.concatenate((phase_zero * left, phase_one * signs * left), axis=2)
        tensors[site + 1] = np.concatenate((right, signs * right), axis=0)
    tensors[0] = np.concatenate((phase_zero * tensors[0], phase_one * signs * tensors[0]), axis=2)
    tensors[-1] = np.concatenate((tensors[-1], signs * tensors[-1]), axis=0)
    for site in range(1, len(tensors) - 1):
        tensor = tensors[site]
        left, physical, right = tensor.shape
        expanded = np.zeros((2 * left, physical, 2 * right), dtype=np.complex128)
        expanded[:left, :, :right] = tensor
        expanded[left:, :, right:] = tensor
        tensors[site] = expanded


def canonical_subspace(vectors, count):
    projector = vectors @ vectors.conj().T
    selected = []
    for _ in range(count):
        residual = projector.copy()
        for vector in selected:
            residual -= np.outer(vector, vector.conj())
        diagonal = np.real(np.diag(residual))
        maximum = np.max(diagonal)
        pivot = int(np.flatnonzero(diagonal >= maximum - 1e-10)[0])
        direction = residual[:, pivot].copy()
        for _ in range(2):
            for vector in selected:
                direction -= vector * np.vdot(vector, direction)
        direction /= np.linalg.norm(direction)
        selected.append(direction)
    return np.column_stack(selected)


def compress(tensors, chi):
    for site in range(len(tensors) - 1, 0, -1):
        left, physical, right = tensors[site].shape
        orthogonal, triangular = qr(tensors[site].reshape(left, physical * right).conj().T,
                                    mode="economic", check_finite=False)
        tensors[site] = orthogonal.conj().T.reshape(-1, physical, right)
        tensors[site - 1] = np.tensordot(tensors[site - 1], triangular.conj().T, axes=(2, 0))
    discarded, gaps, tie_breaks = [], [], 0
    for site in range(len(tensors) - 1):
        left, physical, right = tensors[site].shape
        matrix = tensors[site].reshape(left * physical, right)
        vectors, singular, remainder = svd(matrix,
                                           full_matrices=False, check_finite=False,
                                           lapack_driver="gesvd")
        rank = min(chi, max(1, int(np.count_nonzero(singular > 1e-13 * singular[0]))))
        discarded.append(float(np.sum(singular[rank:] ** 2) / np.sum(singular ** 2)))
        if rank < len(singular) and discarded[-1] > 1e-12:
            gaps.append(float((singular[rank - 1] - singular[rank]) / singular[0]))
        start = 0
        while start < rank:
            stop = start + 1
            while stop < len(singular) and singular[start] - singular[stop] < 1e-11 * singular[0]:
                stop += 1
            if stop - start > 1:
                retained_stop = min(stop, rank)
                vectors[:, start:retained_stop] = canonical_subspace(vectors[:, start:stop], retained_stop - start)
                tie_breaks += int(start < rank < stop)
            start = stop
        tensors[site] = vectors[:, :rank].reshape(left, physical, rank)
        transfer = vectors[:, :rank].conj().T @ matrix
        transfer /= np.linalg.norm(transfer)
        tensors[site + 1] = np.tensordot(transfer, tensors[site + 1], axes=(1, 0))
    tensors[-1] /= np.linalg.norm(tensors[-1])
    return discarded, gaps, tie_breaks


def expand_mps(tensors):
    state = tensors[0]
    for tensor in tensors[1:]:
        state = np.tensordot(state, tensor, axes=(-1, 0))
    return state.reshape(-1)


def mps_state(angles, chi, n_sites=N_SITES, return_tensors=False):
    tensors = [np.array([1, 0], dtype=np.complex128).reshape(1, 2, 1) for _ in range(n_sites)]
    discarded, gaps, tie_breaks = [], [], 0
    for angle in angles:
        gate = rx(angle)
        tensors = [np.einsum("ab,ibj->iaj", gate, tensor) for tensor in tensors]
        entangle_ring(tensors)
        layer_discarded, layer_gaps, layer_ties = compress(tensors, chi)
        discarded.extend(layer_discarded)
        gaps.extend(layer_gaps)
        tie_breaks += layer_ties
    diagnostics = {"discarded_sum": float(sum(discarded)),
                   "discarded_max": float(max(discarded, default=0)),
                   "min_truncation_gap": float(min(gaps, default=1)),
                   "tie_breaks": tie_breaks,
                   "max_bond": max(tensor.shape[2] for tensor in tensors)}
    return (tensors if return_tensors else expand_mps(tensors)), diagnostics


def compare(angles, chis=CHIS):
    result = {"exact": measure(exact_state(angles)), "mps": {}, "diagnostics": {}}
    for chi in chis:
        state, diagnostics = mps_state(angles, chi)
        result["mps"][str(chi)] = measure(state)
        result["diagnostics"][str(chi)] = diagnostics
    result["metrics"] = {}
    for observable in OBSERVABLES:
        estimates = [result["mps"][str(chi)][observable] for chi in chis]
        spread = max(abs(estimates[index + 1] - estimates[index]) for index in range(len(chis) - 1))
        error = abs(estimates[-1] - result["exact"][observable])
        result["metrics"][observable] = {"spread": spread, "error": error,
                                         "overconfidence": error / max(spread, 1e-4)}
    return result
