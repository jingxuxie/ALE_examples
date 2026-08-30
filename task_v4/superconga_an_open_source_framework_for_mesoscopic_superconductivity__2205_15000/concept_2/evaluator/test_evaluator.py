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
        config = json.loads((ROOT / "participant" / "input" / "device.json").read_text())
        count = len(config["candidates"])
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "design.json"
            for content in ({"pattern": [0] * count}, {"pattern": [0] * (count - 1)},
                            {"pattern": [0.375] * count}, {"pattern": [float("nan")] * count},
                            {"pattern": [float("inf")] * count}):
                artifact.write_text(json.dumps(content))
                result = evaluate(directory)
                self.assertFalse(result["valid"])
                self.assertFalse(result["passed"])
                self.assertEqual(result["core_score"], 0)

    def test_disconnected_exact_budget_artifact_is_rejected(self):
        config = json.loads((ROOT / "participant" / "input" / "device.json").read_text())
        coordinates = [tuple(coordinate) for coordinate in config["candidates"]]
        center = (config["width"] // 2, config["height"] // 2)
        neighbors = {(center[0] + offset[0], center[1] + offset[1])
                     for offset in ((1, 0), (-1, 0), (0, 1), (0, -1))}
        self.assertTrue(neighbors.issubset(set(coordinates)))
        selected = set(neighbors)
        for coordinate in coordinates:
            if len(selected) == config["normal_site_count"]:
                break
            if coordinate != center:
                selected.add(coordinate)
        pattern = [int(coordinate in selected) for coordinate in coordinates]
        self.assertEqual(sum(pattern), config["normal_site_count"])
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "design.json").write_text(json.dumps({"pattern": pattern}))
            result = evaluate(directory)
            self.assertFalse(result["valid"])
            self.assertIn("connected", result["reason"])

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
