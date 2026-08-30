import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import itertools
import json
from pathlib import Path
import sys
import tempfile

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import eigsh

from trusted_physics import SIGMA_X, SIGMA_Z, apply_transfer, check, exact_density, exact_order, metrics, transfer_matrix


def assert_close(observed, expected, tolerance, name):
    if np.max(np.abs(np.asarray(observed) - np.asarray(expected))) > tolerance:
        raise AssertionError(name + ": " + str((observed, expected)))


def operator_transfer(tensor, operator):
    dimension = tensor.shape[1]
    basis = np.eye(dimension**2).reshape(dimension**2, dimension, dimension)
    return np.stack([apply_transfer(tensor, matrix, operator).reshape(-1) for matrix in basis], axis=1)


def main():
    concept = Path(__file__).resolve().parents[2]
    checks = []
    for distance in range(1, 129):
        positions = np.arange(1, distance)
        log_product = distance * np.log(2 / np.pi) - np.sum((distance - positions) * np.log1p(-1.0 / (4 * positions**2)))
        assert_close(exact_order(distance), np.exp(log_product), 1e-12, "Cauchy determinant/product")
    checks.append("128 exact order targets agree with independent Cauchy products")
    assert_close(exact_density(1), 4 / (3 * np.pi**2), 1e-15, "nearest density")
    assert_close(exact_order(1), 2 / np.pi, 1e-15, "nearest order")
    checks.append("nearest-neighbor normalization and connected-density convention")
    theta, phi = 0.25, 1.05
    tensor = np.array([[[np.cos(theta), 0.0], [0.0, np.cos(phi)]], [[0.0, np.sin(theta)], [np.sin(phi), 0.0]]], dtype=np.complex128)
    tensor[0, 0, 0] *= np.exp(0.17j)
    tensor[0, 1, 1] *= np.exp(-0.13j)
    tensor[1, 0, 1] *= np.exp(0.21j)
    tensor[1, 1, 0] *= np.exp(-0.31j)
    length = 10
    states = list(itertools.product((0, 1), repeat=length))
    amplitudes = []
    for state in states:
        matrix = np.eye(2, dtype=complex)
        for physical in state:
            matrix = matrix @ tensor[physical]
        amplitudes.append(np.trace(matrix))
    amplitudes = np.asarray(amplitudes)
    amplitudes /= np.linalg.norm(amplitudes)
    transfer = transfer_matrix(tensor)
    norm_ring = np.trace(np.linalg.matrix_power(transfer, length))
    for distance in (1, 2, 4):
        flip_mask = (1 << (length - 1)) | (1 << (length - 1 - distance))
        enumerated_order = np.vdot(amplitudes, amplitudes[np.arange(2**length) ^ flip_mask])
        signs = np.array([(-1.0)**(state[0] + state[distance]) for state in states])
        enumerated_density = np.vdot(amplitudes, signs * amplitudes)
        for operator, enumerated in [(SIGMA_X, enumerated_order), (SIGMA_Z, enumerated_density)]:
            inserted = operator_transfer(tensor, operator)
            contracted = np.trace(inserted @ np.linalg.matrix_power(transfer, distance - 1) @ inserted @ np.linalg.matrix_power(transfer, length - distance - 1)) / norm_ring
            assert_close(contracted, enumerated, 2e-12, "finite ring independent enumeration")
    checks.append("complex MPS finite-ring correlations agree with 1024 enumerated amplitudes")
    values = metrics(tensor)
    for distance in (1, 2, 4, 32):
        for operator, expected in [(SIGMA_X, values["order_correlations"][distance - 1]), (SIGMA_Z, values["density_connected_correlations"][distance - 1] + values["transverse_magnetization"]**2)]:
            inserted = operator_transfer(tensor, operator)
            contracted = np.trace(inserted @ np.linalg.matrix_power(transfer, distance - 1) @ inserted @ np.linalg.matrix_power(transfer, 256 - distance - 1)) / np.trace(np.linalg.matrix_power(transfer, 256))
            assert_close(contracted, expected, 2e-12, "stationary limit")
    checks.append("stationary-density contractions agree with independently contracted length-256 ring")
    for sites in (8, 10, 12):
        indices = np.arange(2**sites, dtype=np.int64)
        diagonal = np.zeros(len(indices))
        rows = [indices]
        columns = [indices]
        data = []
        for site in range(sites):
            diagonal -= 1 - 2 * ((indices >> site) & 1)
            rows.append(indices)
            columns.append(indices ^ ((1 << site) | (1 << ((site + 1) % sites))))
        data = [diagonal] + [-np.ones(len(indices)) for site in range(sites)]
        hamiltonian = coo_matrix((np.concatenate(data), (np.concatenate(rows), np.concatenate(columns))), shape=(len(indices), len(indices))).tocsr()
        energy, vector = eigsh(hamiltonian, k=1, which="SA", tol=2e-12, v0=np.ones(len(indices)))
        exact_finite = -2.0 / (sites * np.sin(np.pi / (2 * sites)))
        assert_close(energy[0] / sites, exact_finite, 2e-12, "independent finite Ising ground energy")
        if sites == 12:
            vector = vector[:, 0]
            finite_order = float(np.dot(vector, vector[indices ^ 3]))
            finite_z = float(np.dot(vector, (1 - 2 * (indices & 1)) * vector))
            assert_close(finite_order, -exact_finite / 2, 2e-11, "Ising duality at nearest separation")
            assert_close(finite_z, -exact_finite / 2, 2e-11, "Ising magnetization normalization")
    checks.append("sparse spin Hamiltonians at N=8,10,12 reproduce exact finite-chain spectrum and normalization")
    with tempfile.TemporaryDirectory(dir=concept / "adversary") as directory:
        destination = Path(directory)
        for name, malformed in [("nan", np.full((2, 2, 2), np.nan)), ("odd_dimension", np.zeros((2, 3, 3))), ("oversized_dimension", np.zeros((2, 26, 26))), ("noncanonical", tensor * 2), ("degenerate", np.array([np.eye(2), np.zeros((2, 2))])), ("zero", np.zeros((2, 2, 2)))]:
            path = destination / (name + ".npz")
            np.savez(path, A=malformed)
            assert not check(path)["valid"], name
        extra = destination / "extra.npz"
        np.savez(extra, A=tensor, score=1)
        assert not check(extra)["valid"]
        good = destination / "good.npz"
        np.savez(good, A=tensor)
        assert check(good)["valid"]
        assert not check(good)["passed"]
    checks.append("malformed, NaN, wrong bond, degenerate, scaled, zero, and extra-key artifacts rejected")
    report = {"passed": True, "checks": checks, "failed": 0}
    (concept / "adversary" / "trust_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
