"""Reproducible numerical checks using only public and synthetic data."""

import time
from pathlib import Path

import numpy as np
from scipy.linalg import eigh

from solve import derivative, mode_response


def matrix_value(data, wavevector):
    atoms = len(data["masses"])
    matrix = np.zeros((atoms, 3, atoms, 3), dtype=np.complex128)
    for row, column, displacement, block in zip(
        data["sr_i"], data["sr_j"], data["sr_vectors"], data["sr_blocks"]
    ):
        matrix[row, :, column, :] += block * np.exp(
            2j * np.pi * np.dot(wavevector, displacement)
        )
    shifted = data["g_vectors"] + wavevector
    denominator = np.einsum("gc,cd,gd->g", shifted, data["dielectric"], shifted)
    weights = np.exp(-denominator / (4 * float(data["ewald_lambda"]) ** 2))
    weights /= denominator
    phases = np.exp(
        2j
        * np.pi
        * np.einsum(
            "gc,ijc->gij",
            data["g_vectors"],
            data["positions"][:, None, :] - data["positions"][None, :, :],
        )
    )
    charges = np.einsum("gc,ica->gia", shifted, data["born"])
    polar = np.einsum("gij,gia,gjb,g->iajb", phases, charges, charges, weights)
    polar /= np.sqrt(data["masses"][:, None, None, None])
    polar /= np.sqrt(data["masses"][None, None, :, None])
    matrix += float(data["nac_factor"]) * polar
    matrix = matrix.reshape(3 * atoms, 3 * atoms)
    return (matrix + matrix.conj().T) / 2


def finite_difference(data):
    atoms = len(data["masses"])
    answer = np.zeros((len(data["q_cart"]), 3, 3 * atoms, 3 * atoms), complex)
    for query, wavevector in enumerate(data["q_cart"]):
        distance = np.min(np.linalg.norm(data["g_vectors"] + wavevector, axis=1))
        step = min(1e-4, 3e-4 * distance)
        for component, direction in enumerate(np.eye(3)):
            answer[query, component] = (
                matrix_value(data, wavevector - 2 * step * direction)
                - 8 * matrix_value(data, wavevector - step * direction)
                + 8 * matrix_value(data, wavevector + step * direction)
                - matrix_value(data, wavevector + 2 * step * direction)
            ) / (12 * step)
    return answer


def direct_polar_derivative(data):
    atoms = len(data["masses"])
    reciprocal = data["g_vectors"].astype(np.longdouble)
    positions = data["positions"].astype(np.longdouble)
    born = data["born"].astype(np.longdouble)
    dielectric = data["dielectric"].astype(np.longdouble)
    phases = np.exp(
        2j
        * np.longdouble(np.pi)
        * np.einsum("gc,ijc->gij", reciprocal, positions[:, None] - positions[None])
    )
    scale = 1 / (4 * np.longdouble(data["ewald_lambda"]) ** 2)
    mass_factor = np.sqrt(
        data["masses"].astype(np.longdouble)[:, None]
        * data["masses"].astype(np.longdouble)[None, :]
    )
    answer = np.zeros((len(data["q_cart"]), 3, 3 * atoms, 3 * atoms), complex)
    for query, wavevector in enumerate(data["q_cart"]):
        shifted = reciprocal + wavevector.astype(np.longdouble)
        denominator = np.einsum("gc,cd,gd->g", shifted, dielectric, shifted)
        weights = np.exp(-denominator * scale) / denominator
        charges = np.einsum("gc,ica->gia", shifted, born)
        for component in range(3):
            denominator_gradient = shifted @ (
                dielectric[:, component] + dielectric[component, :]
            )
            weight_gradient = -weights * denominator_gradient * (
                scale + 1 / denominator
            )
            block = np.einsum(
                "gij,ia,gjb,g->iajb", phases, born[:, component], charges, weights
            )
            block += np.einsum(
                "gij,gia,jb,g->iajb", phases, charges, born[:, component], weights
            )
            block += np.einsum(
                "gij,gia,gjb,g->iajb", phases, charges, charges, weight_gradient
            )
            block *= np.longdouble(data["nac_factor"]) / mass_factor[:, None, :, None]
            matrix = block.reshape(3 * atoms, 3 * atoms)
            answer[query, component] = (matrix + matrix.conj().T) / 2
    return answer


def relative_error(actual, expected):
    return np.linalg.norm(actual - expected) / max(np.linalg.norm(expected), 1e-30)


