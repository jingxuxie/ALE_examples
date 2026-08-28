import argparse
import copy
import json
from pathlib import Path
import time

import solve
import numpy as np


def independent_derivatives(case, spins):
    count = len(spins)
    gradient = np.zeros_like(spins)
    cartesian = np.zeros((3 * count, 3 * count))
    energy = 0.0
    for site, tensor in enumerate(case["anisotropy_meV"]):
        tensor = np.asarray(tensor)
        field = np.asarray(case["field_meV"])
        energy -= spins[site] @ tensor @ spins[site] + field @ spins[site]
        gradient[site] -= 2 * tensor @ spins[site] + field
        cartesian[3 * site:3 * site + 3, 3 * site:3 * site + 3] = -2 * tensor
    for bond, exchange in enumerate(case["exchange_meV"]):
        energy -= exchange * (spins[bond] @ spins[bond + 1])
        gradient[bond] -= exchange * spins[bond + 1]
        gradient[bond + 1] -= exchange * spins[bond]
        cartesian[3 * bond:3 * bond + 3, 3 * bond + 3:3 * bond + 6] = -exchange * np.eye(3)
        cartesian[3 * bond + 3:3 * bond + 6, 3 * bond:3 * bond + 3] = -exchange * np.eye(3)
    basis = np.zeros((3 * count, 2 * count))
    for site in range(count):
        _, _, vectors = np.linalg.svd(spins[site:site + 1], full_matrices=True)
        basis[3 * site:3 * site + 3, 2 * site:2 * site + 2] = vectors[1:].T
        cartesian[3 * site:3 * site + 3, 3 * site:3 * site + 3] -= np.dot(spins[site], gradient[site]) * np.eye(3)
    tangent_gradient = gradient - np.sum(gradient * spins, axis=1)[:, None] * spins
    hessian = basis.T @ cartesian @ basis
    return energy, tangent_gradient, hessian


def verify_case(case, result):
    saddle = result["saddle"]
    np.testing.assert_allclose(np.linalg.norm(saddle, axis=1), 1.0, atol=2e-13)
    energy, gradient, hessian = independent_derivatives(case, saddle)
    energy_a, gradient_a, hessian_a = independent_derivatives(case, np.asarray(case["minimum_a"]))
    values_a = np.linalg.eigvalsh(hessian_a)
    values_s = np.linalg.eigvalsh(hessian)
    assert values_a[0] > 0
    assert values_s[0] < 0 < values_s[1]
    assert np.max(np.linalg.norm(gradient, axis=1)) < 1e-7
    np.testing.assert_allclose(result["barrier_meV"], energy - energy_a, atol=1e-11)
    np.testing.assert_allclose(result["eigenvalues_min_meV"], values_a, atol=1e-11)
    np.testing.assert_allclose(result["eigenvalues_saddle_meV"], values_s, atol=1e-11)
    logarithm = 0.5 * (np.log(values_a).sum() - np.log(values_s[1:]).sum())
    np.testing.assert_allclose(result["log_omega0"], logarithm, atol=1e-10)
    model = solve.SpinModel(case)
    plane = model.plane()
    if plane is not None:
        planar = solve.PlanarModel(model, plane)
        assert solve.connected_planar(planar, planar.angles(saddle))
    generator = np.random.default_rng(9814)
    direction = generator.normal(size=saddle.shape)
    direction -= np.sum(direction * saddle, axis=1)[:, None] * saddle
    direction /= np.linalg.norm(direction)
    step = 2e-4
    plus = solve.sphere_step(saddle, step * direction)
    minus = solve.sphere_step(saddle, -step * direction)
    energy_plus = independent_derivatives(case, plus)[0]
    energy_minus = independent_derivatives(case, minus)[0]
    _, _, analytical, basis = model.derivatives(saddle)
    coefficients = np.einsum("nik,ni->nk", basis, direction).ravel()
    np.testing.assert_allclose((energy_plus + energy_minus - 2 * energy) / step**2, coefficients @ analytical @ coefficients, rtol=2e-6, atol=1e-5)
    return np.max(np.linalg.norm(gradient, axis=1))


def rotate_case(case):
    generator = np.random.default_rng(14429)
    rotation, _ = np.linalg.qr(generator.normal(size=(3, 3)))
    rotated = copy.deepcopy(case)
    for name in ("minimum_a", "minimum_b"):
        rotated[name] = (np.asarray(case[name]) @ rotation.T).tolist()
    rotated["field_meV"] = (rotation @ np.asarray(case["field_meV"])).tolist()
    rotated["anisotropy_meV"] = np.einsum("ik,nkl,jl->nij", rotation, np.asarray(case["anisotropy_meV"]), rotation).tolist()
    return rotated


def perturb_case(case):
    from scipy.spatial.transform import Rotation

    generator = np.random.default_rng(773293)
    perturbed = copy.deepcopy(case)
    count = len(case["minimum_a"])
    rotations = Rotation.from_rotvec(generator.normal(0.0, 0.035, (count, 3))).as_matrix()
    perturbed["anisotropy_meV"] = np.einsum("nik,nkl,njl->nij", rotations, np.asarray(case["anisotropy_meV"]), rotations).tolist()
    perturbed["exchange_meV"] = (np.asarray(case["exchange_meV"]) * generator.uniform(0.95, 1.05, count - 1)).tolist()
    perturbed["field_meV"][1] += 0.003
    model = solve.SpinModel(perturbed)
    for name in ("minimum_a", "minimum_b"):
        minimum = model.relax(np.asarray(perturbed[name]))
        assert np.max(np.abs(model.derivatives(minimum)[1])) < 1e-8
        perturbed[name] = minimum.tolist()
    return perturbed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", nargs="+")
    parser.add_argument("--rotate", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--perturb", action="store_true")
    arguments = parser.parse_args()
    for filename in arguments.cases:
        case = json.loads(Path(filename).read_text())
        started = time.monotonic()
        result = solve.solve(case)
        residual = verify_case(case, result)
        print(f"{Path(filename).stem}: barrier={result['barrier_meV']:.12f}, log_omega0={result['log_omega0']:.12f}, residual={residual:.2e}, seconds={time.monotonic() - started:.3f}", flush=True)
        if arguments.rotate:
            rotated = rotate_case(case)
            other = solve.solve(rotated)
            verify_case(rotated, other)
            for name in ("barrier_meV", "eigenvalues_min_meV", "eigenvalues_saddle_meV", "log_omega0"):
                np.testing.assert_allclose(result[name], other[name], atol=2e-8)
            print("  rotation invariance: passed", flush=True)
        if arguments.full:
            model = solve.SpinModel(case)
            saddle = solve.search_full(model, time.monotonic() + 45)
            assert saddle is not None
            assert solve.connected_full(model, saddle)
            energy, gradient, hessian = independent_derivatives(case, saddle)
            energy_a = independent_derivatives(case, model.minimum_a)[0]
            assert np.max(np.linalg.norm(gradient, axis=1)) < 1e-7
            np.testing.assert_allclose(energy - energy_a, result["barrier_meV"], atol=2e-8)
            np.testing.assert_allclose(np.linalg.eigvalsh(hessian), result["eigenvalues_saddle_meV"], atol=2e-8)
            print("  full-sphere search: passed", flush=True)
        if arguments.perturb:
            perturbed = perturb_case(case)
            other = solve.solve(perturbed)
            verify_case(perturbed, other)
            assert solve.connected_full(solve.SpinModel(perturbed), other["saddle"])
            print("  nonplanar perturbation: passed", flush=True)


if __name__ == "__main__":
    main()
