import os
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "champion"))

import numpy as np

from contractor import canonicalize, hamiltonian_terms, measure
from observables import diagnostics
from refine import project_parity, refine
import optimizer
import teacher_engine


def small_request(sector="any"):
    return {"n_sites": 3, "local_dim": 4, "bond_cap": 4, "omega": [1.0] * 3,
            "mass2": [-0.7] * 3, "lambda4": [2.5] * 3, "coupling": [1.0] * 2,
            "field": [0.0] * 3, "sector": sector, "seed": 1,
            "budget_seconds": 2.0, "wall_seconds": 30.0}


class ObservablesTests(unittest.TestCase):
    def test_sequential_environments_real_and_complex(self):
        generator = np.random.default_rng(19)
        for complex_values in (False, True):
            arrays = [generator.normal(size=shape) for shape in
                      ((3, 2, 3), (3, 4, 5), (2, 3, 4, 4), (5, 3, 5))]
            if complex_values:
                arrays = [array + 1j * generator.normal(size=array.shape) for array in arrays]
            left, tensor, operator, right = arrays
            expected_left = np.einsum("awb,apr,wxpq,bqs->rxs", left, tensor.conj(), operator, tensor)
            expected_right = np.einsum("apr,wxpq,bqs,rxs->awb", tensor.conj(), operator, tensor, right)
            np.testing.assert_allclose(teacher_engine.left_step(left, tensor, operator), expected_left, atol=1e-11)
            np.testing.assert_allclose(teacher_engine.right_step(right, tensor, operator), expected_right, atol=1e-11)

    def test_dense_complex_variance_and_schmidt(self):
        request = small_request()
        generator = np.random.default_rng(71)
        tensors = [generator.normal(size=shape) + 1j * generator.normal(size=shape)
                   for shape in ((1, 4, 3), (3, 4, 3), (3, 4, 1))]
        tensors = canonicalize(tensors)
        vector = np.einsum("apb,bqc,crd->pqr", *tensors).ravel()
        onsite, positions = hamiltonian_terms(request)
        identity = np.eye(4)
        matrix = (np.kron(np.kron(onsite[0], identity), identity)
                  + np.kron(np.kron(identity, onsite[1]), identity)
                  + np.kron(np.kron(identity, identity), onsite[2])
                  - np.kron(np.kron(positions[0], positions[1]), identity)
                  - np.kron(np.kron(identity, positions[1]), positions[2]))
        energy = float(np.vdot(vector, matrix @ vector).real)
        result = diagnostics(tensors, request, energy)
        self.assertAlmostEqual(result["energy_variance"],
                               np.linalg.norm(matrix @ vector - energy * vector) ** 2, places=10)
        for record in result["schmidt"]:
            values = np.linalg.svd(vector.reshape(4 ** record["cut"], -1), compute_uv=False)
            np.testing.assert_allclose(record["probabilities"], values[:3] ** 2, atol=1e-12)

    def test_refinement_preserves_parity_and_cap(self):
        for sector in ("even", "odd"):
            request = small_request(sector)
            state = optimizer.optimize(request)
            initial = measure(state, request)
            improved, trajectory = refine(state, request, budget_seconds=2.0, max_sweeps=2)
            checked = measure(improved, request)
            self.assertLessEqual(checked["energy"], initial["energy"] + 1e-11)
            self.assertLessEqual(checked["max_bond"], request["bond_cap"])
            self.assertTrue(trajectory)

    def test_parity_projection_dense(self):
        request = small_request()
        generator = np.random.default_rng(42)
        state = [generator.normal(size=shape) for shape in ((1, 4, 2), (2, 4, 2), (2, 4, 1))]
        state = canonicalize(state)
        dense = np.einsum("apb,bqc,crd->pqr", *state).ravel()
        parity = np.array([(-1.0) ** sum(index) for index in np.ndindex(4, 4, 4)])
        for sector, sign in (("even", 1), ("odd", -1)):
            expected = dense * (1 + sign * parity)
            expected /= np.linalg.norm(expected)
            projected = project_parity(state, request, sector)
            actual = np.einsum("apb,bqc,crd->pqr", *projected).ravel()
            self.assertAlmostEqual(abs(np.vdot(expected, actual)), 1.0, places=11)

    def test_tilted_hamiltonian_releases_projected_seed(self):
        zero_field = small_request()
        state = optimizer.optimize(zero_field)
        seed = project_parity(state, zero_field, "even")
        request = dict(zero_field, field=[0.03, -0.02, 0.01])
        initial = measure(seed, request)
        improved, _ = refine(seed, request, budget_seconds=2.0, max_sweeps=2)
        checked = measure(improved, request)
        self.assertLess(checked["energy"], initial["energy"] - 1e-8)
        self.assertLess(abs(checked["parity"]), 1 - 1e-8)


if __name__ == "__main__":
    unittest.main()