def random_polar_data(generator, atoms=4, reciprocal_radius=2, queries=6, terms=83):
    cell = np.array([[5.1, 0.6, -0.3], [1.1, 4.8, 0.8], [0.3, -0.4, 6.2]])
    integers = np.arange(-reciprocal_radius, reciprocal_radius + 1)
    reciprocal = np.stack(np.meshgrid(integers, integers, integers), axis=-1)
    reciprocal = reciprocal.reshape(-1, 3) @ np.linalg.inv(cell).T
    dielectric_seed = generator.normal(size=(3, 3))
    return {
        "cell": cell,
        "positions": generator.uniform(size=(atoms, 3)) @ cell,
        "masses": generator.uniform(20, 100, size=atoms),
        "born": generator.normal(size=(atoms, 3, 3)),
        "dielectric": dielectric_seed @ dielectric_seed.T + 1.5 * np.eye(3),
        "nac_factor": np.array(3.8),
        "ewald_lambda": np.array(0.31),
        "g_vectors": reciprocal,
        "sr_vectors": generator.normal(size=(terms, 3)) * 4,
        "sr_i": generator.integers(atoms, size=terms),
        "sr_j": generator.integers(atoms, size=terms),
        "sr_blocks": generator.normal(size=(terms, 3, 3))
        + 1j * generator.normal(size=(terms, 3, 3)),
        "q_cart": generator.uniform(-0.15, 0.15, size=(queries, 3)),
    }


def random_unitary(generator, size):
    seed = generator.normal(size=(size, size)) + 1j * generator.normal(size=(size, size))
    return np.linalg.qr(seed)[0]


def response_fixture(generator):
    modes = 12
    groups = np.repeat(np.arange(4), [3, 1, 3, 5])
    eigenvalues = np.repeat([-2.0, 0.8, 4.0, 9.0], [3, 1, 3, 5])
    eigenvalues += np.linspace(-1e-13, 1e-13, modes)
    active = groups != 0
    factor = 7.5
    tolerance = 1e-8
    cell = np.array([[4.3, 0.4, -0.8], [-0.2, 5.2, 0.6], [0.9, 0.3, 6.5]])
    basis = random_unitary(generator, modes)
    projected = generator.normal(size=(3, modes, modes)) + 1j * generator.normal(
        size=(3, modes, modes)
    )
    projected += projected.conj().swapaxes(-1, -2)
    expected = np.zeros_like(projected)
    for label in [1, 2, 3]:
        indices = np.flatnonzero(groups == label)
        size = len(indices)
        block = generator.normal(size=(3, size, size)) + 1j * generator.normal(
            size=(3, size, size)
        )
        block += block.conj().swapaxes(-1, -2)
        if size == 3:
            block[0] = np.diag([1.0, 1.0, 4.0])
        if size == 5:
            slopes = np.array([2, 2 + 0.75 * tolerance, 2 + 1.5 * tolerance, 8, 11])
            rotation = random_unitary(generator, size)
            block[0] = (rotation * slopes) @ rotation.conj().T
        expected[:, indices[:, None], indices] = block
        projected[:, indices[:, None], indices] = (
            block * 2 * np.sqrt(np.mean(eigenvalues[indices])) / factor
        )
    cartesian = basis @ projected @ basis.conj().T
    reduced = np.einsum("am,mij->aij", np.linalg.inv(cell).T, cartesian)
    directions = generator.normal(size=(8, 3))
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    directions = np.concatenate([np.eye(3), directions, -np.eye(3)])
    data = {
        "cell": cell,
        "response_ddm_reduced": reduced[None],
        "response_eigenvectors": basis[None],
        "response_eigenvalues": eigenvalues[None],
        "response_groups": groups[None],
        "response_active": active[None],
        "response_directions": directions,
        "frequency_factor": np.array(factor),
        "branch_tolerance": np.array(tolerance),
    }
    return data, expected


def expected_spectra(data, response):
    groups = data["response_groups"][0]
    directions = data["response_directions"]
    velocity = np.zeros((1, len(directions), len(groups)))
    branch_velocity = np.zeros((1, len(directions), len(groups), 3))
    for label in np.unique(groups):
        indices = np.flatnonzero(groups == label)
        if not data["response_active"][0, indices[0]]:
            continue
        block = response[:, indices[:, None], indices]
        for direction_index, direction in enumerate(directions):
            directional = sum(direction[component] * block[component] for component in range(3))
            slopes, branches = eigh(directional, driver="evr")
            velocity[0, direction_index, indices] = slopes
            components = np.array(
                [
                    [np.vdot(branch, operator @ branch).real for operator in block]
                    for branch in branches.T
                ]
            )
            begin = 0
            for end in range(1, len(indices) + 1):
                if end == len(indices) or slopes[end] - slopes[end - 1] > float(data["branch_tolerance"]):
                    components[begin:end] = components[begin:end].mean(axis=0)
                    begin = end
            branch_velocity[0, direction_index, indices] = components
    return velocity, branch_velocity


