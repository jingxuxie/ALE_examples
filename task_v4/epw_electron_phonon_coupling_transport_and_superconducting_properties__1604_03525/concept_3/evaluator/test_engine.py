import json
import os
from pathlib import Path
import tempfile
import unittest

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from hidden.engine import DIMENSION, InvalidWitness, certify_coefficients, direct_observables, load_witness, validate_pair


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.zero = np.zeros((DIMENSION, DIMENSION))
        self.weak = self.zero.copy()
        self.weak[0, 4] = self.weak[4, 0] = 0.15
        self.weak[1, 5] = self.weak[5, 1] = -0.15

    def test_isotropic_exact_solution(self):
        result = validate_pair((self.zero, self.zero))
        self.assertTrue(result["valid"])
        self.assertFalse(result["passed"])
        self.assertAlmostEqual(result["trace_ratio"], 1)
        np.testing.assert_allclose(result["certificates"][0]["continuum_conductivity"], np.eye(2) / 2)

    def test_higher_harmonic_leakage_with_matched_full_tensor(self):
        result = validate_pair((self.zero, self.weak))
        self.assertTrue(result["valid"])
        self.assertFalse(result["passed"])
        self.assertAlmostEqual(result["trace_ratio"], 1 / (1 - 0.15 ** 2), places=11)
        self.assertLess(result["maximum_numerical_error"], 1e-11)

    def test_rotation_cannot_change_trace_score(self):
        rotated = self.zero.copy()
        rotated[0, 4] = rotated[4, 0] = 0.12
        tensor, _ = certify_coefficients(rotated)
        transform = np.zeros_like(rotated)
        angle = 0.347
        for harmonic in range(1, 10):
            block = np.array([[np.cos(harmonic * angle), -np.sin(harmonic * angle)],
                              [np.sin(harmonic * angle), np.cos(harmonic * angle)]])
            start = 2 * harmonic - 2
            transform[start:start + 2, start:start + 2] = block
        other_tensor, _ = certify_coefficients(transform @ rotated @ transform.T)
        self.assertAlmostEqual(np.trace(tensor), np.trace(other_tensor), places=12)

    def test_trivial_first_harmonic_anisotropy_is_rejected(self):
        changed = self.zero.copy()
        changed[0, 0] = 0.1
        changed[1, 1] = -0.1
        with self.assertRaises(InvalidWitness):
            certify_coefficients(changed)

    def test_asymmetry_inversion_and_negative_kernel_rejected(self):
        for row, column, value in ((0, 4, 0.1), (0, 2, 0.1), (4, 4, 0.9)):
            changed = self.zero.copy()
            changed[row, column] = value
            if column != 4 or row != 0:
                changed[column, row] = value
            with self.assertRaises(InvalidWitness):
                certify_coefficients(changed)

    def test_shifted_dense_invariants(self):
        values = direct_observables(self.weak, 96, 0.219)
        np.testing.assert_allclose(values["degree"], 1, atol=1e-12)
        np.testing.assert_allclose(values["dirichlet"], np.eye(2) / 2, atol=1e-12)

    def test_loader_rejects_malformed_numeric_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "witness.json"
            for text in ('{"schema_version": 1, "schema_version": 1}', '{"kernel_a": NaN}', '[]'):
                path.write_text(text)
                with self.assertRaises((InvalidWitness, ValueError)):
                    load_witness(directory)
            payload = {"schema_version": 1, "kernel_a": self.zero.tolist(), "kernel_b": self.zero.tolist()}
            for bad_value in (True, "0", 1e100):
                payload["kernel_a"][0][0] = bad_value
                path.write_text(json.dumps(payload))
                with self.assertRaises(InvalidWitness):
                    load_witness(directory)
            path.write_text(" " * 131073)
            with self.assertRaises(InvalidWitness):
                load_witness(directory)

    def test_symlink_witness_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target.json"
            target.write_text("{}")
            (Path(directory) / "witness.json").symlink_to(target)
            with self.assertRaises(InvalidWitness):
                load_witness(directory)


if __name__ == "__main__":
    unittest.main()
