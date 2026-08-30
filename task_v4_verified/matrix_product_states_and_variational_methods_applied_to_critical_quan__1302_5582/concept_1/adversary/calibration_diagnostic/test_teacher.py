"""Private teacher equivalence and a one-sweep generation-time smoke test."""

import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import hashlib
import json
from pathlib import Path
import sys
import time
import unittest
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "participant/baseline"))
sys.path.insert(0, str(ROOT / "evaluator"))

import numpy as np
import mps
import trusted_contractor
from hidden import teacher
from hidden.suite import cases


def pair_inputs(complex_values=False):
    request = {"n_sites": 4, "local_dim": 3, "bond_cap": 2, "sector": "any",
               "omega": [0.7, 1.1, 0.9, 1.3], "mass2": [-0.4, 0.2, -0.1, 0.3],
               "lambda4": [1.8, 2.1, 1.6, 2.0], "coupling": [0.8, 0.5, 1.1],
               "field": [0.01, 0.0, -0.02, 0.0]}
    generator = np.random.default_rng(127)
    bonds = [1, 2, 2, 2, 1]
    tensors = []
    for site in range(4):
        shape = (bonds[site], 3, bonds[site + 1])
        tensor = generator.normal(size=shape)
        if complex_values:
            tensor = tensor + 1j * generator.normal(size=shape)
        tensors.append(tensor)
    tensors = mps.right_canonical(tensors)
    orthogonal, triangular = np.linalg.qr(tensors[0].reshape(3, 2))
    tensors[0] = orthogonal.reshape(1, 3, 2)
    tensors[1] = np.tensordot(triangular, tensors[1], axes=(1, 0))
    mpo = mps.make_mpo(request)
    left = mps.left_step(np.ones((1, 1, 1)), tensors[0], mpo[0])
    right = mps.right_step(np.ones((1, 1, 1)), tensors[3], mpo[3])
    return tensors[1], tensors[2], left, right, mpo[1], mpo[2]


def pair_vector(pair):
    return np.tensordot(pair[0], pair[1], axes=(2, 0)).ravel()


class TeacherTests(unittest.TestCase):
    def setUp(self):
        self.original_pair = mps.optimize_pair

    def tearDown(self):
        mps.optimize_pair = self.original_pair

    def test_random_real_and_complex_operator_equivalence(self):
        generator = np.random.default_rng(451)
        for complex_values in (False, True):
            for left_bond, right_bond, first_dim, second_dim in ((1, 2, 2, 3), (2, 3, 3, 2), (3, 2, 2, 2)):
                with self.subTest(complex_values=complex_values, bonds=(left_bond, right_bond)):
                    shapes = ((left_bond, 2, left_bond), (2, 3, first_dim, first_dim),
                              (3, 2, second_dim, second_dim), (right_bond, 2, right_bond),
                              (left_bond, first_dim, second_dim, right_bond))
                    arguments = []
                    for shape in shapes:
                        array = generator.normal(size=shape)
                        if complex_values:
                            array = array + 1j * generator.normal(size=shape)
                        arguments.append(array)
                    expected = np.einsum("awb,wxpq,xyrs,cyf,bqsf->aprc", *arguments, optimize=False)
                    np.testing.assert_allclose(teacher._apply_pair(*arguments), expected,
                                               rtol=5e-12, atol=5e-12)

    def test_pair_solve_and_svd_match_baseline(self):
        for complex_values in (False, True):
            arguments = pair_inputs(complex_values)
            for direction in ("left", "right"):
                with self.subTest(complex_values=complex_values, direction=direction):
                    expected = pair_vector(self.original_pair(*arguments, 2, direction, 1e-10, 60))
                    actual = pair_vector(teacher.optimize_pair(*arguments, 2, direction, 1e-10, 60))
                    np.testing.assert_allclose(np.outer(actual, actual.conj()),
                                               np.outer(expected, expected.conj()), atol=2e-8, rtol=2e-8)

    def test_eigsh_parameters_pass_through(self):
        arguments = pair_inputs()
        theta = np.tensordot(arguments[0], arguments[1], axes=(2, 0))

        def fake_eigsh(operator, **kwargs):
            self.assertEqual(kwargs["tol"], 7e-8)
            self.assertEqual(kwargs["maxiter"], 13)
            self.assertEqual(kwargs["ncv"], min(20, theta.size))
            self.assertEqual(kwargs["which"], "SA")
            self.assertEqual(kwargs["k"], 1)
            np.testing.assert_allclose(kwargs["v0"], theta.ravel() / np.linalg.norm(theta))
            return np.array([0.0]), kwargs["v0"][:, None]

        with mock.patch.object(teacher, "eigsh", side_effect=fake_eigsh):
            teacher.optimize_pair(*arguments, 2, "right", 7e-8, 13)

    def test_arpack_empty_fallback_matches_baseline(self):
        arguments = pair_inputs(True)
        size = np.tensordot(arguments[0], arguments[1], axes=(2, 0)).size

        def fail(*args, **kwargs):
            raise teacher.ArpackNoConvergence("test", np.empty(0), np.empty((size, 0), dtype=complex))

        with mock.patch.object(mps, "eigsh", side_effect=fail):
            expected = pair_vector(self.original_pair(*arguments, 2, "left", 1e-9, 9))
        with mock.patch.object(teacher, "eigsh", side_effect=fail):
            actual = pair_vector(teacher.optimize_pair(*arguments, 2, "left", 1e-9, 9))
        np.testing.assert_allclose(actual, expected, atol=1e-13)

    def test_install_is_targeted_and_idempotent(self):
        numpy_path = np.einsum_path
        numpy_contraction = np.einsum
        original_sweep = mps.sweep
        teacher.install()
        teacher.install()
        self.assertIs(mps.optimize_pair, teacher.optimize_pair)
        self.assertIs(mps.sweep, original_sweep)
        self.assertIs(np.einsum_path, numpy_path)
        self.assertIs(np.einsum, numpy_contraction)

    def test_q7f1_one_sweep(self):
        seed = ROOT / "evaluator/hidden/states/q7f1_baseline_short.npz"
        if not seed.exists():
            self.skipTest("main archived the baseline seed")
        request = next(request for _, request in cases() if request["case_id"] == "q7f1")
        tensors = trusted_contractor.load_mps(seed, request)
        baseline = trusted_contractor.measure(tensors, request)
        teacher.install()
        beginning = time.process_time()
        tensors = mps.sweep(tensors, mps.make_mpo(request, parity_bias=2.0), request["bond_cap"],
                            tolerance=2e-9, maxiter=80, deadline=beginning + 10.0)
        cpu_seconds = time.process_time() - beginning
        retained = OUTPUT / "teacher_q7f1_smoke.npz"
        trusted_contractor.save_mps(retained, tensors)
        measured = trusted_contractor.measure(trusted_contractor.load_mps(retained, request), request)
        report = {"baseline": baseline, "measurement": measured, "cpu_seconds": cpu_seconds,
                  "baseline_gap": baseline["energy"] - measured["energy"],
                  "teacher_sha256": hashlib.sha256((ROOT / "evaluator/hidden/teacher.py").read_bytes()).hexdigest(),
                  "state_sha256": hashlib.sha256(retained.read_bytes()).hexdigest(),
                  "full_budgeted_solver_certification": False}
        (OUTPUT / "teacher_q7f1_smoke.json").write_text(json.dumps(report, indent=2) + "\n")
        self.assertGreater(report["baseline_gap"], 1e-7 * request["n_sites"])
        self.assertLessEqual(measured["max_bond"], request["bond_cap"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