def main():
    generator = np.random.default_rng(27082026)
    public_input = Path(__file__).resolve().parent.parent / "participant/input/smoke.npz"
    with np.load(public_input, allow_pickle=False) as archive:
        smoke = dict(archive)
    smoke_result = derivative(smoke)
    smoke_error = relative_error(smoke_result, finite_difference(smoke))
    assert smoke_error < 1e-9
    print("Smoke derivative / five-point finite difference:", smoke_error)
    smoke_response, smoke_velocity, smoke_branches = mode_response(smoke)
    np.testing.assert_allclose(
        smoke_response, smoke_response.conj().swapaxes(-1, -2), atol=0, rtol=0
    )
    np.testing.assert_allclose(
        np.einsum("pkim,km->pki", smoke_branches, smoke["response_directions"]),
        smoke_velocity, atol=2e-8, rtol=1e-11,
    )

    synthetic = random_polar_data(generator)
    near_direction = np.array([2.0, -3.0, 1.0])
    near_direction *= 2.1e-5 / np.linalg.norm(near_direction)
    synthetic["q_cart"][0] = near_direction
    synthetic["q_cart"][1] = -synthetic["g_vectors"][17] + near_direction
    synthetic_result = derivative(synthetic)
    finite_result = finite_difference(synthetic)
    for query in range(len(synthetic["q_cart"])):
        error = relative_error(synthetic_result[query], finite_result[query])
        assert error < 2e-8
        print("Oblique anisotropic derivative query", query, "/ finite difference:", error)
    polar_only = dict(synthetic, sr_blocks=np.zeros_like(synthetic["sr_blocks"]))
    polar_error = relative_error(derivative(polar_only), direct_polar_derivative(polar_only))
    assert polar_error < 1e-12
    print("Polar derivative / extended-precision direct formula:", polar_error)
    short_only = dict(synthetic, nac_factor=np.array(0.0))
    short_error = relative_error(derivative(short_only), finite_difference(short_only))
    assert short_error < 2e-8
    print("Short-range-only derivative / finite difference:", short_error)
    empty = dict(
        synthetic,
        g_vectors=np.zeros((0, 3)), sr_vectors=np.zeros((0, 3)),
        sr_blocks=np.zeros((0, 3, 3)), sr_i=np.zeros(0, dtype=int),
        sr_j=np.zeros(0, dtype=int),
    )
    assert np.count_nonzero(derivative(empty)) == 0

    response_data, expected = response_fixture(generator)
    response, velocity, branches = mode_response(response_data)
    expected_velocity, expected_branches = expected_spectra(response_data, expected)
    np.testing.assert_allclose(response[0], expected, atol=1e-12, rtol=1e-12)
    np.testing.assert_allclose(velocity, expected_velocity, atol=1e-11, rtol=1e-11)
    np.testing.assert_allclose(branches, expected_branches, atol=1e-10, rtol=1e-10)
    np.testing.assert_allclose(branches[0, 0, 4], branches[0, 0, 5], atol=0, rtol=0)
    np.testing.assert_allclose(branches[0, 0, 7], branches[0, 0, 8], atol=0, rtol=0)
    np.testing.assert_allclose(branches[0, 0, 8], branches[0, 0, 9], atol=0, rtol=0)
    print("Complex subspaces, inactive groups, exact and transitive ties: passed")
    rotation = np.zeros((12, 12), complex)
    groups = response_data["response_groups"][0]
    for label in np.unique(groups):
        indices = np.flatnonzero(groups == label)
        rotation[indices[:, None], indices] = random_unitary(generator, len(indices))
    rotated_data = dict(
        response_data,
        response_eigenvectors=response_data["response_eigenvectors"] @ rotation,
    )
    rotated_response, rotated_velocity, rotated_branches = mode_response(rotated_data)
    np.testing.assert_allclose(
        rotated_response, rotation.conj().T @ response @ rotation, atol=2e-12, rtol=2e-12
    )
    np.testing.assert_allclose(rotated_velocity, velocity, atol=1e-11, rtol=1e-11)
    np.testing.assert_allclose(rotated_branches, branches, atol=2e-10, rtol=2e-10)
    print("Unitary gauge covariance and branch-vector invariance: passed")

    chunked = random_polar_data(generator, atoms=12, reciprocal_radius=12, queries=1, terms=0)
    chunked_result = derivative(chunked)
    middle = len(chunked["g_vectors"]) // 2
    split_result = derivative(dict(chunked, g_vectors=chunked["g_vectors"][:middle]))
    split_result += derivative(dict(chunked, g_vectors=chunked["g_vectors"][middle:]))
    np.testing.assert_allclose(chunked_result, split_result, atol=1e-12, rtol=1e-11)
    print("Reciprocal chunking across 15625 supplied vectors: passed")

    large = random_polar_data(generator, atoms=16, reciprocal_radius=5, queries=96, terms=6000)
    started = time.perf_counter()
    large_result = derivative(large)
    assert np.isfinite(large_result).all()
    assert large_result.shape == (96, 3, 48, 48)
    print("Large derivative batch (96 queries, 16 atoms, 1331 reciprocal vectors), seconds:", time.perf_counter() - started)
    repeated = dict(response_data)
    for key in ["response_ddm_reduced", "response_eigenvectors", "response_eigenvalues", "response_groups", "response_active"]:
        repeated[key] = np.repeat(repeated[key], 512, axis=0)
    started = time.perf_counter()
    repeated_result = mode_response(repeated)
    for actual, target in zip(repeated_result, [response, velocity, branches]):
        np.testing.assert_allclose(actual, np.repeat(target, 512, axis=0), atol=1e-12, rtol=1e-12)
    print("Response batch (512 packets, 12 modes, 14 directions), seconds:", time.perf_counter() - started)
    print("All numerical checks passed.")


if __name__ == "__main__":
    main()
