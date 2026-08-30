import hashlib
import json
from pathlib import Path
import unittest

import numpy as np


POOL = Path(__file__).resolve().parent
ROOT = POOL.parents[1]
PLAN = json.loads((POOL / "plan.json").read_text())


def load_case(case_id):
    directory = POOL / "cases" / case_id
    with np.load(directory / "instance.npz", allow_pickle=False) as archive:
        instance = {key: archive[key] for key in archive.files}
    with np.load(directory / "reference.npz", allow_pickle=False) as archive:
        reference = {key: archive[key] for key in archive.files}
    return instance, reference


class PoolAudit(unittest.TestCase):
    def test_case_count_and_nonactivated_scope(self):
        manifest = json.loads((POOL / "manifest.json").read_text())
        self.assertFalse(PLAN["active"])
        self.assertFalse(manifest["active"])
        self.assertEqual(len(manifest["cases"]), 12)
        self.assertTrue(all(record["certified"] for record in manifest["cases"]))
        originals = [record for record in PLAN["specifications"] if record["profile"] == "original"]
        self.assertEqual(len(originals), 8)
        self.assertEqual({record["family"] for record in originals}, {"multiband", "retardation", "critical", "weak_interband", "combined"})

    def test_new_seeds_and_honest_domain_labels(self):
        original_manifest = json.loads((ROOT / "evaluator" / "hidden" / "manifest.json").read_text())
        old_seeds = {record["seed"] for record in original_manifest["cases"]}
        for specification in PLAN["specifications"]:
            self.assertNotIn(specification["seed"], old_seeds)
            parameters = json.loads((POOL / "cases" / specification["case_id"] / "parameters.json").read_text())
            original = specification["profile"] == "original"
            self.assertEqual(parameters["in_original_parameter_contract"], original)
            if original:
                self.assertLessEqual(parameters["n_freq"], 2048)
            else:
                self.assertIn(parameters["n_freq"], (4096, 8192))
                self.assertAlmostEqual(parameters["phonon_ratio"], 500.0)

    def test_reference_integrity_and_cross_start_certificates(self):
        for specification in PLAN["specifications"]:
            directory = POOL / "cases" / specification["case_id"]
            certificate = json.loads((directory / "certificate.json").read_text())
            self.assertTrue(certificate["valid"])
            self.assertEqual(certificate["instance_sha256"], hashlib.sha256((directory / "instance.npz").read_bytes()).hexdigest())
            self.assertEqual(certificate["solution_sha256"], hashlib.sha256((directory / "reference.npz").read_bytes()).hexdigest())
            for label in ("direct_sum_primary", "direct_sum_second_start"):
                self.assertLess(certificate[label]["gap_residual"], 5e-11)
                self.assertLess(certificate[label]["z_residual"], 5e-11)
                self.assertTrue(certificate[label]["sign_correct"])
            self.assertLess(certificate["direct_sum_second_start"]["branch_error"], 2e-6)
            self.assertGreater(certificate["max_low_frequency_gap_over_pi_temperature"], 1e-4)
            self.assertGreater(certificate["normal_state_pairing_eigenvalue"], 1.000005)

    def test_low_temperature_pairs_preserve_cutoff_and_spectrum(self):
        for first_id, second_id in (("pool_08", "pool_09"), ("pool_10", "pool_11")):
            first, unused = load_case(first_id)
            second, unused = load_case(second_id)
            self.assertEqual(int(second["n_freq"]), 2 * int(first["n_freq"]))
            self.assertAlmostEqual(float(first["temperature"]), 2 * float(second["temperature"]))
            np.testing.assert_array_equal(first["omega"], second["omega"])
            np.testing.assert_array_equal(first["weights"], second["weights"])
            np.testing.assert_array_equal(first["coulomb"], second["coulomb"])
            first_cutoff = np.pi * float(first["temperature"]) * (2 * int(first["n_freq"]) - 1)
            second_cutoff = np.pi * float(second["temperature"]) * (2 * int(second["n_freq"]) - 1)
            self.assertLess(abs(first_cutoff / second_cutoff - 1), 7e-5)
            if first_id == "pool_08":
                np.testing.assert_array_equal(first["coupling"], second["coupling"])

    def test_critical_pair_has_recorded_physical_calibration(self):
        for case_id in ("pool_10", "pool_11"):
            parameters = json.loads((POOL / "cases" / case_id / "parameters.json").read_text())
            self.assertLess(abs(parameters["linear_eigenvalue"] - 1.00003), 2e-8)
            self.assertGreater(len(parameters["calibration"]), 2)
            self.assertGreater(parameters["critical_coupling_multiplier"], 0)

    def test_independent_full_signed_frequency_spot_checks(self):
        for specification in PLAN["specifications"]:
            instance, reference = load_case(specification["case_id"])
            temperature = float(instance["temperature"])
            count = int(instance["n_freq"])
            positive = np.pi * temperature * (2 * np.arange(count) + 1)
            signed = np.concatenate((-positive[::-1], positive))
            delta = reference["delta"]
            full_delta = np.concatenate((delta[:, ::-1], delta), axis=1)
            radius = np.hypot(signed, full_delta)
            selected = np.unique([0, 1, count // 7, count // 2, count - 1])
            differences = positive[selected, None] - signed[None, :]
            normal = np.zeros((len(instance["weights"]), len(selected)))
            pairing = np.zeros_like(normal)
            for mode_index, energy in enumerate(instance["omega"]):
                kernel = energy ** 2 / (energy ** 2 + differences ** 2)
                weighted = instance["coupling"][mode_index] * instance["weights"]
                normal += weighted @ ((signed / radius) @ kernel.T)
                pairing += weighted @ ((full_delta / radius) @ kernel.T)
            pairing -= ((instance["coulomb"] * instance["weights"]) @ (full_delta / radius).sum(axis=1))[:, None]
            expected_z = 1 + np.pi * temperature * normal / positive[selected]
            expected_delta = np.pi * temperature * pairing / expected_z
            scale = np.maximum(np.max(np.abs(delta), axis=1), np.pi * temperature * 1e-10)
            self.assertLess(float(np.max(np.abs(delta[:, selected] - expected_delta) / scale[:, None])), 5e-11)
            self.assertLess(float(np.max(np.abs(reference["z"][:, selected] - expected_z) / np.maximum(1, expected_z))), 5e-11)

    def test_measured_resource_claims_are_supported(self):
        report = json.loads((POOL / "champion_report.json").read_text())
        self.assertFalse(report["active"])
        self.assertFalse(report["active_task_or_target_modified"])
        self.assertFalse(report["fresh_agent_launched"])
        self.assertLessEqual(report["aggregate_cpu_seconds"], 901)
        self.assertEqual(report["candidate_resources"]["cpu_seconds"], 12)
        self.assertEqual(report["candidate_resources"]["threads"], 1)
        self.assertEqual(report["candidate_resources"]["memory_mb"], 2048)
        for measurement in report["measurements"]:
            if measurement["accepted"]:
                self.assertEqual(measurement["execution"]["returncode"], 0)
                self.assertLessEqual(measurement["execution"]["cpu_seconds"], 12)
                self.assertLessEqual(measurement["quality"]["gap_residual"], 2e-8)
                self.assertLessEqual(measurement["quality"]["z_residual"], 2e-9)
                self.assertLessEqual(measurement["quality"]["branch_error"], 0.002)

    def test_read_only_sources_unchanged(self):
        report = json.loads((POOL / "champion_report.json").read_text())
        self.assertEqual(report["source_hash_mismatches"], [])
        for relative, expected in report["source_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
