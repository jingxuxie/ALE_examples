import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
module_spec = importlib.util.spec_from_file_location("trusted_evaluator", ROOT / "evaluator/evaluate.py")
checker = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(checker)
RULES = checker.contract()


def baseline():
    return {"schema_version": 1, "stages": checker.reference_stages(RULES)}


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / "adversary", prefix="selftest_")
        self.directory = Path(self.temporary.name)
        self.path = self.directory / "submission.json"

    def tearDown(self):
        self.temporary.cleanup()

    def rejected(self, payload):
        self.path.write_text(json.dumps(payload))
        report = checker.evaluate(self.path)
        self.assertFalse(report["valid"], report)
        self.assertFalse(report["passed"], report)
        self.assertEqual(report["core_score"], 0)
        self.assertTrue(report["reason"])

    def test_valid_baseline_cli(self):
        subprocess.run([sys.executable, "-B", str(ROOT / "participant/baseline/build.py"), "--output", str(self.path)], check=True, capture_output=True)
        self.assertEqual(json.loads(self.path.read_text()), baseline())
        output = self.directory / "report.json"
        process = subprocess.run([sys.executable, "-B", str(ROOT / "evaluator/evaluate.py"), "--submission", str(self.path), "--output", str(output)], check=True, text=True, capture_output=True)
        report = json.loads(output.read_text())
        self.assertEqual(json.loads(process.stdout), report)
        self.assertTrue(report["valid"])
        self.assertFalse(report["passed"])
        self.assertEqual(report["core_score"], 1.0)
        self.assertEqual(report["worst_family_score"], 1.0)
        expected_points = len(RULES["sampling"]["families"]) * RULES["sampling"]["hidden_instances_per_family"] * len(RULES["sampling"]["dtau"]) * len(RULES["sampling"]["repetitions"]) * 2
        self.assertEqual(report["scored_points"], expected_points)
        self.assertEqual(report["resource_score"], 1.0)

    def test_bad_coefficients(self):
        for value in (-0.1, 0, 1e-6, 1.1, True, "0.125", None, [], {}, float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=repr(value)):
                payload = baseline()
                payload["stages"][0]["coefficient"] = value
                self.rejected(payload)

    def test_bad_schema_and_shape(self):
        candidates = [None, [], {}, {"schema_version": True, "stages": baseline()["stages"]}]
        for count in (0, 9, 32, 34, 100):
            candidates.append({"schema_version": 1, "stages": baseline()["stages"][:count] + ([{}] * max(0, count - 33))})
        for payload in candidates:
            with self.subTest(payload=str(payload)[:70]):
                self.rejected(payload)

    def test_unknown_keys_components(self):
        payload = baseline()
        payload["score"] = 999
        self.rejected(payload)
        for value in ("K", "x0", 0, True, [], {}, None):
            payload = baseline()
            payload["stages"][0]["component"] = value
            self.rejected(payload)
        payload = baseline()
        payload["stages"][0]["extra"] = 1
        self.rejected(payload)

    def test_palindrome_and_normalization(self):
        payload = baseline()
        payload["stages"][0]["coefficient"] += 1e-5
        self.rejected(payload)
        payload = baseline()
        payload["stages"][0]["coefficient"] *= 0.5
        payload["stages"][-1]["coefficient"] *= 0.5
        self.rejected(payload)
        payload = baseline()
        payload["stages"][0]["component"] = "V"
        self.rejected(payload)

    def test_adjacent_stages(self):
        payload = baseline()
        payload["stages"][1]["component"] = "X0"
        payload["stages"][-2]["component"] = "X0"
        self.rejected(payload)

    def test_malformed_text(self):
        for raw in (b'{"schema_version":1,"schema_version":1,"stages":[]}', b'{"stages":NaN}', b'{"stages":Infinity}', b'{"stages":1e999}', b'\xff', b'{} {}', b'{}' + b' ' * 32768, b'[' * 2000 + b']' * 2000):
            self.path.write_bytes(raw)
            self.assertFalse(checker.evaluate(self.path)["valid"])

    def test_nonregular_and_missing(self):
        self.assertFalse(checker.evaluate(self.path)["valid"])
        self.assertFalse(checker.evaluate(self.directory)["valid"])
        target = self.directory / "target.json"
        target.write_text(json.dumps(baseline()))
        self.path.symlink_to(target)
        self.assertFalse(checker.evaluate(self.path)["valid"])
        self.path.unlink()
        import os

        os.mkfifo(self.path)
        self.assertFalse(checker.evaluate(self.path)["valid"])

    def test_timeout_and_failed_worker(self):
        self.path.write_text(json.dumps(baseline()))
        with patch.object(checker.subprocess, "run", side_effect=subprocess.TimeoutExpired("worker", 180)):
            self.assertFalse(checker.evaluate(self.path)["valid"])
        with patch.object(checker.subprocess, "run", return_value=subprocess.CompletedProcess("worker", -9, "", "")):
            self.assertFalse(checker.evaluate(self.path)["valid"])

    def test_independent_exponential_oracle(self):
        import numpy as np
        from scipy.linalg import expm

        components = {name: np.diag([index * 0.1, -index * 0.07]).astype(complex) for index, name in enumerate(RULES["components"], start=1)}
        np.testing.assert_allclose(checker.product(baseline()["stages"], components, 0.4), expm(-0.4 * sum(components.values())), atol=2e-14, rtol=2e-14)
        components["X0"] = np.array([[0, 0.4j], [-0.4j, 0]], dtype=complex)
        stages = [{"component": "X0", "coefficient": 0.3}, {"component": "V", "coefficient": 0.7}]
        expected = np.eye(2, dtype=complex)
        for stage in stages:
            values, vectors = np.linalg.eigh(components[stage["component"]])
            expected = expected @ ((vectors * np.exp(-0.4 * stage["coefficient"] * values)) @ vectors.conj().T)
        np.testing.assert_allclose(checker.product(stages, components, 0.4), expected, atol=1e-14)
        self.assertGreater(np.linalg.norm(expected - expm(-0.4 * (0.3 * components["X0"] + 0.7 * components["V"]))), 1e-4)

    def test_frozen_integrity_and_ensembles(self):
        import numpy as np

        manifest = json.loads((ROOT / "evaluator/hidden/manifest.json").read_text())
        for relative, digest in manifest["sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest)
        self.assertLessEqual(len((ROOT / "participant/TASK.md").read_text().split()), 300)
        fixtures = json.loads((ROOT / "evaluator/hidden/instances.json").read_text())["instances"]
        self.assertEqual(len(fixtures), len(RULES["sampling"]["families"]) * RULES["sampling"]["hidden_instances_per_family"])
        for instance in fixtures:
            components = checker.matrices(instance, RULES["components"])
            for name, matrix in components.items():
                np.testing.assert_allclose(matrix, matrix.conj().T)
                if name != "V":
                    self.assertTrue(np.all(np.count_nonzero(matrix, axis=1) == 1))
            commutator_norm = np.linalg.norm(components["X0"] @ components["V"] - components["V"] @ components["X0"])
            if instance["family"].startswith("uniform_"):
                self.assertLess(commutator_norm, 1e-12)
            else:
                self.assertGreater(commutator_norm, 1e-6)

    def test_positive_spectrum_against_direct_products(self):
        import numpy as np

        random = np.random.default_rng(89351)
        components = {}
        for name in RULES["components"]:
            matrix = random.normal(size=(5, 5)) + 1j * random.normal(size=(5, 5))
            components[name] = (matrix + matrix.conj().T) / 8
        stages = baseline()["stages"]
        stages[0]["coefficient"] += 2e-13
        stages[-1]["coefficient"] -= 2e-13
        checker.validate({"schema_version": 1, "stages": stages}, RULES)
        stages = checker.canonical_stages(stages)
        for step in [0.4, 1.0]:
            vectors, logarithms = checker.positive_spectrum(stages, components, step)
            direct = checker.product(stages, components, step)
            for repeats in [1, 4]:
                propagated, green = checker.spectral_observables(vectors, logarithms, repeats)
                powered = np.linalg.matrix_power(direct, repeats)
                np.testing.assert_allclose(propagated, powered, rtol=2e-12, atol=2e-12)
                np.testing.assert_allclose(green, np.linalg.solve(np.eye(5) + powered, np.eye(5)), rtol=2e-12, atol=2e-12)

    def test_positive_decision_branch_only(self):
        relaxed = copy.deepcopy(RULES)
        relaxed["scoring"]["targets"] = {"core_score_min": 0.9, "worst_family_score_min": 0.9, "max_point_ratio_max": 1.0}
        fixtures = json.loads((ROOT / "evaluator/hidden/instances.json").read_text())["instances"]
        selected = [next(instance for instance in fixtures if instance["family"] == family["name"]) for family in RULES["sampling"]["families"]]
        report = checker.score(baseline(), relaxed, selected)
        self.assertTrue(report["passed"])
        self.assertEqual(RULES["scoring"]["targets"]["core_score_min"], 1.8)

    def test_passing_control_if_available(self):
        controls = list((ROOT / "adversary" / f"passing_generation_{RULES.get('generation', 1)}").glob("*.json"))
        if not controls:
            self.skipTest("No known passing witness; no synthetic pass substituted for a real control.")
        for path in controls:
            report = checker.evaluate(path)
            self.assertTrue(report["valid"], report)
            self.assertTrue(report["passed"], report)


def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CheckerTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    summary = {"generation": RULES.get("generation", 1), "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": [{"test": str(test), "reason": reason} for test, reason in result.skipped], "successful": result.wasSuccessful(), "passing_control": "unavailable at current target; relaxed-threshold decision branch independently checked", "targets_changed": False}
    (ROOT / "adversary/self_test_report.json").write_text(json.dumps(summary, indent=2) + "\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
