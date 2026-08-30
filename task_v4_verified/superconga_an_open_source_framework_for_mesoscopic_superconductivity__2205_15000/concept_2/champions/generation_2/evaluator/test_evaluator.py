import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from evaluate import ROOT, evaluate


class EvaluatorTests(unittest.TestCase):
    def test_private_feasibility_witness(self):
        result = evaluate(ROOT / "evaluator" / "hidden" / "feasible_design")
        self.assertTrue(result["valid"])
        self.assertTrue(result["passed"])
        self.assertGreater(result["core_score"], 1 - 1e-10)

    def test_bad_artifacts_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "design.json"
            for content in ({"pattern": [0] * 64}, {"pattern": [0] * 63},
                            {"pattern": [0.375] * 64}, {"pattern": [float("nan")] * 64},
                            {"pattern": [float("inf")] * 64}):
                artifact.write_text(json.dumps(content))
                result = evaluate(directory)
                self.assertFalse(result["valid"])
                self.assertFalse(result["passed"])
                self.assertEqual(result["core_score"], 0)

    def test_missing_and_oversized_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(evaluate(directory)["valid"])
            (Path(directory) / "design.json").write_text(" " * 65537)
            self.assertFalse(evaluate(directory)["valid"])

    def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "design.json").symlink_to(ROOT / "evaluator" / "hidden" / "feasible_design" / "design.json")
            self.assertFalse(evaluate(directory)["valid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
