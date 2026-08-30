"""Black-box malformed-output and trusted scorer contract checks."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest

import numpy as np

from evaluate import ROOT, check_submission, evaluate, run_guarded
from scoring import parse_predictions, score_predictions


class EvaluatorTests(unittest.TestCase):
    observations = []

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="malformed-", dir=ROOT / "adversary")
        self.addCleanup(self.temporary.cleanup)
        self.submission = Path(self.temporary.name) / "submission"
        self.submission.mkdir()
        shutil.copyfile(ROOT / "adversary/fixture.py", self.submission / "solver.py")
        self.settings = json.loads((ROOT / "evaluator/settings.json").read_text())

    def run_fixture(self, mode):
        (self.submission / "mode.txt").write_text(mode)
        report = evaluate(self.submission, split="validation")
        self.observations.append({"case": mode, "report": report})
        return report

    @classmethod
    def tearDownClass(cls):
        (ROOT / "adversary/malformed_reports.json").write_text(json.dumps(cls.observations, indent=2) + "\n")

    def test_malformed_outputs(self):
        for mode in ("wrong_count", "wrong_shape", "boolean", "string", "nan", "infinity",
                     "extra_key", "missing", "truncated", "duplicate_key", "oversized", "symlink"):
            with self.subTest(mode=mode):
                report = self.run_fixture(mode)
                self.assertFalse(report["valid"], report)
                self.assertFalse(report["passed"])
                self.assertEqual(report["core_score"], 0.0)

    def test_zero_predictions_valid_but_fail_accuracy(self):
        report = self.run_fixture("zero")
        self.assertTrue(report["valid"], report)
        self.assertFalse(report["passed"])
        self.assertEqual(report["reason"], "accuracy_target_not_met")

    def test_staged_input_has_no_labels(self):
        report = self.run_fixture("public_inputs_only")
        self.assertTrue(report["valid"], report)

    def test_flood_is_bounded(self):
        report = self.run_fixture("flood")
        self.assertFalse(report["valid"])
        self.assertEqual(report["reason"], "stdout_stderr_limit_exceeded")

    def test_memory_is_bounded(self):
        report = self.run_fixture("memory")
        self.assertFalse(report["valid"])
        self.assertIn("MemoryError", report["runtime"]["diagnostic"])

    def test_wall_guard_kills_and_reaps(self):
        (self.submission / "mode.txt").write_text("timeout")
        scratch = Path(self.temporary.name) / "scratch"
        scratch.mkdir()
        request = scratch / "request.json"
        request.write_text('{"n_instances":256}')
        settings = dict(self.settings, wall_seconds=0.5)
        report = run_guarded(["/usr/bin/python3", str(self.submission / "solver.py"),
                              str(request), str(scratch / "predictions.json")], {},
                             self.submission, scratch, settings)
        self.observations.append({"case": "shortened_test_only_wall_guard", "report": report})
        self.assertEqual(report["failure"], "wall_time_limit_exceeded")
        self.assertLess(report["wall_seconds"], 3.0)

    def test_path_overlap_rejected(self):
        with self.assertRaises(ValueError):
            check_submission(ROOT, self.settings)
        with self.assertRaises(ValueError):
            check_submission(ROOT / "evaluator/hidden", self.settings)

    def test_submission_symlink_rejected(self):
        (self.submission / "leak").symlink_to(ROOT / "evaluator/hidden/test.npz")
        with self.assertRaises(ValueError):
            check_submission(self.submission, self.settings)

    def test_metric_boundary_and_order(self):
        families = np.repeat(np.arange(4), 64)
        labels = np.ones((256, 2))
        exact = score_predictions(labels.copy(), labels, families, self.settings)
        self.assertTrue(exact["accuracy_passed"])
        self.assertEqual(exact["core_score"], 1.0)
        predictions = labels + [0.029, 0.019]
        self.assertTrue(score_predictions(predictions, labels, families, self.settings)["accuracy_passed"])
        predictions[:64, 0] += 0.06
        self.assertFalse(score_predictions(predictions, labels, families, self.settings)["accuracy_passed"])
        permutation = np.random.default_rng(17).permutation(256)
        shuffled = score_predictions(predictions[permutation], labels[permutation], families[permutation], self.settings)
        original = score_predictions(predictions, labels, families, self.settings)
        self.assertAlmostEqual(shuffled["core_score"], original["core_score"])
        self.assertAlmostEqual(shuffled["worst_family_score"], original["worst_family_score"])

    def test_parser_nonfinite_overflow_and_boolean_version(self):
        for text in ('{"schema_version":1,"predictions":[[1e999,0]]}',
                     '{"schema_version":true,"predictions":[[0,0]]}',
                     '{"schema_version":1,"predictions":[[1e101,0]]}'):
            with self.assertRaises(ValueError):
                parse_predictions(text, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
