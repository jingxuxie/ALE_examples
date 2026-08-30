import hashlib
import json
from pathlib import Path
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
HIDDEN = ROOT / "evaluator" / "hidden"
NEW_CASES = ("case_10", "case_11", "case_18", "case_19")


class GenerationTwo(unittest.TestCase):
    def test_new_reference_certificates_and_physical_inputs(self):
        for case_id in NEW_CASES:
            certificate = json.loads((HIDDEN / "references" / (case_id + ".json")).read_text())
            self.assertTrue(certificate["valid"])
            self.assertGreater(certificate["normal_pairing_eigenvalue"], 1)
            self.assertGreater(certificate["minimum_low_gap_over_piT"], 1e-9)
            self.assertLess(certificate["second_start_all_frequency"]["branch_error"], 2e-6)
            for key in ("primary_all_frequency", "second_start_all_frequency", "primary_direct_rows", "second_start_direct_rows"):
                self.assertLess(certificate[key]["gap_residual"], 5e-11)
                self.assertLess(certificate[key]["z_residual"], 5e-11)
            for folder, key in (("cases", "instance_sha256"), ("references", "reference_sha256")):
                path = HIDDEN / folder / (case_id + ".npz")
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), certificate[key])
            with np.load(HIDDEN / "cases" / (case_id + ".npz"), allow_pickle=False) as instance:
                self.assertAlmostEqual(float(instance["weights"].sum()), 1)
                self.assertTrue(np.all(instance["weights"] > 0))
                self.assertTrue(np.all(instance["omega"] > 0))
                self.assertTrue(np.all(instance["coupling"] >= 0))
                self.assertTrue(np.all(instance["coulomb"] >= 0))
                np.testing.assert_array_equal(instance["coupling"], instance["coupling"].transpose(0, 2, 1))
                np.testing.assert_array_equal(instance["coulomb"], instance["coulomb"].T)
            with np.load(HIDDEN / "references" / (case_id + ".npz"), allow_pickle=False) as reference:
                self.assertTrue(np.all(reference["delta"][:, 0] > 0))
                self.assertTrue(np.all(np.any(reference["delta"] < 0, axis=1)))

    def test_actual_v3_has_branch_not_resource_failures(self):
        report = json.loads((ROOT / "attempts" / "previous_fresh_report.json").read_text())
        records = {record["case_id"]: record for record in report["cases"]}
        self.assertEqual({case_id for case_id, record in records.items() if not record["accepted"]}, set(NEW_CASES))
        for case_id in NEW_CASES:
            record = records[case_id]
            self.assertEqual(record["returncode"], 0)
            self.assertLess(record["cpu_seconds"], 12)
            self.assertGreater(record["branch_error"], 0.04)
            self.assertTrue(record["sign_correct"])
        for case_id in ("case_10", "case_11"):
            self.assertLessEqual(records[case_id]["gap_residual"], 2e-8)
            self.assertLessEqual(records[case_id]["z_residual"], 2e-9)
            self.assertGreater(records[case_id]["branch_error"], 0.99)

    def test_original_large_grids_are_retained(self):
        manifest = json.loads((HIDDEN / "manifest.json").read_text())
        self.assertEqual(manifest["generation"], 2)
        self.assertEqual(len(manifest["cases"]), 20)
        for family in ("multiband", "retardation", "critical", "weak_interband", "combined"):
            self.assertEqual(sum(record["family"] == family for record in manifest["cases"]), 4)
        for case_id in ("case_08", "case_09", "case_16", "case_17"):
            with np.load(HIDDEN / "cases" / (case_id + ".npz"), allow_pickle=False) as instance:
                self.assertEqual(int(instance["n_freq"]), 32768)
                self.assertEqual(len(instance["weights"]), 40)
        for case_id in NEW_CASES:
            with np.load(HIDDEN / "cases" / (case_id + ".npz"), allow_pickle=False) as instance:
                self.assertLessEqual(int(instance["n_freq"]), 4096)
                self.assertLessEqual(len(instance["weights"]), 15)

    def test_reduced_model_changes_instability_count(self):
        report = json.loads((ROOT / "adversary" / "linear_diagnostic.json").read_text())
        self.assertTrue(report["candidate_code_imported_only_in_sandbox_child"])
        for record in report["cases"]:
            full = np.array(record["full_linear_eigenvalues"])
            reduced = np.array(record["reduced_linear_eigenvalues"])
            self.assertGreater(np.count_nonzero(full > 1), np.count_nonzero(reduced > 1))


if __name__ == "__main__":
    unittest.main()
