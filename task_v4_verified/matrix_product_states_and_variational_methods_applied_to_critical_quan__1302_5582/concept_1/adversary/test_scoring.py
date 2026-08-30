import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import aggregate, quality


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.scoring = json.loads((ROOT / "participant/input/scoring.json").read_text())

    def rows(self, value, valid=True):
        return [{"family": family, "stages": {
            "short": {"quality": value, "valid": valid, "cpu_seconds": 1.0},
            "long": {"quality": value, "valid": valid, "cpu_seconds": 1.0}}}
            for family in ("symmetric", "crossover", "double_well", "inhomogeneous")]

    def test_quality_endpoints(self):
        self.assertEqual(quality(12.0, 12.0, 10.0, 10), 0.0)
        self.assertEqual(quality(10.0, 12.0, 10.0, 10), 1.0)
        self.assertEqual(quality(9.0, 12.0, 10.0, 10), 1.0)
        self.assertEqual(quality(13.0, 12.0, 10.0, 10), 0.0)

    def test_log_gap_closure(self):
        self.assertAlmostEqual(quality(10.02, 12.0, 10.0, 10), 0.5)

    def test_passing_score(self):
        report = aggregate(self.rows(1.0), self.scoring)
        self.assertTrue(report["passed"])
        self.assertTrue(report["valid"])
        self.assertAlmostEqual(report["score"], 99.875)
        self.assertEqual(report["core_score"], report["core"])
        self.assertEqual(report["worst_family_score"], report["worst_family"])

    def test_invalid_output_fails(self):
        report = aggregate(self.rows(1.0, valid=False), self.scoring)
        self.assertFalse(report["passed"])
        self.assertFalse(report["valid"])
        self.assertIn("invalid", report["reason"])

    def test_worst_family_guard(self):
        rows = self.rows(1.0)
        rows[-1]["stages"]["short"]["quality"] = 0.0
        rows[-1]["stages"]["long"]["quality"] = 0.5
        report = aggregate(rows, self.scoring)
        self.assertFalse(report["passed"])
        self.assertTrue(report["valid"])
        self.assertLess(report["worst_family_score"], 0.7)


if __name__ == "__main__":
    unittest.main()
