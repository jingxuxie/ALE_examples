#!/usr/bin/env python3
"""Gauge-resolved canonical Hermitian low-energy Hamiltonian exporter."""

import os

for variable in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import itertools

import numpy as np


C = 3.809982208629016
BOHR = 0.52917721067
VELOCITY = 2.0 * C / BOHR


def real_vector(matrix):
    vector = matrix.reshape(-1, order="F")
    return np.concatenate((vector.real, vector.imag))


def complex_matrix(vector, dimension):
    count = dimension * dimension
    return (vector[:count] + 1j * vector[count:]).reshape(
        dimension, dimension, order="F"
    )


def polar_unitary(matrix):
    left, _, right = np.linalg.svd(matrix, full_matrices=False)
    return left @ right


def intertwining_operator(input_repr, standard_repr, antiunitary):
    """Real-linear constraints, including conjugation of antiunitary columns."""
    dimension = input_repr.shape[1]
    identity = np.eye(dimension)
    constraints = []
    for supplied, standard, anti in zip(input_repr, standard_repr, antiunitary):
        left = np.kron(identity, supplied)
        right = np.kron(standard.T, identity)
        difference = left - right
        if anti:
            total = left + right
            block = np.block(
                [[difference.real, total.imag], [difference.imag, -total.real]]
            )
        else:
            block = np.block(
                [[difference.real, -difference.imag],
                 [difference.imag, difference.real]]
            )
        constraints.append(block)
    return np.concatenate(constraints, axis=0)


def hermitian_generators(dimension):
    generators = []
    for row in range(dimension):
        diagonal = np.zeros((dimension, dimension), dtype=complex)
        diagonal[row, row] = 1.0
        generators.append(diagonal)
        for column in range(row + 1, dimension):
            symmetric = np.zeros_like(diagonal)
            symmetric[row, column] = 1.0 / np.sqrt(2.0)
            symmetric[column, row] = 1.0 / np.sqrt(2.0)
            generators.append(symmetric)
            antisymmetric = np.zeros_like(diagonal)
            antisymmetric[row, column] = 1j / np.sqrt(2.0)
            antisymmetric[column, row] = -1j / np.sqrt(2.0)
            generators.append(antisymmetric)
    return np.array(generators)


def refine_unitary(unitary, operator, generators):
    """Gauss--Newton refinement on U(d), without relaxing unitarity."""
    residual = operator @ real_vector(unitary)
    score = float(residual @ residual)
    for _ in range(60):
        tangents = unitary @ (1j * generators)
        tangent_vectors = np.stack([real_vector(matrix) for matrix in tangents], axis=1)
        jacobian = operator @ tangent_vectors
        if np.max(np.abs(jacobian.T @ residual)) < 1e-13:
            break
        step = np.linalg.lstsq(jacobian, -residual, rcond=1e-7)[0]
        step_norm = np.linalg.norm(step)
        if step_norm < 1e-13:
            break
        step /= max(1.0, step_norm)
        generator = np.einsum("a,aij->ij", step, generators)
        eigenvalues, eigenvectors = np.linalg.eigh(generator)
        accepted = False
        for backtrack in range(14):
            fraction = 0.5 ** backtrack
            increment = (eigenvectors * np.exp(1j * fraction * eigenvalues)) @ eigenvectors.conj().T
            candidate = unitary @ increment
            candidate_residual = operator @ real_vector(candidate)
            candidate_score = float(candidate_residual @ candidate_residual)
            if candidate_score < score:
                improvement = score - candidate_score
                unitary = candidate
                residual = candidate_residual
                score = candidate_score
                accepted = True
                break
        if not accepted or improvement < 1e-14 * max(score, 1e-24):
            break
    return unitary, score


def recover_basis(input_repr, standard_repr, antiunitary):
    """Find an admissible intertwining unitary, allowing reducible coreps."""
    dimension = input_repr.shape[1]
    identity = np.eye(dimension, dtype=complex)
    if len(input_repr) == 0:
        return identity
    operator = intertwining_operator(input_repr, standard_repr, antiunitary)
    identity_residual = operator @ real_vector(identity)
    identity_score = float(identity_residual @ identity_residual)
    if identity_score < 1e-26:
        return identity
    _, _, right = np.linalg.svd(operator, full_matrices=False)
    modes = right.T[:, ::-1]
    candidates = [(identity_score, identity)]
    random = np.random.default_rng(1729)
    for count in range(1, modes.shape[1] + 1):
        for _ in range(1 if count == 1 else 4):
            vector = modes[:, :count] @ random.normal(size=count)
            unitary = polar_unitary(complex_matrix(vector, dimension))
            residual = operator @ real_vector(unitary)
            candidates.append((float(residual @ residual), unitary))
    candidates.sort(key=lambda candidate: candidate[0])
    best_score, best_unitary = candidates[0]
    if best_score < 1e-25:
        return best_unitary
    generators = hermitian_generators(dimension)
    for _, unitary in candidates[:4]:
        unitary, score = refine_unitary(unitary, operator, generators)
        if score < best_score:
            best_score, best_unitary = score, unitary
    return best_unitary


