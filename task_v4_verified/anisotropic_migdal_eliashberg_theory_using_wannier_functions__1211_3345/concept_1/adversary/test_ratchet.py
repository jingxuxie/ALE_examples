"""Private final-ratchet checks, copied into the inactive package before running."""

import hashlib
import json
from pathlib import Path
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HIDDEN = ROOT / "evaluator" / "hidden"
NEW_CASES = ("case_06", "case_07", "case_16", "case_17")


class GenerationThree(unittest.TestCase):
    def test_resolved_noncommuting_spectral_inputs(self):
        manifest = json.loads((HIDDEN / "manifest.json").read_text())
        records = {record["case_id"]: record for record in manifest["cases"]}
        for case_id in NEW_CASES:
            record = records[case_id]
            self.assertEqual(record["n_modes"], 96)
            self.assertLess(record["normalized_kernel_difference_vs_192_bins"], 1e-8)
            self.assertGreater(record["spectral_matrix_rank_relative_1e_8"], 50)
            self.assertGreater(record["maximum_relative_noncommutator"], 0.05)
            self.assertGreater(record["minimum_patch_singular_ratio"], 1e-10)
            self.assertLess(record["integrated_lambda_max"], 2)
            self.assertGreater(record["integrated_lambda_min"], 0)
            self.assertAlmostEqual(record["finite_cutoff_over_physical_phonon_upper"], 17.157, places=2)
            with np.load(HIDDEN / "cases" / (case_id + ".npz"), allow_pickle=False) as instance:
                self.assertEqual(len(np.unique(instance["omega"])), 96)
                self.assertTrue(np.all(instance["omega"] > 0))
                self.assertTrue(np.all(instance["weights"] > 0))
                self.assertAlmostEqual(float(instance["weights"].sum()), 1)
                self.assertTrue(np.all(instance["coupling"] > 0))
                self.assertTrue(np.all(instance["coulomb"] >= 0))
                np.testing.assert_allclose(instance["coupling"], instance["coupling"].transpose(0, 2, 1), rtol=0, atol=1e-13)
                np.testing.assert_allclose(instance["coulomb"], instance["coulomb"].T, rtol=0, atol=1e-13)

    def test_independent_nonzero_branch_certificates(self):
        for case_id in NEW_CASES:
            certificate = json.loads((HIDDEN / "references" / (case_id + ".json")).read_text())
            self.assertTrue(certificate["valid"])
            self.assertGreater(certificate["normal_pairing_eigenvalue"], 1.0001)
            self.assertGreater(certificate["minimum_low_gap_over_piT"], 1e-7)
            self.assertLess(certificate["second_start_all_frequency"]["branch_error"], 1e-6)
            self.assertEqual(certificate["initial_amplitude_factors"], [0.65, 1.5])
            for key in ("primary_all_frequency", "second_start_all_frequency", "primary_direct_rows", "second_start_direct_rows"):
                self.assertLess(certificate[key]["gap_residual"], 5e-12)
                self.assertLess(certificate[key]["z_residual"], 5e-12)
            for folder, key in (("cases", "instance_sha256"), ("references", "reference_sha256")):
                path = HIDDEN / folder / (case_id + ".npz")
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), certificate[key])

    def test_actual_v4_fails_only_selected_resource_cases(self):
        report = json.loads((ROOT / "attempts" / "previous_fresh_report.json").read_text())
        self.assertEqual(report["core_score"], 0.8)
        self.assertEqual(report["worst_family_score"], 0.5)
        self.assertFalse(report["passed"])
        failures = {record["case_id"]: record for record in report["cases"] if not record["accepted"]}
        self.assertEqual(set(failures), set(NEW_CASES))
        for record in failures.values():
            self.assertEqual(record["returncode"], -24)
            self.assertGreater(record["cpu_seconds"], 11.5)
            self.assertFalse(record["wall_timeout"])

    def test_all_other_cases_are_preserved(self):
        retained = json.loads((ROOT / "adversary" / "retained_case_hashes.json").read_text())
        self.assertEqual(len(retained), 32)
        for relative, expected in retained.items():
            self.assertEqual(hashlib.sha256((HIDDEN / relative).read_bytes()).hexdigest(), expected)
        for case_id in ("case_10", "case_11", "case_18", "case_19"):
            certificate = json.loads((HIDDEN / "references" / (case_id + ".json")).read_text())
            self.assertTrue(certificate["valid"])
            self.assertLess(certificate["second_start_all_frequency"]["branch_error"], 2e-6)
        for case_id in ("case_08", "case_09"):
            with np.load(HIDDEN / "cases" / (case_id + ".npz"), allow_pickle=False) as instance:
                self.assertEqual(int(instance["n_freq"]), 32768)
                self.assertEqual(len(instance["weights"]), 40)

    def test_extended_resource_margin_is_not_target_attainability(self):
        evidence = json.loads((ROOT / "adversary" / "continuum_evidence.json").read_text())
        self.assertEqual(len(evidence["cases"]), 4)
        self.assertFalse(evidence["joint_12_cpu_attainability_established"])
        for record in evidence["cases"]:
            extended = record["deadline_lifted_control"]
            self.assertGreater(extended["execution"]["cpu_seconds"], 24)
            if extended["output_available"]:
                self.assertTrue(extended["quality_passed"])
            else:
                self.assertEqual(extended["execution"]["returncode"], -24)

    def test_balanced_families_and_independent_public_example(self):
        manifest = json.loads((HIDDEN / "manifest.json").read_text())
        self.assertEqual(manifest["generation"], 3)
        self.assertEqual(len(manifest["cases"]), 20)
        for family in ("multiband", "retardation", "critical", "weak_interband", "combined"):
            self.assertEqual(sum(record["family"] == family for record in manifest["cases"]), 4)
        example = ROOT / "participant" / "input" / "examples" / "phonon_continuum_96.npz"
        with np.load(example, allow_pickle=False) as instance:
            self.assertEqual(len(instance["omega"]), 96)
            self.assertEqual(int(instance["n_freq"]), 4096)
        hidden_hashes = {hashlib.sha256(path.read_bytes()).hexdigest() for path in (HIDDEN / "cases").glob("*.npz")}
        self.assertNotIn(hashlib.sha256(example.read_bytes()).hexdigest(), hidden_hashes)


if __name__ == "__main__":
    unittest.main()
