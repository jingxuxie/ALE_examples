import os
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "v1"))
import core
import optimizer
from contractor import measure


class VariantTests(unittest.TestCase):
    def setUp(self):
        self.random = np.random.default_rng(7182)

    def symmetric(self, size):
        matrix = self.random.normal(size=(size, size))
        return (matrix + matrix.T) * 0.5

    def test_environment_kernels_equal_dense_operator(self):
        for left, dimension, right in ((2, 4, 3), (3, 5, 2), (1, 6, 4)):
            tensor = self.random.normal(size=(left, dimension, right))
            onsite, position = self.symmetric(dimension), self.symmetric(dimension)
            left_environment = self.symmetric(left), self.symmetric(left)
            right_environment = self.symmetric(right), self.symmetric(right)
            for actual, expected in zip(optimizer.left_step(left_environment, tensor, onsite, position, 0.7),
                                        core.left_step(left_environment, tensor, onsite, position, 0.7)):
                np.testing.assert_allclose(actual, expected, atol=2e-12)
            for actual, expected in zip(optimizer.right_step(right_environment, tensor, onsite, position, 0.7),
                                        core.right_step(right_environment, tensor, onsite, position, 0.7)):
                np.testing.assert_allclose(actual, expected, atol=2e-12)

    def test_site_kernel_and_diagonal_equal_dense_operator(self):
        shape = (3, 4, 2)
        left_environment = self.symmetric(3), self.symmetric(3)
        right_environment = self.symmetric(2), self.symmetric(2)
        onsite, position = self.symmetric(4), self.symmetric(4)
        left_matrix = core.left_block(left_environment, onsite, position, 0.8)
        full = (np.kron(left_matrix, np.eye(2)) + np.kron(np.eye(12), right_environment[0])
                - 0.6 * np.kron(np.kron(np.eye(3), position), right_environment[1]))
        row_charge = (np.arange(3)[:, None] % 2 ^ (np.arange(4)[None, :] % 2)).ravel()
        for rows, columns in ((None, None), (row_charge, np.arange(2))):
            action, diagonal, pack, unpack = optimizer.site_action(
                left_environment, right_environment, onsite, position, 0.8, 0.6, shape, rows, columns)
            vector = pack(self.random.normal(size=shape))
            expected = pack((full @ unpack(vector).ravel()).reshape(shape))
            np.testing.assert_allclose(action(vector), expected, atol=2e-12)
            np.testing.assert_allclose(diagonal, pack(np.diag(full).reshape(shape)), atol=2e-12)

    def test_qr_preserves_state_and_charge_blocks(self):
        rows = np.arange(11) % 2
        columns = np.arange(7) % 2
        matrix = self.random.normal(size=(11, 7)) * (rows[:, None] == columns[None, :])
        orthogonal, triangular, charges = optimizer.charge_qr(matrix, rows, columns)
        np.testing.assert_allclose(orthogonal @ triangular, matrix, atol=2e-12)
        np.testing.assert_allclose(orthogonal.T @ orthogonal, np.eye(7), atol=2e-12)
        self.assertEqual(float(np.sum(np.abs(orthogonal) * (rows[:, None] != charges[None, :]))), 0.0)
        for candidate in (matrix, matrix.T):
            orthogonal, triangular, _ = optimizer.charge_qr(candidate)
            np.testing.assert_allclose(orthogonal @ triangular, candidate, atol=2e-12)

    def test_small_states_preserve_sectors_and_respond_to_fields(self):
        request = {"n_sites": 4, "local_dim": 4, "bond_cap": 4, "sector": "even",
                   "omega": [1.0] * 4, "mass2": [-0.08] * 4, "lambda4": [0.1] * 4,
                   "field": [0.0] * 4, "coupling": [1.0] * 3,
                   "budget_seconds": 0.9, "wall_seconds": 10.0}
        for sector in ("even", "odd"):
            request["sector"] = sector
            checked = measure(optimizer.optimize(request), request)
            self.assertLessEqual(checked["max_bond"], 4)
            self.assertAlmostEqual(checked["parity"], 1.0 if sector == "even" else -1.0, places=8)
        request.update(sector="any", field=[0.003] * 4)
        checked = measure(optimizer.optimize(request), request)
        self.assertLess(checked["parity"], 1.0 - 1e-7)


if __name__ == "__main__":
    unittest.main()
