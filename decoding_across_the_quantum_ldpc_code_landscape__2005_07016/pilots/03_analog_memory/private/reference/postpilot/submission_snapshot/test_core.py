import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np

from solve import solve_arrays
from validate import exact_tests, generate, in_row_space, row_basis, toric2d, verify


class DecoderTests(unittest.TestCase):
    def test_exhaustive_map_and_invariances(self):
        exact_tests()

    def test_forced_osd_with_dependent_checks(self):
        random = np.random.default_rng(914)
        independent = random.integers(0, 2, (5, 9), dtype=np.uint8)
        checks = np.vstack((independent, independent[0] ^ independent[3]))
        metachecks = np.array([[1, 0, 0, 1, 0, 1]], dtype=np.uint8)
        stabilizers = np.zeros((0, 9), dtype=np.uint8)
        case, _, _ = generate((checks, stabilizers, metachecks), 16, 3, 0.15, 1.3, 417)
        answer, statistics = solve_arrays(case, iterations=0, runs=1)
        verify(case, answer)
        self.assertTrue(np.all(statistics[:, 2] == 0))

    def test_affine_calibration_and_single_round(self):
        for rounds in (1, 3):
            case, _, _ = generate(toric2d(3), 8, rounds, 0.07, 0.8, 92 + rounds)
            original, _ = solve_arrays(case, runs=4)
            transformed = dict(case)
            for key in ("mean0", "mean1", "readout"):
                transformed[key] = -2.5 * case[key] + 0.75
            transformed["sigma"] = 2.5 * case["sigma"]
            recalibrated, _ = solve_arrays(transformed, runs=4)
            verify(case, original)
            verify(transformed, recalibrated)
            np.testing.assert_array_equal(original["syndrome_history"], recalibrated["syndrome_history"])
            final_difference = np.bitwise_xor.reduce(original["increments"] ^ recalibrated["increments"], axis=1)
            basis = row_basis(case["stabilizers"])
            self.assertTrue(all(in_row_space(row, basis) for row in final_difference))

    def test_uninformative_and_deterministic_probabilities(self):
        checks = np.zeros((3, 4), dtype=np.uint8)
        code = checks, np.eye(4, dtype=np.uint8), np.eye(3, dtype=np.uint8)
        case, _, _ = generate(code, 8, 3, 0.1, 1.0, 912)
        case["data_error_prob"][:] = np.array([0.0, 1.0, 0.0, 1.0])
        case["mean1"] = case["mean0"].copy()
        answer, _ = solve_arrays(case, runs=4)
        verify(case, answer)
        np.testing.assert_array_equal(answer["increments"], np.broadcast_to(
            np.array([0, 1, 0, 1], dtype=np.uint8), (8, 3, 4)))

    def test_high_confidence_history(self):
        case, _, actual_history = generate(toric2d(7), 16, 4, 0.04, 0.001, 9151)
        answer, _ = solve_arrays(case, runs=4)
        verify(case, answer)
        np.testing.assert_array_equal(answer["syndrome_history"], actual_history)

    def test_submission_cli(self):
        case, _, _ = generate(toric2d(3), 4, 3, 0.04, 1.0, 511)
        directory = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            input_path = Path(temporary) / "case.npz"
            output_path = Path(temporary) / "answer.npz"
            np.savez_compressed(input_path, **case)
            subprocess.run([sys.executable, str(directory / "solve.py"),
                            "--input", str(input_path), "--output", str(output_path)], check=True)
            with np.load(output_path, allow_pickle=False) as result:
                answer = {key: result[key] for key in result.files}
            verify(case, answer)


if __name__ == "__main__":
    unittest.main(verbosity=2)
