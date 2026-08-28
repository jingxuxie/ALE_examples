#!/usr/bin/env python3
"""Gauge-resolved canonical Hermitian low-energy and weak-field exporter."""

import argparse
from itertools import permutations

import numpy as np
from scipy.linalg import expm
from scipy.optimize import least_squares


KINETIC = 3.809982208629016
BOHR = 0.52917721067
VELOCITY = 2.0 * KINETIC / BOHR


def _real_vector(matrix):
    return np.concatenate((matrix.real.ravel(), matrix.imag.ravel()))


def _complex_matrix(vector, dimension):
    size = dimension * dimension
    return (vector[:size] + 1j * vector[size:]).reshape(dimension, dimension)


def _polar(matrix):
    left, _, right = np.linalg.svd(matrix)
    return left @ right


def _hermitian_generators(dimension):
    generators = []
    for row in range(dimension):
        diagonal = np.zeros((dimension, dimension), dtype=complex)
        diagonal[row, row] = 1.0
        generators.append(diagonal)
        for column in range(row + 1, dimension):
            symmetric = np.zeros_like(diagonal)
            symmetric[row, column] = symmetric[column, row] = 1.0 / np.sqrt(2.0)
            antisymmetric = np.zeros_like(diagonal)
            antisymmetric[row, column] = 1j / np.sqrt(2.0)
            antisymmetric[column, row] = -1j / np.sqrt(2.0)
            generators.extend((symmetric, antisymmetric))
    return np.asarray(generators)


def recover_basis(input_repr, standard_repr, antiunitary):
    """Find a unitary intertwiner, allowing reducible and noisy corepresentations.

    Antiunitary intertwining is real-linear rather than complex-linear. Polar
    factors of invertible exact intertwiners are themselves intertwiners. Small
    singular-vector subspaces provide seeds without assuming a kernel dimension;
    constrained least squares then accommodates representation rounding errors.
    """
    dimension = input_repr.shape[-1]
    identity = np.eye(dimension, dtype=complex)
    if len(input_repr) == 0:
        return identity

    def residual(matrix):
        transformed = np.where(antiunitary[:, None, None], matrix.conj(), matrix)
        return _real_vector(input_repr @ transformed - matrix @ standard_repr)

    identity_residual = residual(identity)
    exact_tolerance = 1e-12 * max(1.0, np.sqrt(len(input_repr) * dimension))
    if np.linalg.norm(identity_residual) <= exact_tolerance:
        return identity

    matrix_units = np.eye(dimension * dimension).reshape(-1, dimension, dimension)
    real_units = np.concatenate((matrix_units, 1j * matrix_units))
    operator = np.column_stack([residual(unit) for unit in real_units])
    _, _, right = np.linalg.svd(operator, full_matrices=False)
    small_modes = right[::-1].T
    identity_vector = _real_vector(identity)
    random = np.random.default_rng(1847)
    candidates = [(float(identity_residual @ identity_residual), identity)]

    for count in range(1, small_modes.shape[1] + 1):
        subspace = small_modes[:, :count]
        coefficients = [subspace.T @ identity_vector]
        coefficients.extend(random.normal(size=count) for _ in range(4))
        for coefficient in coefficients:
            vector = subspace @ coefficient
            if np.linalg.norm(vector) < 1e-14:
                continue
            candidate = _polar(_complex_matrix(vector, dimension))
            error = residual(candidate)
            score = float(error @ error)
            if score <= exact_tolerance**2:
                return candidate
            candidates.append((score, candidate))

    candidates.sort(key=lambda candidate: candidate[0])
    best_score, best_basis = candidates[0]
    generators = _hermitian_generators(dimension)
    for _, initial in candidates[:3]:
        def parameterized_basis(parameters):
            hermitian = np.tensordot(parameters, generators, axes=(0, 0))
            return initial @ expm(1j * hermitian)

        solution = least_squares(
            lambda parameters: residual(parameterized_basis(parameters)),
            np.zeros(dimension * dimension),
            jac="3-point",
            ftol=5e-13,
            xtol=5e-13,
            gtol=5e-13,
            max_nfev=100,
        )
        candidate = parameterized_basis(solution.x)
        error = residual(candidate)
        score = float(error @ error)
        if score < best_score:
            best_score, best_basis = score, candidate
        if best_score <= exact_tolerance**2:
            break
    return _polar(best_basis)


def _hermitize(tensor):
    return 0.5 * (tensor + tensor.swapaxes(-1, -2).conj())


def _standard_tensor(tensor, basis):
    """Transform matrix indices, then move leading Cartesian indices to the end."""
    transformed = _hermitize(basis.conj().T @ tensor @ basis)
    return np.moveaxis(transformed, (-2, -1), (0, 1)).astype(complex, copy=False)


