"""Deterministic builder checks; run with /usr/bin/python, threads=1."""

import os

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(ROOT / "participant/workspace"))
import contractor
import trusted_contractor
from mps import make_mpo, product_state, project_parity, sweep


def small_request():
    return {"version": 1, "case_id": "test", "seed": 1, "n_sites": 4, "local_dim": 4,
            "bond_cap": 8, "sector": "any", "omega": [0.6, 0.9, 1.4, 0.8],
            "mass2": [-0.8, 0.4, -0.3, 0.1], "lambda4": [1.8, 2.2, 1.3, 1.6],
            "field": [0.001, 0.0, -0.002, 0.0], "coupling": [0.3, 1.1, 0.7],
            "budget_seconds": 6.0, "wall_seconds": 10.0}


def kron_chain(factors):
    result = np.ones((1, 1))
    for factor in factors:
        result = np.kron(result, factor)
    return result


def dense_hamiltonian(request):
    length, dimension = request["n_sites"], request["local_dim"]
    result = np.zeros((dimension ** length,) * 2)
    for site in range(length):
        padded = dimension + 8
        ladder = np.diag(np.sqrt(np.arange(1, padded)), 1)
        position = (ladder + ladder.T) / np.sqrt(2 * request["omega"][site])
        momentum = 1j * np.sqrt(request["omega"][site] / 2) * (ladder.T - ladder)
        local = (0.5 * momentum @ momentum
                 + 0.5 * request["mass2"][site] * position @ position
                 + request["lambda4"][site] / 24 * np.linalg.matrix_power(position, 4)
                 - request["field"][site] * position).real[:dimension, :dimension]
        factors = [np.eye(dimension) for _ in range(length)]
        factors[site] = local
        result += kron_chain(factors)
    for site, coupling in enumerate(request["coupling"]):
        for endpoint in (site, site + 1):
            factors = [np.eye(dimension) for _ in range(length)]
            padded = dimension + 8
            ladder = np.diag(np.sqrt(np.arange(1, padded)), 1)
            position = (ladder + ladder.T) / np.sqrt(2 * request["omega"][endpoint])
            factors[endpoint] = (position @ position)[:dimension, :dimension]
            result += 0.5 * coupling * kron_chain(factors)
        factors = [np.eye(dimension) for _ in range(length)]
        for endpoint in (site, site + 1):
            ladder = np.diag(np.sqrt(np.arange(1, dimension)), 1)
            factors[endpoint] = (ladder + ladder.T) / np.sqrt(2 * request["omega"][endpoint])
        result -= coupling * kron_chain(factors)
    return result


