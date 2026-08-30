import sys

sys.dont_write_bytecode = True

from collections import Counter
import json
import math
from pathlib import Path
import time
import unittest

import numpy as np

import stress


class StressAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((stress.PRIVATE / "stress_report.json").read_text())
        cls.artifact = json.loads((stress.PRIVATE / "known_witness.json").read_text())
        cls.checker = stress.module("stress_test_checker", "participant/workspace/check.py")
        cls.graph, cls.projection = stress.geometry()

    def test_frozen_integrity_and_original_witness(self):
        self.assertEqual(stress.verify_frozen(), self.report["frozen_manifest_sha256_unchanged"])
        manifest = json.loads((stress.ROOT / "evaluator/hidden/frozen_manifest.json").read_text())
        self.assertEqual(stress.sha256(stress.PRIVATE / "known_witness.json"), manifest["known_private_witness_sha256"])

    def test_deterministic_families(self):
        fields = list(stress.spatial_fields(0, 1))
        self.assertEqual(Counter(family for family, name, field in fields), {"row_corners": 14, "column_corners": 30, "quadrant_corners": 14, "local_2x2_patch": 24})
        self.assertEqual(list(stress.spatial_fields(3, 41)), list(stress.spatial_fields(3, 41)))

    def test_no_global_budget_drift(self):
        rates = np.array(self.artifact["probabilities"])
        for case in self.report["cases"]:
            factors = np.array(case["multipliers"])
            self.assertLessEqual(float(np.max(np.abs(factors - 1))), case["amplitude"] + 1e-14)
            self.assertAlmostEqual(float(np.dot(rates, factors)), float(sum(rates)), places=13)
            self.assertTrue(np.all(1.05 * rates * factors < 0.5))
        self.assertIsNone(stress.balanced_levels([1] * 20, rates, self.projection))

    def test_nominal_metrics_match_frozen_checker(self):
        original = self.checker.check(self.artifact)
        nominal = self.report["cases"][0]["metrics"]
        self.assertAlmostEqual(original["core_score"], nominal["certified_score"], places=12)
        for field, key in (("certified_gap", "gap"), ("certified_opposite_posterior", "posterior"), ("certified_syndrome_probability", "mass")):
            self.assertAlmostEqual(original[field], nominal["certified"][key], places=12)

    def test_failure_cluster_separates_slack(self):
        totals = self.report["actual_failure_mechanisms"]
        self.assertGreater(totals["lost_gap"], 0)
        self.assertEqual(totals["lost_posterior"], 0)
        self.assertEqual(totals["lost_mass"], 0)
        self.assertTrue(self.report["all_profiles_certify_inversion"])
        self.assertTrue(any(case["metrics"]["certificate_only_failure"] for case in self.report["cases"]))

    def test_off_anchor_interval_bounds(self):
        lookup = {case["case_id"]: case for case in self.report["cases"]}
        for case_id in self.report["worst_case_by_actual_metric"].values():
            case = lookup[case_id]
            rates = np.array(self.artifact["probabilities"]) * case["multipliers"]
            physical = case["metrics"]["physical_class"]
            bound = case["metrics"]["certified"]
            for scale in np.linspace(0.950137, 1.049813, 101):
                joint, costs = self.checker.frontier(rates, self.artifact["syndrome"], scale)
                self.assertGreaterEqual(float(costs[1 - physical] - costs[physical]) + 1e-12, bound["gap"])
                self.assertGreaterEqual(float(joint[1 - physical] / sum(joint)) + 1e-12, bound["posterior"])
                self.assertGreaterEqual(float(sum(joint)) + 1e-15, bound["mass"])

    def test_symmetries_include_odd_logical_xor(self):
        self.assertEqual(len(self.report["symmetry_checks"]), 6)
        self.assertTrue(all(check["passed"] for check in self.report["symmetry_checks"]))
        odd = [check for check in self.report["symmetry_checks"] if check["control"] == "odd_syndrome_control" and check["columns_reflected"]]
        self.assertTrue(all(check["logical_xor"] == 1 for check in odd))
        for columns, rows in ((False, True), (True, False), (True, True)):
            reflected, shift = stress.mirror(self.artifact, self.graph, columns, rows)
            restored, second_shift = stress.mirror(reflected, self.graph, columns, rows)
            self.assertEqual(restored, self.artifact)
            self.assertEqual(shift ^ second_shift, 0)

    def test_independent_and_order_checks(self):
        checks = self.report["independent_checks"]
        self.assertEqual(len(checks), 6)
        self.assertTrue(all(check["passed"] and check["mass_relative_error"] < 3e-12 and check["cost_absolute_error"] < 1e-11 for check in checks))
        self.assertTrue({"edge_order_reverse", "edge_order_seeded_permutation", "smallest_amplitude_gap"}.issubset({check["purpose"] for check in checks}))

    def test_output_cannot_escape_adversary(self):
        with self.assertRaises(ValueError):
            stress.private_output(stress.ROOT / "status.json")
        with self.assertRaises(ValueError):
            stress.private_output(stress.ROOT / "participant/forbidden.json")
        self.assertEqual(stress.private_output(stress.PRIVATE / "allowed.json"), (stress.PRIVATE / "allowed.json").resolve())


if __name__ == "__main__":
    started = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(StressAudit)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {"passed": result.wasSuccessful(), "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "elapsed_seconds": time.monotonic() - started, "writes_confined_to": "concept_2/adversary/"}
    (stress.PRIVATE / "stress_audit_report.json").write_text(json.dumps(report, indent=2) + "\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