def effective_tensors(energy, momentum, spin, target, order):
    """Canonical block-unitary reduction in the supplied selected-band basis."""
    dimension = len(target)
    mask = np.ones(len(energy), dtype=bool)
    mask[target] = False
    remote = np.flatnonzero(mask)
    gaps = energy[target][None, :] - energy[remote][:, None]
    if np.any(gaps == 0):
        raise ValueError(
            "A selected band is degenerate with a remote band; "
            "the retained subspace must include the entire degenerate multiplet."
        )
    inverse_gaps = 1.0 / gaps
    retained_velocity = VELOCITY * momentum[:, target[:, None], target[None, :]]
    coupling = VELOCITY * momentum[:, target[:, None], remote[None, :]]
    first_generator = coupling.conj().transpose(0, 2, 1) * inverse_gaps[None, :, :]

    ordered_second = np.empty((3, 3, dimension, dimension), dtype=complex)
    for first in range(3):
        for second in range(3):
            ordered_second[first, second] = 0.5 * (
                coupling[first] @ first_generator[second]
                + first_generator[first].conj().T @ coupling[second].conj().T
            )
    quadratic = 0.5 * (ordered_second + ordered_second.swapaxes(0, 1))
    for axis in range(3):
        quadratic[axis, axis] += C * np.eye(dimension)

    zeeman = np.array(spin, dtype=complex, copy=True)
    for axis, (first, second) in enumerate(((1, 2), (2, 0), (0, 1))):
        zeeman[axis] += (-0.5j / C) * (
            ordered_second[first, second] - ordered_second[second, first]
        )

    cubic = np.zeros((3, 3, 3, dimension, dimension), dtype=complex)
    if order == 3 and len(remote):
        second_generator = np.empty((3, 3, len(remote), dimension), dtype=complex)
        packed_first = first_generator.transpose(1, 0, 2).reshape(len(remote), 3 * dimension)
        for first in range(3):
            remote_velocity = VELOCITY * momentum[first][np.ix_(remote, remote)]
            remote_product = (remote_velocity @ packed_first).reshape(
                len(remote), 3, dimension
            ).transpose(1, 0, 2)
            second_generator[first] = (
                remote_product - first_generator @ retained_velocity[first]
            ) * inverse_gaps[None, :, :]
        for first, second, third in itertools.product(range(3), repeat=3):
            product = coupling[first] @ second_generator[second, third]
            cubic[first, second, third] = 0.5 * (product + product.conj().T)
        cubic = sum(
            cubic.transpose(permutation + (3, 4))
            for permutation in itertools.permutations(range(3))
        ) / 6.0

    return {
        "H0": np.diag(energy[target]).astype(complex),
        "H1": retained_velocity.transpose(1, 2, 0),
        "H2": quadratic.transpose(2, 3, 0, 1),
        "H3": cubic.transpose(3, 4, 0, 1, 2),
        "G": zeeman.transpose(1, 2, 0),
    }


def export(case):
    energy = np.asarray(case["energy"], dtype=float)
    momentum = np.asarray(case["momentum"], dtype=complex)
    target = np.asarray(case["target"], dtype=int)
    spin = np.asarray(case["spin"], dtype=complex)
    dimension = len(target)
    order = int(case["order"])
    if order not in (2, 3):
        raise ValueError("The requested expansion order must be 2 or 3.")
    if dimension == 0 or len(np.unique(target)) != dimension:
        raise ValueError("The target must be nonempty and contain distinct indices.")
    if np.any(target < 0) or np.any(target >= len(energy)):
        raise ValueError("A target index is outside the full band space.")
    if momentum.shape != (3, len(energy), len(energy)):
        raise ValueError("Momentum must have shape (3, n, n).")
    if spin.shape != (3, dimension, dimension):
        raise ValueError("Spin must have shape (3, d, d).")
    input_repr = np.asarray(case["dft_repr"], dtype=complex)
    standard_repr = np.asarray(case["standard_repr"], dtype=complex)
    antiunitary = np.asarray(case["antiunitary"], dtype=bool)
    if (
        input_repr.shape != (len(antiunitary), dimension, dimension)
        or standard_repr.shape != input_repr.shape
    ):
        raise ValueError("The symmetry representation shapes are inconsistent.")
    unitary = recover_basis(input_repr, standard_repr, antiunitary)
    tensors = effective_tensors(energy, momentum, spin, target, order)
    result = {"U": unitary}
    for name, tensor in tensors.items():
        result[name] = np.einsum(
            "pi,pq...,qj->ij...", unitary.conj(), tensor, unitary, optimize=True
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as archive:
        result = export(dict(archive))
    with open(arguments.output, "wb") as destination:
        np.savez_compressed(destination, **result)


if __name__ == "__main__":
    main()