def dense_state(tensors):
    vector = tensors[0][0]
    for tensor in tensors[1:]:
        vector = np.tensordot(vector, tensor, axes=(-1, 0))
    return vector.ravel()


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.request = small_request()
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / "adversary")
        self.path = Path(self.folder.name) / "state.npz"
        self.tensors = product_state(self.request, tilt=0.1)

    def tearDown(self):
        self.folder.cleanup()

    def test_projected_powers(self):
        local = contractor.local_operators(7, 0.7)
        levels = np.arange(7)
        np.testing.assert_allclose(np.diag(local["q2"]), (levels + 0.5) / 0.7)
        np.testing.assert_allclose(np.diag(local["p2"]), (levels + 0.5) * 0.7)
        np.testing.assert_allclose(np.diag(local["q4"]), 3 * (2 * levels ** 2 + 2 * levels + 1) / (4 * 0.7 ** 2))
        self.assertGreater(np.linalg.norm(local["q2"] - local["q"] @ local["q"]), 1)
        self.assertGreater(np.linalg.norm(local["q4"] - np.linalg.matrix_power(local["q"], 4)), 1)

    def test_complex_dense_and_gauge(self):
        generator = np.random.default_rng(709)
        bonds = [1, 3, 5, 2, 1]
        tensors = [generator.normal(size=(bonds[site], 4, bonds[site + 1]))
                   + 1j * generator.normal(size=(bonds[site], 4, bonds[site + 1])) for site in range(4)]
        vector = dense_state(tensors)
        expected = np.vdot(vector, dense_hamiltonian(self.request) @ vector) / np.vdot(vector, vector)
        for implementation in (contractor, trusted_contractor):
            measured = implementation.measure(tensors, self.request)
            self.assertAlmostEqual(measured["energy"], expected.real, places=11)
        tensors[0] *= 1e70
        tensors[1] *= 1e-70
        self.assertAlmostEqual(contractor.measure(tensors, self.request)["energy"], expected.real, places=10)

    def test_mpo_matches_dense(self):
        mpo = make_mpo(self.request)
        combined = mpo[0][0]
        for tensor in mpo[1:]:
            combined = np.einsum("apq,abrs->bprqs", combined, tensor).reshape(
                tensor.shape[1], combined.shape[1] * 4, combined.shape[2] * 4)
        np.testing.assert_allclose(combined[0], dense_hamiltonian(self.request), atol=1e-12)

    def test_variational_engine_against_exact(self):
        mpo = make_mpo(self.request)
        tensors = self.tensors
        for _ in range(3):
            tensors = sweep(tensors, mpo, 8, tolerance=1e-11, maxiter=100)
        energy = contractor.measure(tensors, self.request)["energy"]
        exact = np.linalg.eigvalsh(dense_hamiltonian(self.request))[0]
        self.assertGreaterEqual(energy + 1e-10, exact)
        self.assertLess(energy - exact, 1e-6)

    def test_parity_sectors(self):
        self.request["field"] = [0.0] * 4
        for sector in ("even", "odd"):
            self.request["sector"] = sector
            tensors = project_parity(self.tensors, sector)
            self.assertAlmostEqual(contractor.measure(tensors, self.request)["parity"],
                                   1 if sector == "even" else -1, places=10)
        with self.assertRaises(ValueError):
            contractor.measure(self.tensors, self.request)

    def test_roundtrip(self):
        contractor.save_mps(self.path, self.tensors)
        self.assertEqual(len(contractor.load_mps(self.path, self.request)), 4)

    def test_nonfinite_and_zero(self):
        for value in (np.nan, np.inf, -np.inf, 1e101):
            tensors = [tensor.copy() for tensor in self.tensors]
            tensors[0][0, 0, 0] = value
            contractor.save_mps(self.path, tensors)
            with self.assertRaises(ValueError):
                trusted_contractor.load_mps(self.path, self.request)
        tensors = [tensor.copy() for tensor in self.tensors]
        tensors[1][:] = 0
        with self.assertRaises(ValueError):
            contractor.measure(tensors, self.request)

    def test_malformed_arrays(self):
        arrays = {"A%d" % site: tensor for site, tensor in enumerate(self.tensors)}
        for invalid in (np.zeros((1, 4, 9)), np.ones((1, 3, 1)), np.ones((4,)),
                        np.ones((1, 4, 1), dtype=np.float32), np.array([[['x']]], dtype=object)):
            np.savez(self.path, **dict(arrays, A0=invalid))
            with self.assertRaises(ValueError):
                contractor.load_mps(self.path, self.request)
        np.savez(self.path, **dict(arrays, claimed_energy=np.array(-1e99)))
        with self.assertRaises(ValueError):
            contractor.load_mps(self.path, self.request)

    def test_duplicate_and_symlink(self):
        contractor.save_mps(self.path, self.tensors)
        with zipfile.ZipFile(self.path, "a") as archive:
            archive.writestr("A0.npy", b"bad")
        with self.assertRaises(ValueError):
            contractor.load_mps(self.path, self.request)
        link = self.path.with_name("link.npz")
        link.symlink_to(self.path)
        with self.assertRaises(ValueError):
            contractor.load_mps(link, self.request)


if __name__ == "__main__":
    unittest.main(verbosity=2)
