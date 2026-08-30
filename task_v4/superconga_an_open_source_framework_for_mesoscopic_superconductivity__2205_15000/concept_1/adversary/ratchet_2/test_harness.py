from common import ASSETS, ROOT, digest, load_corpus, read_json, verify_files, write_json

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import numpy as np
from scipy import ndimage

from checking import GLModel, aggregate, checked_field, compare_topology, energy_gradient, local_polish, physical_flux_error, score_field
from replay import capture_source, classify_controls, result_gate
from runner import quiet_accounting


class HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.policy = load_corpus()
        cls.references = {reference["case_id"]: reference for reference in cls.manifest["cases"]}

    def test_pool_and_predeclared_selection(self):
        self.assertEqual(self.manifest["physical_case_count"], 24)
        self.assertEqual(self.manifest["selected_replay_count"], 13)
        self.assertEqual(len(set(self.manifest["replay_order"])), 13)
        for reference in self.references.values():
            self.assertEqual(reference["selected_for_replay"], reference["reference_gap"] >= 0.5)
        self.assertEqual(self.policy["maximum_concurrent_solvers"], 1)
        self.assertEqual(self.policy["maximum_total_solver_processes"], 32)

    def test_all_references_and_physical_objectives(self):
        records = []
        for reference in self.references.values():
            case = read_json(ROOT / reference["case_path"])
            original = read_json(ROOT / reference["original_case_path"])
            for name in original:
                if name not in ("initial_real", "initial_imag"):
                    self.assertEqual(case[name], original[name])
            baseline = checked_field(ROOT / reference["baseline_path"], case)
            witness = checked_field(ROOT / reference["witness_path"], case)
            self.assertTrue(np.array_equal(baseline, np.asarray(case["initial_real"]) + 1j * np.asarray(case["initial_imag"])))
            for kind, field in (("baseline", baseline), ("witness", witness)):
                energy, unused, rms = energy_gradient(case, field)
                self.assertAlmostEqual(energy, reference[kind + "_energy"], delta=1e-9)
                self.assertLess(rms, self.policy["stationarity_rms_max"])
            metadata = read_json(ROOT / reference["metadata_path"])
            error = physical_flux_error(case, metadata)
            self.assertLess(error, 1e-10)
            self.assertEqual(ndimage.label(np.asarray(case["mask"], dtype=bool))[1], 1)
            self.assertGreater(min(np.min(case["kx"]), np.min(case["ky"])), 0)
            self.assertEqual(reference["witness_energy"], min(candidate["energy"] for candidate in reference["all_preexisting_reference_candidates"]))
            records.append({"case_id": reference["case_id"], "physical_flux_error": error, "initial_equals_reference": True, "reference_gap": reference["reference_gap"]})
        write_json(ROOT / "physical_revalidation.json", {"passed": True, "case_count": len(records), "records": records})

    def test_public_release_snapshot(self):
        release = read_json(ROOT / "provenance/A2_release_manifest.json")
        for relative, expected in release["participant"]["files"].items():
            path = ASSETS / relative
            self.assertEqual(digest(path), expected)
        for relative, expected in release["evaluator"]["files"].items():
            if relative in ("evaluator/evaluate.py", "evaluator/independent.py"):
                self.assertEqual(digest(ASSETS / relative), expected)

    def test_gradient_and_gauge(self):
        reference = self.references["nf04"]
        case = read_json(ROOT / reference["case_path"])
        model = GLModel(case)
        generator = np.random.default_rng(81129)
        vector = generator.normal(size=2 * model.size) * 0.4
        energy, gradient = model.objective(vector)
        direction = generator.normal(size=vector.size)
        direction /= np.linalg.norm(direction)
        numeric = (model.objective(vector + 2e-5 * direction)[0] - model.objective(vector - 2e-5 * direction)[0]) / 4e-5
        self.assertAlmostEqual(numeric, float(gradient @ direction), delta=1e-6)
        field = model.unpack(vector)
        checked_energy, checked_gradient, unused = energy_gradient(case, field)
        self.assertAlmostEqual(energy, checked_energy, delta=1e-9)
        self.assertLess(np.max(abs(gradient - model.pack(checked_gradient))), 1e-10)
        gauge = generator.uniform(-2, 2, size=model.shape)
        transformed = copy.deepcopy(case)
        transformed["ax"] = (np.asarray(case["ax"]) + gauge[:, 1:] - gauge[:, :-1]).tolist()
        transformed["ay"] = (np.asarray(case["ay"]) + gauge[1:] - gauge[:-1]).tolist()
        gauged_energy, gauged_gradient, unused = energy_gradient(transformed, field * np.exp(1j * gauge))
        self.assertAlmostEqual(energy, gauged_energy, delta=1e-9)
        self.assertLess(np.max(abs(gauged_gradient - checked_gradient * np.exp(1j * gauge))), 1e-10)

    def test_topology_is_gauge_invariant(self):
        reference = self.references["nf01"]
        case = read_json(ROOT / reference["case_path"])
        baseline = checked_field(ROOT / reference["baseline_path"], case)
        witness = checked_field(ROOT / reference["witness_path"], case)
        first = compare_topology(case, baseline, witness, self.policy)
        self.assertTrue(first["meaningful"])
        self.assertGreater(first["changed_hole_count"], 10)
        gauge = np.random.default_rng(61422).uniform(-4, 4, size=baseline.shape)
        transformed = copy.deepcopy(case)
        transformed["ax"] = (np.asarray(case["ax"]) + gauge[:, 1:] - gauge[:, :-1]).tolist()
        transformed["ay"] = (np.asarray(case["ay"]) + gauge[1:] - gauge[:-1]).tolist()
        second = compare_topology(transformed, baseline * np.exp(1j * gauge), witness * np.exp(1j * gauge), self.policy)
        self.assertEqual(first["changed_hole_count"], second["changed_hole_count"])
        self.assertEqual(first["changed_vortex_plaquettes"], second["changed_vortex_plaquettes"])

    def test_uniform_zero_field_and_polish(self):
        case = read_json(ROOT / self.references["nf01"]["case_path"])
        mask = np.asarray(case["mask"], dtype=bool)
        case["alpha"] = (-np.ones(mask.shape)).tolist()
        case["beta"] = np.ones(mask.shape).tolist()
        case["ax"] = np.zeros_like(case["ax"]).tolist()
        case["ay"] = np.zeros_like(case["ay"]).tolist()
        field = mask.astype(complex)
        energy, unused, rms = energy_gradient(case, field)
        self.assertAlmostEqual(energy, -case["h"]**2 * mask.sum() / 2)
        self.assertEqual(rms, 0.0)
        polished, report = local_polish(case, field, 2)
        self.assertTrue(report["completed"])
        self.assertAlmostEqual(report["gain"], 0.0)
        self.assertTrue(np.array_equal(field, polished))

    def test_no_notification_does_not_stat_results(self):
        with patch("replay.read_json", side_effect=AssertionError("must not read results")):
            result = result_gate(None, None, False, self.policy)
        self.assertEqual(result["status"], "awaiting_main_notification")

    def test_missing_exit_does_not_read_evaluation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "scratch") as temporary:
            with patch("replay.read_json", side_effect=AssertionError("must not read evaluation")):
                result = result_gate(Path(temporary) / "absent.json", None, True, self.policy)
        self.assertEqual(result["status"], "awaiting_main_notification")

    def test_failure_stops_without_source_capture(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "scratch") as temporary:
            exit_path, evaluation_path = Path(temporary) / "exit.json", Path(temporary) / "evaluation.json"
            write_json(exit_path, {"exit_code": 0})
            write_json(evaluation_path, {"valid": True, "passed": False, "core_score": 0.4, "worst_family_score": 0.4})
            result = result_gate(exit_path, evaluation_path, True, self.policy)
            self.assertEqual(result["status"], "not_needed")
            with self.assertRaises(ValueError):
                capture_source(None, result)

    def test_gate_rejects_contradictory_pass(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "scratch") as temporary:
            exit_path, evaluation_path = Path(temporary) / "exit.json", Path(temporary) / "evaluation.json"
            write_json(exit_path, {"exit_code": 0})
            write_json(evaluation_path, {"valid": True, "passed": True, "core_score": 0.4, "worst_family_score": 0.9})
            with self.assertRaises(ValueError):
                result_gate(exit_path, evaluation_path, True, self.policy)

    def control_record(self, score=0.1, low_load=True):
        return {"valid": True, "low_load_validated": low_load, "case_score": score, "remaining_gap": 2.0, "diagnostic": {"substantive": True, "control_inconclusive": False}}

    def test_two_good_repeats_required(self):
        record = self.control_record()
        self.assertEqual(classify_controls({}, [record], self.policy)[0], "resource_inconclusive")
        self.assertEqual(classify_controls({}, [record, copy.deepcopy(record)], self.policy)[0], "stable_meaningful_gap")

    def test_busy_failures_are_not_hard_evidence(self):
        record = self.control_record(low_load=False)
        self.assertEqual(classify_controls({}, [record, copy.deepcopy(record)], self.policy)[0], "resource_inconclusive")

    def test_success_even_under_load_invalidates_gap(self):
        record = self.control_record(score=0.8, low_load=False)
        self.assertEqual(classify_controls({}, [record], self.policy)[0], "warm_replay_closes_gap")

    def test_incomplete_polish_is_inconclusive(self):
        record = self.control_record()
        record["diagnostic"] = {"substantive": False, "control_inconclusive": True}
        self.assertEqual(classify_controls({}, [record, copy.deepcopy(record)], self.policy)[0], "resource_inconclusive")

    def test_load_accounting_thresholds(self):
        good = {"cpu_to_wall_ratio": 0.98, "sibling_busy_max": 0.1, "pre_busy_fraction": {"1": 0.1, "2": 0.1}}
        self.assertTrue(quiet_accounting(good, self.policy))
        for key, value in (("cpu_to_wall_ratio", 0.8), ("sibling_busy_max", 0.9), ("pre_busy_fraction", {"1": 0.9})):
            bad = dict(good)
            bad[key] = value
            self.assertFalse(quiet_accounting(bad, self.policy))

    def test_npz_bomb_rejected_before_load(self):
        case = read_json(ROOT / self.references["nf01"]["case_path"])
        with tempfile.TemporaryDirectory(dir=ROOT / "scratch") as temporary:
            path = Path(temporary) / "bomb.npz"
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("psi.npy", b"0" * (4194304 + 1))
            with patch("independent.np.load", side_effect=AssertionError("must not load")):
                with self.assertRaises(ValueError):
                    checked_field(path, case)

    def test_dynamic_family_counts_and_invalid_output(self):
        target = dict(self.policy)
        references = [self.references[name] for name in ("nf01", "nf02", "nf04")]
        target.update({"case_count": 3, "families": ["collective_half_flux"], "family_cardinality": {"collective_half_flux": 3}})
        records = []
        for reference in references:
            case = read_json(ROOT / reference["case_path"])
            field = checked_field(ROOT / reference["witness_path"], case)
            records.append(score_field(reference, case, field, 1.0, target))
        self.assertTrue(aggregate(records, target)["passed"])
        records[0].update({"valid": False, "case_score": 0.0, "reason": "invalid test output"})
        self.assertFalse(aggregate(records, target)["passed"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(HarnessTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    write_json(ROOT / "validation.json", {"passed": result.wasSuccessful(), "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "tests": unittest.defaultTestLoader.getTestCaseNames(HarnessTests), "test_solver_processes_launched": 0, "gate_tests_use_synthetic_files_only": True, "corpus_manifest_sha256": digest(ROOT / "corpus/manifest.json")})
    raise SystemExit(0 if result.wasSuccessful() else 1)
