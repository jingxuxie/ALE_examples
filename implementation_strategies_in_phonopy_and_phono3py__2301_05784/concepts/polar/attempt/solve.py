#!/usr/bin/env python3
"""Analytic polar lattice derivatives and degenerate-mode response."""

import sys
import time

import numpy as np


def derivative(data):
    """Differentiate the supplied finite Fourier and reciprocal sums exactly."""
    masses = data["masses"]
    atoms = len(masses)
    modes = 3 * atoms
    wavevectors = data["q_cart"]
    answer = np.zeros((len(wavevectors), 3, modes, modes), dtype=np.complex128)

    pair_ids = data["sr_i"] * atoms + data["sr_j"]
    ordering = np.argsort(pair_ids, kind="stable")
    pair_ids = pair_ids[ordering]
    pair_starts = np.concatenate(([0], np.flatnonzero(np.diff(pair_ids)) + 1))
    if len(pair_ids):
        distinct_pairs = pair_ids[pair_starts]
        pair_rows = distinct_pairs // atoms
        pair_columns = distinct_pairs % atoms
    short_vectors = data["sr_vectors"][ordering]
    short_blocks = data["sr_blocks"][ordering]

    reciprocal = data["g_vectors"]
    dielectric = data["dielectric"]
    dielectric_gradient = dielectric + dielectric.T
    gaussian_scale = 1.0 / (4.0 * float(data["ewald_lambda"]) ** 2)
    nac_factor = float(data["nac_factor"])
    charges = (data["born"] / np.sqrt(masses)[:, None, None])
    charges = charges.transpose(1, 0, 2).reshape(3, modes)
    reciprocal_phases = np.exp(2j * np.pi * (reciprocal @ data["positions"].T))
    reciprocal_chunk = max(1, 524288 // max(1, modes))

    for query, wavevector in enumerate(wavevectors):
        result = answer[query]
        if len(pair_ids):
            short_phases = np.exp(2j * np.pi * (short_vectors @ wavevector))
            for component in range(3):
                factors = 2j * np.pi * short_vectors[:, component] * short_phases
                blocks = np.add.reduceat(
                    short_blocks * factors[:, None, None], pair_starts, axis=0
                )
                result[component].reshape(atoms, 3, atoms, 3)[
                    pair_rows, :, pair_columns, :
                ] = blocks
        result[:] = 0.5 * (result + result.conj().swapaxes(-1, -2))

        if nac_factor == 0.0:
            continue
        for start in range(0, len(reciprocal), reciprocal_chunk):
            stop = min(start + reciprocal_chunk, len(reciprocal))
            shifted = reciprocal[start:stop] + wavevector
            denominator = np.sum((shifted @ dielectric) * shifted, axis=1)
            denominator_gradient = shifted @ dielectric_gradient
            weights = np.exp(-gaussian_scale * denominator) / denominator
            charge_values = shifted @ charges
            phases = np.repeat(reciprocal_phases[start:stop], 3, axis=1)
            charge_conjugate = (charge_values * phases).conj()
            weighted_phases = weights[:, None] * phases
            for component in range(3):
                logarithmic_gradient = denominator_gradient[:, component] * (
                    1.0 / denominator + gaussian_scale
                )
                half_gradient = weighted_phases * (
                    charges[component][None, :]
                    - 0.5 * logarithmic_gradient[:, None] * charge_values
                )
                cross = half_gradient.T @ charge_conjugate
                result[component] += nac_factor * (cross + cross.conj().T)
    return answer


def mode_response(data):
    """Project into declared groups and resolve branches separately by direction."""
    reduced = data["response_ddm_reduced"]
    packets, _, modes, _ = reduced.shape
    directions = data["response_directions"]
    response = np.zeros((packets, 3, modes, modes), dtype=np.complex128)
    velocity = np.zeros((packets, len(directions), modes), dtype=np.float64)
    branch_velocity = np.zeros(
        (packets, len(directions), modes, 3), dtype=np.float64
    )
    frequency_factor = float(data["frequency_factor"])
    branch_tolerance = float(data["branch_tolerance"])

    for packet in range(packets):
        basis = data["response_eigenvectors"][packet]
        cartesian = np.einsum("am,aij->mij", data["cell"], reduced[packet])
        projected = basis.conj().T @ cartesian @ basis
        for label in np.unique(data["response_groups"][packet]):
            indices = np.flatnonzero(data["response_groups"][packet] == label)
            if not data["response_active"][packet, indices[0]]:
                continue
            eigenvalue = np.mean(data["response_eigenvalues"][packet, indices])
            normalization = frequency_factor / (2.0 * np.sqrt(eigenvalue))
            block = projected[:, indices[:, None], indices] * normalization
            block = 0.5 * (block + block.conj().swapaxes(-1, -2))
            response[packet][:, indices[:, None], indices] = block

            if len(indices) == 1:
                components = block[:, 0, 0].real
                velocity[packet, :, indices[0]] = directions @ components
                branch_velocity[packet, :, indices[0], :] = components
                continue

            directional = np.einsum("km,mij->kij", directions, block)
            slopes, branches = np.linalg.eigh(directional)
            applied = block[None, :, :, :] @ branches[:, None, :, :]
            components = np.einsum(
                "kib,kmib->kbm", branches.conj(), applied
            ).real
            for direction in range(len(directions)):
                boundaries = np.concatenate(
                    (
                        [0],
                        np.flatnonzero(np.diff(slopes[direction]) > branch_tolerance)
                        + 1,
                        [len(indices)],
                    )
                )
                for begin, end in zip(boundaries[:-1], boundaries[1:]):
                    if end - begin > 1:
                        components[direction, begin:end] = np.mean(
                            components[direction, begin:end], axis=0
                        )
            velocity[packet][:, indices] = slopes
            branch_velocity[packet][:, indices, :] = components

    return response, velocity, branch_velocity


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python solve.py INPUT.npz OUTPUT.npz")
    with np.load(sys.argv[1], allow_pickle=False) as archive:
        data = dict(archive)
    started = time.perf_counter()
    derivatives = derivative(data)
    derivative_seconds = time.perf_counter() - started
    started = time.perf_counter()
    response, velocity, branch_velocity = mode_response(data)
    response_seconds = time.perf_counter() - started
    with open(sys.argv[2], "wb") as output:
        np.savez(
            output,
            derivative=derivatives,
            response=response,
            velocity=velocity,
            branch_velocity=branch_velocity,
            derivative_seconds=derivative_seconds,
            response_seconds=response_seconds,
        )


if __name__ == "__main__":
    main()