def export(case):
    """Return U, H0 through H3, and G in the NPZ contract's conventions."""
    energy = np.asarray(case["energy"], dtype=float)
    momentum = np.asarray(case["momentum"], dtype=complex)
    selected = np.asarray(case["target"], dtype=int)
    spin = np.asarray(case["spin"], dtype=complex)
    input_repr = np.asarray(case["dft_repr"], dtype=complex)
    standard_repr = np.asarray(case["standard_repr"], dtype=complex)
    antiunitary = np.asarray(case["antiunitary"], dtype=bool)
    order = int(np.asarray(case["order"]).item())
    dimension = len(selected)
    bands = len(energy)

    if energy.ndim != 1 or momentum.shape != (3, bands, bands):
        raise ValueError("energy and momentum have incompatible shapes")
    if selected.ndim != 1 or dimension == 0:
        raise ValueError("target must be a nonempty one-dimensional array")
    if len(np.unique(selected)) != dimension or np.any((selected < 0) | (selected >= bands)):
        raise ValueError("target must contain distinct valid band indices")
    if spin.shape != (3, dimension, dimension):
        raise ValueError("spin must use the target basis and have shape (3,d,d)")
    if input_repr.shape != (len(antiunitary), dimension, dimension):
        raise ValueError("dft_repr must have shape (g,d,d)")
    if standard_repr.shape != input_repr.shape or antiunitary.ndim != 1:
        raise ValueError("incompatible symmetry generator arrays")
    if order not in (2, 3):
        raise ValueError("order must be 2 or 3")
    for name, array in (("energy", energy), ("momentum", momentum), ("spin", spin),
                        ("dft_repr", input_repr), ("standard_repr", standard_repr)):
        if not np.all(np.isfinite(array)):
            raise ValueError(f"{name} contains nonfinite entries")

    basis = recover_basis(input_repr, standard_repr, antiunitary)
    remote_mask = np.ones(bands, dtype=bool)
    remote_mask[selected] = False
    remote = np.flatnonzero(remote_mask)
    gaps = energy[selected][None, :] - energy[remote][:, None]
    if np.any(gaps == 0.0):
        raise ValueError("A target band is degenerate with a remote band; enlarge the target space")
    inverse_gaps = 1.0 / gaps

    linear_pp = VELOCITY * momentum[:, selected[:, None], selected[None, :]]
    linear_qp = VELOCITY * momentum[:, remote[:, None], selected[None, :]]
    linear_pq = VELOCITY * momentum[:, selected[:, None], remote[None, :]]
    wave_first = linear_qp * inverse_gaps[None, :, :]

    ordered_second = 0.5 * (
        np.einsum("aim,bmj->abij", linear_pq, wave_first, optimize=True)
        + np.einsum("ami,bmj->abij", wave_first.conj(), linear_qp, optimize=True)
    )
    quadratic = 0.5 * (ordered_second + ordered_second.swapaxes(0, 1))
    quadratic += KINETIC * np.einsum("ab,ij->abij", np.eye(3), np.eye(dimension))

    zeeman = spin.copy()
    for axis, (first, second) in enumerate(((1, 2), (2, 0), (0, 1))):
        zeeman[axis] -= 0.5j / KINETIC * (
            ordered_second[first, second] - ordered_second[second, first]
        )

    cubic = np.zeros((3, 3, 3, dimension, dimension), dtype=complex)
    if order == 3 and len(remote):
        wave_second = np.empty((3, 3, len(remote), dimension), dtype=complex)
        for first in range(3):
            linear_qq = VELOCITY * momentum[first][np.ix_(remote, remote)]
            for second in range(3):
                wave_second[first, second] = inverse_gaps * (
                    linear_qq @ wave_first[second] - wave_first[first] @ linear_pp[second]
                )
        directed_cubic = _hermitize(
            np.einsum("aim,bcmj->abcij", linear_pq, wave_second, optimize=True)
        )
        for permutation in permutations(range(3)):
            cubic += directed_cubic.transpose(permutation + (3, 4)) / 6.0

    return {
        "U": basis,
        "H0": _standard_tensor(np.diag(energy[selected]), basis),
        "H1": _standard_tensor(linear_pp, basis),
        "H2": _standard_tensor(quadratic, basis),
        "H3": _standard_tensor(cubic, basis),
        "G": _standard_tensor(zeeman, basis),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="input case NPZ")
    parser.add_argument("--output", required=True, help="output tensor NPZ")
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as archive:
        result = export(archive)
    with open(arguments.output, "wb") as output:
        np.savez_compressed(output, **result)


if __name__ == "__main__":
    main()
