from common import ROOT, CONCEPT, checked_field, energy_gradient, read_case, write_json

import tempfile
import unittest
from unittest.mock import patch
import zipfile

import numpy as np

from focused import FOCUS, SELECTED, aggregate, digest, load
from evaluate import score_field


class FocusedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.target = load()
        cls.references = cls.manifest["cases"]

    def scores(self, kind):
        result = []
        for reference in self.references:
            case = read_case(ROOT / reference["case_path"])
            field = checked_field(ROOT / reference[kind + "_path"], case)
            result.append(score_field(reference, case, field, 0.0, self.target))
        return result

    def test_frozen_inputs_and_family(self):
        self.assertEqual({reference["case_id"] for reference in self.references}, set(SELECTED))
        self.assertEqual(self.target["family_cardinality"], {"collective_fluxoid": 3})
        for reference in self.references:
            self.assertGreaterEqual(reference["gap"], 0.5)
            self.assertEqual(digest(ROOT / reference["case_path"]), digest(ROOT / "proposal/cases" / (reference["case_id"] + ".json")))

    def test_baseline_zero_witness_one(self):
        baseline = aggregate(self.scores("baseline"), self.target)
        witness = aggregate(self.scores("witness"), self.target)
        self.assertTrue(baseline["valid"])
        self.assertFalse(baseline["passed"])
        self.assertEqual(baseline["core_score"], 0.0)
        self.assertTrue(witness["passed"])
        self.assertEqual(witness["core_score"], 1.0)

    def test_single_family_aggregation_and_boundary(self):
        records = self.scores("witness")
        for record in records:
            record["case_score"] = 0.65
        report = aggregate(records, self.target)
        self.assertTrue(report["passed"])
        self.assertEqual(report["core_score"], report["worst_family_score"])
        records[0]["case_score"] = 0.649
        self.assertFalse(aggregate(records, self.target)["passed"])

    def test_missing_duplicate_and_unknown_family(self):
        records = self.scores("witness")
        for invalid in (records[:-1], [records[0], records[0], records[2]]):
            with self.assertRaises(ValueError):
                aggregate(invalid, self.target)
        records[0]["family"] = "unknown"
        with self.assertRaises(ValueError):
            aggregate(records, self.target)

    def test_invalid_case_cannot_pass(self):
        records = self.scores("witness")
        records[0].update({"valid": False, "case_score": 0.0, "runtime_score": 0.0, "reason": "test invalid"})
        report = aggregate(records, self.target)
        self.assertGreaterEqual(report["core_score"], self.target["core_min"])
        self.assertFalse(report["passed"])
        self.assertFalse(report["valid"])

    def test_deadline_regression_and_stationarity(self):
        reference = self.references[0]
        case = read_case(ROOT / reference["case_path"])
        field = checked_field(ROOT / reference["baseline_path"], case)
        expired = score_field(reference, case, field, 60.01, self.target)
        regressed = score_field(reference, case, np.zeros_like(field), 0.0, self.target)
        perturbed = score_field(reference, case, field * 1.01, 0.0, self.target)
        self.assertFalse(expired["valid"])
        self.assertIn("regression", regressed["reason"])
        self.assertIn("gradient RMS", perturbed["reason"])

    def test_compressed_bomb_rejected_before_numpy_load(self):
        case = read_case(ROOT / self.references[0]["case_path"])
        with tempfile.TemporaryDirectory(dir=ROOT / "scratch") as temporary:
            from pathlib import Path
            path = Path(temporary) / "bomb.npz"
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("psi.npy", b"0" * (4194304 + 1))
            self.assertLess(path.stat().st_size, 4194304)
            with patch("independent.np.load", side_effect=AssertionError("must reject before load")):
                with self.assertRaisesRegex(ValueError, "oversized"):
                    checked_field(path, case)

    def test_malformed_npz(self):
        reference = self.references[0]
        case = read_case(ROOT / reference["case_path"])
        field = checked_field(ROOT / reference["baseline_path"], case)
        from pathlib import Path
        with tempfile.TemporaryDirectory(dir=ROOT / "scratch") as temporary:
            path = Path(temporary) / "bad.npz"
            np.savez(path, psi=field, energy=np.array(0.0))
            with self.assertRaises(ValueError):
                checked_field(path, case)
            np.savez(path, psi=field.real)
            with self.assertRaises(ValueError):
                checked_field(path, case)
            invalid = field.copy()
            invalid.flat[0] = complex(float("nan"), 0)
            np.savez(path, psi=invalid)
            with self.assertRaises(ValueError):
                checked_field(path, case)
            invalid.flat[0] = 1
            np.savez(path, psi=invalid)
            with self.assertRaises(ValueError):
                checked_field(path, case)

    def test_public_allowlist_and_development_targets(self):
        public = ROOT / "candidate_public"
        release = read_case(ROOT / "candidate_public_manifest.json")
        actual = {str(path.relative_to(public)) for path in public.rglob("*") if path.is_file()}
        self.assertEqual(actual, set(release["files"]))
        for relative, expected in release["files"].items():
            self.assertEqual(digest(public / relative), expected)
        self.assertFalse(list(public.rglob("*.npz")))
        self.assertEqual(digest(public / "baseline/solve.py"), digest(CONCEPT / "champions/generation_1/solve.py"))
        for target in read_case(public / "input/development_targets.json")["cases"]:
            self.assertNotIn(target["case_id"], SELECTED)
            case = read_case(public / "input/cases" / (target["case_id"] + ".json"))
            self.assertNotIn("seed", case)
            field = np.asarray(case["initial_real"]) + 1j * np.asarray(case["initial_imag"])
            energy, unused, rms = energy_gradient(case, field)
            self.assertAlmostEqual(energy, target["baseline_energy"], places=9)
            self.assertLess(rms, 0.002)

    def test_qualified_executable_source_and_outputs(self):
        report = read_case(FOCUS / "qualified_challenger_score.json")
        self.assertTrue(report["valid"] and report["passed"])
        for name, expected in report["source_sha256"].items():
            self.assertEqual(digest(ROOT / "challenger" / name), expected)
        for reference in self.references:
            case = read_case(ROOT / reference["case_path"])
            field = checked_field(ROOT / "runs/proposal_challenger" / reference["case_id"] / "field.npz", case)
            energy, unused, rms = energy_gradient(case, field)
            self.assertLess(energy - reference["witness_energy"], 1e-7)
            self.assertLess(rms, 0.002)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FocusedTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    write_json(ROOT / "focused_validation.json", {"passed": result.wasSuccessful(), "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "tests": unittest.defaultTestLoader.getTestCaseNames(FocusedTests), "proposal_manifest_sha256": digest(FOCUS / "manifest.json")})
    raise SystemExit(0 if result.wasSuccessful() else 1)
