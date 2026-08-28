#!/usr/bin/env python3
"""Bulk complex-band decay and variational finite-device end localization."""

import os

for thread_variable in (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[thread_variable] = "1"

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import scipy.linalg as linalg


def quadratic_pencil(onsite, hopping):
    """Linearize (T*z**2 + H*z + T.conj().T) psi = 0."""
    dimension = onsite.shape[0]
    scale = max(linalg.norm(onsite, np.inf), linalg.norm(hopping, np.inf))
    if scale == 0:
        raise ValueError("The bulk Hamiltonian has no finite decay length")
    matrix_a = np.zeros((2 * dimension, 2 * dimension), dtype=np.complex128)
    matrix_b = np.zeros_like(matrix_a)
    matrix_a[:dimension, :dimension] = -onsite / scale
    matrix_a[:dimension, dimension:] = -hopping.conj().T / scale
    matrix_a[dimension:, :dimension] = np.eye(dimension)
    matrix_b[:dimension, :dimension] = hopping / scale
    matrix_b[dimension:, dimension:] = np.eye(dimension)
    return matrix_a, matrix_b


def reduced_pencil(onsite, left_factor, right_factor):
    """Eliminate the cell interior for T = left_factor @ right_factor.H.

    For a = right_factor.H @ psi and b = left_factor.H @ psi / z,
    psi = -H**(-1) @ (z * left_factor @ a + right_factor @ b).
    Projecting this identity gives a pencil of size twice rank(T),
    irrespective of how many original slices were grouped into a cell.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("error", linalg.LinAlgWarning)
        factorization, pivots = linalg.lu_factor(onsite, check_finite=False)
        condition_estimator = linalg.get_lapack_funcs("gecon", (factorization,))
        reciprocal_condition, info = condition_estimator(
            factorization, linalg.norm(onsite, 1)
        )
        if info != 0 or reciprocal_condition < 1e-10:
            raise linalg.LinAlgError("Cell interior is too close to singular")
        inverse_factors = linalg.lu_solve(
            (factorization, pivots),
            np.column_stack((left_factor, right_factor)),
            check_finite=False,
        )
    rank = left_factor.shape[1]
    inverse_left = inverse_factors[:, :rank]
    inverse_right = inverse_factors[:, rank:]
    cross = right_factor.conj().T @ inverse_left
    right_block = right_factor.conj().T @ inverse_right
    left_block = left_factor.conj().T @ inverse_left
    reverse_cross = left_factor.conj().T @ inverse_right
    identity = np.eye(rank)
    zeros = np.zeros((rank, rank), dtype=np.complex128)
    matrix_a = np.block([[-identity, -right_block], [zeros, -reverse_cross]])
    matrix_b = np.block([[cross, zeros], [left_block, identity]])
    return matrix_a, matrix_b


def bulk_amplitude_length(onsite, hopping, cell_length_nm):
    """Return -d/log(|z|) for the slowest nonzero right-decaying mode."""
    onsite = np.asarray(onsite, dtype=np.complex128)
    hopping = np.asarray(hopping, dtype=np.complex128)
    left_vectors, singular_values, right_adjoint = linalg.svd(
        hopping, full_matrices=False, check_finite=False
    )
    threshold = hopping.shape[0] * np.finfo(float).eps * singular_values[0]
    rank = int(np.count_nonzero(singular_values > threshold))
    if rank == 0:
        raise ValueError("No nonzero exponentially decaying bulk modes")
    pencil = None
    if rank < hopping.shape[0]:
        root_singular_values = np.sqrt(singular_values[:rank])
        left_factor = left_vectors[:, :rank] * root_singular_values
        right_factor = right_adjoint[:rank].conj().T * root_singular_values
        try:
            pencil = reduced_pencil(onsite, left_factor, right_factor)
        except (linalg.LinAlgError, linalg.LinAlgWarning):
            pass
    if pencil is None:
        pencil = quadratic_pencil(onsite, hopping)
    homogeneous = linalg.eigvals(
        *pencil, homogeneous_eigvals=True, overwrite_a=True, check_finite=False
    )
    numerator, denominator = np.abs(homogeneous)
    decaying = (
        np.isfinite(numerator)
        & np.isfinite(denominator)
        & (numerator > 0)
        & (denominator > numerator)
    )
    numerator = numerator[decaying]
    denominator = denominator[decaying]
    if numerator.size == 0:
        raise ValueError("No finite right-decaying bulk modes were found")
    attenuation = np.log(denominator) - np.log(numerator)
    near_unit_circle = numerator > 0.5 * denominator
    attenuation[near_unit_circle] = -np.log1p(
        (numerator[near_unit_circle] - denominator[near_unit_circle])
        / denominator[near_unit_circle]
    )
    length = float(cell_length_nm / np.min(attenuation))
    if not np.isfinite(length) or length <= 0:
        raise ValueError("Invalid bulk amplitude decay length")
    return length


def fit_amplitude_length(coordinates, density):
    """Apply the specified, unsmoothed second-quarter density-log OLS fit."""
    quarter = len(coordinates) // 4
    selection = slice(quarter, 2 * quarter)
    selected_density = density[selection]
    if quarter < 2 or np.any(selected_density <= 0):
        raise ValueError("The fit window must contain positive densities")
    centered_x = coordinates[selection] - np.mean(coordinates[selection])
    log_density = np.log(selected_density)
    slope = np.dot(centered_x, log_density - np.mean(log_density)) / np.dot(
        centered_x, centered_x
    )
    if not np.isfinite(slope) or slope >= 0:
        raise ValueError("The finite-window density slope must be negative")
    return float(-2 / slope)


def finite_left_end(basis, energy_matrix, orbital_x, coordinates):
    """Minimize position only within the closest-to-zero energy pair."""
    energies, energy_vectors = linalg.eigh(energy_matrix, check_finite=False)
    selected_pair = np.argsort(np.abs(energies), kind="stable")[:2]
    pair = basis @ energy_vectors[:, selected_pair]
    centered_positions = orbital_x - 0.5 * (coordinates[0] + coordinates[-1])
    position_matrix = pair.conj().T @ (centered_positions[:, None] * pair)
    position_matrix = 0.5 * (position_matrix + position_matrix.conj().T)
    _, position_vectors = linalg.eigh(position_matrix, check_finite=False)
    wavefunction = pair @ position_vectors[:, 0]
    density = np.bincount(
        np.searchsorted(coordinates, orbital_x),
        weights=np.abs(wavefunction) ** 2,
        minlength=len(coordinates),
    )
    density /= np.sum(density)
    return {
        "rho_left": density.tolist(),
        "xi_window_nm": fit_amplitude_length(coordinates, density),
    }


def analyze(case, arrays):
    if case["family"] == "bulk_tail":
        return {
            "xi_amplitude_nm": bulk_amplitude_length(
                arrays["onsite"], arrays["hopping"], float(arrays["cell_length_nm"])
            )
        }
    if case["family"] == "finite_end":
        return finite_left_end(
            arrays["basis"],
            arrays["energy_matrix"],
            arrays["x_orbital_nm"],
            arrays["x_grid_nm"],
        )
    raise ValueError(f"Unknown case family: {case['family']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.input / "manifest.json").read_text(encoding="utf-8"))
    predictions = {}
    for case in manifest["cases"]:
        with np.load(args.input / case["file"], allow_pickle=False) as arrays:
            predictions[case["id"]] = analyze(case, arrays)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"schema_version": 1, "predictions": predictions}, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
