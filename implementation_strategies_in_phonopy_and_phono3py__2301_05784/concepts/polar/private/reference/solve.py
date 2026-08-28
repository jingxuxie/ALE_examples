"""Private exported-model solution, validated against the pinned upstream oracle."""

import resource
import sys
import time

import numpy as np


def derivative(data):
    atoms = len(data["masses"])
    mass_root = np.sqrt(data["masses"])
    phase = np.exp(2j * np.pi * (data["g_vectors"] @ data["positions"].T))
    born = data["born"] / mass_root[:, None, None]
    answer = []
    for wavevector in data["q_cart"]:
        result = np.zeros((3, atoms, 3, atoms, 3), dtype=np.complex128)
        phases = np.exp(2j * np.pi * (data["sr_vectors"] @ wavevector))
        coefficients = 2j * np.pi * data["sr_vectors"] * phases[:, None]
        for row in range(atoms):
            for column in range(atoms):
                selected = (data["sr_i"] == row) & (data["sr_j"] == column)
                result[:, row, :, column, :] = np.einsum(
                    "tm,tab->mab", coefficients[selected], data["sr_blocks"][selected]
                )
        shifted = data["g_vectors"] + wavevector
        dielectric_q = shifted @ data["dielectric"].T
        denominator = np.sum(shifted * dielectric_q, axis=1)
        scale = 4 * float(data["ewald_lambda"]) ** 2
        gaussian = np.exp(-denominator / scale)
        charge = np.einsum("gb,iba->gia", shifted, born) * phase[:, :, None]
        for axis in range(3):
            differentiated_charge = phase[:, :, None] * born[None, :, axis, :]
            part = np.einsum(
                "gia,gjb,g->iajb", differentiated_charge, charge.conj(),
                gaussian / denominator, optimize=True,
            )
            part += np.einsum(
                "gia,gjb,g->iajb", charge, differentiated_charge.conj(),
                gaussian / denominator, optimize=True,
            )
            weight = -2 * dielectric_q[:, axis] * gaussian * (
                1 / denominator ** 2 + 1 / (scale * denominator)
            )
            part += np.einsum("gia,gjb,g->iajb", charge, charge.conj(), weight, optimize=True)
            result[axis] += float(data["nac_factor"]) * part
        result = result.reshape(3, 3 * atoms, 3 * atoms)
        answer.append((result + result.conj().transpose(0, 2, 1)) / 2)
    return np.asarray(answer)


def mode_response(data):
    cartesian = np.einsum("am,paij->pmij", data["cell"], data["response_ddm_reduced"])
    response = np.zeros_like(cartesian)
    packets, _, modes, _ = response.shape
    velocity = np.zeros((packets, len(data["response_directions"]), modes))
    branch_velocity = np.zeros((packets, len(data["response_directions"]), modes, 3))
    for packet in range(packets):
        for label in np.unique(data["response_groups"][packet]):
            indices = np.flatnonzero(data["response_groups"][packet] == label)
            if not data["response_active"][packet, indices[0]]:
                continue
            basis = data["response_eigenvectors"][packet][:, indices]
            eigenvalue = data["response_eigenvalues"][packet, indices].mean()
            block = basis.conj().T @ cartesian[packet] @ basis
            block *= float(data["frequency_factor"]) / (2 * np.sqrt(eigenvalue))
            block = (block + block.conj().transpose(0, 2, 1)) / 2
            for axis in range(3):
                response[packet, axis][np.ix_(indices, indices)] = block[axis]
            for direction, vector in enumerate(data["response_directions"]):
                slopes, selected_basis = np.linalg.eigh(
                    np.einsum("m,mij->ij", vector, block)
                )
                velocity[packet, direction, indices] = slopes
                values = np.diagonal(selected_basis.conj().T @ block @ selected_basis, axis1=1, axis2=2).real.T.copy()
                boundaries = np.flatnonzero(np.diff(slopes) > float(data["branch_tolerance"])) + 1
                for cluster in np.split(np.arange(len(indices)), boundaries):
                    values[cluster] = values[cluster].mean(axis=0)
                branch_velocity[packet, direction, indices] = values
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
