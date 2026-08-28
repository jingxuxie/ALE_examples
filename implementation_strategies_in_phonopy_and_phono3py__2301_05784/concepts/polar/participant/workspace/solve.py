"""Incomplete starter: fixed Cartesian finite differences and diagonal response."""

import resource
import sys
import time

import numpy as np


def matrix_value(data, wavevector):
    atoms = len(data["masses"])
    result = np.zeros((atoms, 3, atoms, 3), dtype=np.complex128)
    phases = np.exp(2j * np.pi * (data["sr_vectors"] @ wavevector))
    blocks = data["sr_blocks"] * phases[:, None, None]
    for row in range(atoms):
        for column in range(atoms):
            selected = (data["sr_i"] == row) & (data["sr_j"] == column)
            result[row, :, column, :] = blocks[selected].sum(axis=0)
    shifted = data["g_vectors"] + wavevector
    denominator = np.einsum("ga,ab,gb->g", shifted, data["dielectric"], shifted)
    weights = np.exp(-denominator / (4 * float(data["ewald_lambda"]) ** 2))
    weights /= denominator
    charge = np.einsum("gb,iba->gia", shifted, data["born"])
    phase = np.exp(2j * np.pi * (data["g_vectors"] @ data["positions"].T))
    charge = charge * phase[:, :, None] / np.sqrt(data["masses"])[None, :, None]
    result += float(data["nac_factor"]) * np.einsum(
        "gia,gjb,g->iajb", charge, charge.conj(), weights, optimize=True
    )
    result = result.reshape(3 * atoms, 3 * atoms)
    return (result + result.conj().T) / 2


def derivative(data):
    step = 1e-5
    answer = []
    for wavevector in data["q_cart"]:
        components = []
        for direction in np.eye(3):
            plus = matrix_value(data, wavevector + step * direction)
            minus = matrix_value(data, wavevector - step * direction)
            components.append((plus - minus) / (2 * step))
        answer.append(components)
    return np.asarray(answer)


def mode_response(data):
    reduced = data["response_ddm_reduced"]
    cartesian = np.einsum("am,paij->pmij", data["cell"], reduced)
    packets, _, modes, _ = cartesian.shape
    response = np.zeros_like(cartesian)
    velocity = np.zeros((packets, len(data["response_directions"]), modes))
    branch_velocity = np.zeros((packets, len(data["response_directions"]), modes, 3))
    factor = float(data["frequency_factor"])
    for packet in range(packets):
        basis = data["response_eigenvectors"][packet]
        diagonal = np.einsum("ia,mij,ja->ma", basis.conj(), cartesian[packet], basis)
        for label in np.unique(data["response_groups"][packet]):
            indices = np.flatnonzero(data["response_groups"][packet] == label)
            if not data["response_active"][packet, indices[0]]:
                continue
            eigenvalue = data["response_eigenvalues"][packet, indices].mean()
            values = diagonal[:, indices].real * factor / (2 * np.sqrt(eigenvalue))
            for local, index in enumerate(indices):
                response[packet, :, index, index] = values[:, local]
            directional = data["response_directions"] @ values
            for direction in range(len(directional)):
                velocity[packet, direction, indices] = np.sort(directional[direction])
                ordering = np.argsort(directional[direction])
                branch_velocity[packet, direction, indices] = values[:, ordering].T
    return response, velocity, branch_velocity


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: python solve.py INPUT.npz OUTPUT.npz")
    with np.load(sys.argv[1], allow_pickle=False) as archive:
        data = dict(archive)
    started = time.perf_counter()
    ddm = derivative(data)
    derivative_seconds = time.perf_counter() - started
    derivative_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    started = time.perf_counter()
    response, velocity, branch_velocity = mode_response(data)
    response_seconds = time.perf_counter() - started
    np.savez_compressed(
        sys.argv[2], derivative=ddm, response=response, velocity=velocity,
        branch_velocity=branch_velocity,
        derivative_seconds=derivative_seconds, response_seconds=response_seconds,
        derivative_cumulative_max_rss_kb=derivative_rss,
        response_cumulative_max_rss_kb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    )


if __name__ == "__main__":
    main()
