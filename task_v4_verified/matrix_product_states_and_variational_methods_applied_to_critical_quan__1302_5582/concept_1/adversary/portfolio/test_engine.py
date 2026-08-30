"""Portfolio-local numerical tests; does not import participant files."""

import os
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

from pathlib import Path
import time
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parent
VARIANT = os.environ.get("PORTFOLIO_VARIANT", "v1")
if VARIANT not in ("v1", "v2", "v3"):
    raise ValueError("unknown portfolio variant")
sys.path.insert(0, str(ROOT / VARIANT))
import contractor
import engine


def request_for(sector):
    return {"version": 1, "case_id": "independent-unit", "seed": 29, "n_sites": 3,
            "local_dim": 4, "bond_cap": 4, "sector": sector, "omega": [0.7, 1.2, 0.9],
            "mass2": [-1.2, -0.6, -1.4], "lambda4": [2.0, 2.4, 1.8],
            "field": [0.002, 0.0, -0.003] if sector == "any" else [0.0] * 3,
            "coupling": [0.8, 1.1], "budget_seconds": 30.0, "wall_seconds": 120.0}


def kron_all(factors):
    result = np.ones((1, 1))
    for factor in factors:
        result = np.kron(result, factor)
    return result


def exact_energy(request):
    onsite, position = contractor.hamiltonian_terms(request)
    dimension = request["local_dim"]
    length = request["n_sites"]
    matrix = np.zeros((dimension ** length,) * 2)
    for site, local in enumerate(onsite):
        factors = [np.eye(dimension) for _ in onsite]
        factors[site] = local
        matrix += kron_all(factors)
    for site, coupling in enumerate(request["coupling"]):
        factors = [np.eye(dimension) for _ in onsite]
        factors[site] = position[site]
        factors[site + 1] = position[site + 1]
        matrix -= coupling * kron_all(factors)
    if request["sector"] != "any":
        parities = np.array([sum(np.unravel_index(index, [dimension] * length)) % 2
                             for index in range(dimension ** length)])
        indices = np.flatnonzero(parities == int(request["sector"] == "odd"))
        matrix = matrix[np.ix_(indices, indices)]
    return np.linalg.eigvalsh(matrix)[0]


class EngineTests(unittest.TestCase):
    def test_small_exact_sector_energies(self):
        for sector in ("any", "even", "odd"):
            with self.subTest(sector=sector):
                request = request_for(sector)
                tensors, _ = engine.optimize(request)
                measured = contractor.measure(tensors, request)
                exact = exact_energy(request)
                self.assertGreaterEqual(measured["energy"] + 1e-9, exact)
                self.assertLess(measured["energy"] - exact, 3e-7)

    def test_complex_charge_split(self):
        generator = np.random.default_rng(71)
        shape = (2, 3, 3, 2)
        charges = np.array([0, 1])
        allowed = (charges[:, None, None, None] ^ (np.arange(3)[None, :, None, None] % 2)
                   ^ (np.arange(3)[None, None, :, None] % 2) ^ charges[None, None, None, :]) == 0
        theta = (generator.normal(size=shape) + 1j * generator.normal(size=shape)) * allowed
        theta /= np.linalg.norm(theta)
        for direction in ("left", "right"):
            first, second, middle = engine.split_pair(theta.ravel(), shape, 6, direction, charges, charges)
            np.testing.assert_allclose(np.tensordot(first, second, axes=(2, 0)), theta, atol=1e-13)
            mask = (charges[:, None, None] ^ (np.arange(3)[None, :, None] % 2)
                    ^ middle[None, None, :]) == 0
            self.assertEqual(np.max(np.abs(first[~mask])), 0.0)

    def test_zero_tilt_odd_initialization(self):
        request = request_for("odd")
        request["mass2"] = [1.0] * 3
        onsite, _ = contractor.hamiltonian_terms(request)
        vectors = []
        for local in onsite:
            vector = np.zeros(4)
            vector[::2] = np.linalg.eigh(local[::2, ::2])[1][:, 0]
            vectors.append(vector)
        tensors, charges = engine.initial_state(vectors, request)
        measured = contractor.measure(tensors, request)
        self.assertAlmostEqual(measured["parity"], -1.0, places=12)
        self.assertEqual(charges[-1][0], 1)

    def test_expired_deadline_preserves_valid_state(self):
        request = request_for("even")
        vectors = engine.mean_field_starts(request, time.process_time() + 0.2)[0][1]
        tensors, charges = engine.initial_state(vectors, request)
        before = contractor.measure(tensors, request)
        tensors, charges, complete = engine.sweep(tensors, charges, engine.make_mpo(request), 4,
                                                 1e-8, time.process_time() - 1)
        after = contractor.measure(tensors, request)
        self.assertFalse(complete)
        self.assertAlmostEqual(before["energy"], after["energy"], places=11)


if __name__ == "__main__":
    unittest.main(verbosity=2)
