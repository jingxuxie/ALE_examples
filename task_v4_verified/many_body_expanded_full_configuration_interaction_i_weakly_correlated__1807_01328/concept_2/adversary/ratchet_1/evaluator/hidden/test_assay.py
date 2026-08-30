import copy
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

import assay_worker as worker


ROOT = Path(__file__).resolve().parents[2]
PUBLIC_SPEC = importlib.util.spec_from_file_location("model", ROOT / "participant/workspace/model.py")
PUBLIC_MODEL = importlib.util.module_from_spec(PUBLIC_SPEC)
sys.modules["model"] = PUBLIC_MODEL
PUBLIC_SPEC.loader.exec_module(PUBLIC_MODEL)
ASSAY_SPEC = importlib.util.spec_from_file_location("public_assay", ROOT / "participant/workspace/assay.py")
PUBLIC_ASSAY = importlib.util.module_from_spec(ASSAY_SPEC)
ASSAY_SPEC.loader.exec_module(PUBLIC_ASSAY)
BASELINE = json.loads((ROOT / "participant/input/baseline_witness.json").read_text())
AUTHOR = json.loads((ROOT / "adversary/known_witness.json").read_text())
PREVIOUS = json.loads((ROOT / "adversary/v1_witness.json").read_text())


class AssayTests(unittest.TestCase):
    def test_targets_and_independent_pools(self):
        for filename in ("target.json", "assay_spec.json"):
            self.assertEqual((ROOT / "participant/input" / filename).read_bytes(), (ROOT / "evaluator/hidden" / filename).read_bytes())
        hidden = worker.hidden_uniforms()
        public = PUBLIC_ASSAY.training_uniforms()
        self.assertEqual(hidden.shape, (128, 42))
        self.assertEqual(public.shape, (64, 42))
        self.assertFalse(np.any(np.all(hidden[:, None, :] == public[None, :, :], axis=2)))
        payload = (ROOT / "evaluator/hidden/uniforms.json").read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), worker.SPEC["hidden_uniforms_sha256"])
        private_seed = str(json.loads(payload)["seed"])
        for path in (ROOT / "participant").rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                self.assertNotIn(private_seed, path.read_text())

    def test_noise_mapping_boundaries_and_symmetry(self):
        candidate = copy.deepcopy(BASELINE)
        for field, bound in (("virtual_hopping", 0.45), ("virtual_density", 0.60)):
            candidate[field][0][1] = candidate[field][1][0] = bound
            candidate[field][0][2] = candidate[field][2][0] = -bound
        for uniforms in (np.zeros(42), np.full(42, np.nextafter(1.0, 0.0)), worker.hidden_uniforms()[0]):
            public = PUBLIC_ASSAY.perturb(candidate, uniforms)
            private = worker.perturb(candidate, uniforms)
            self.assertEqual(public, private)
            PUBLIC_MODEL.decode_witness(private)
            for field in worker.FIELDS:
                self.assertLessEqual(float(np.max(np.abs(np.array(private[field]) - np.array(candidate[field])))), 0.001 + 1e-15)
        with self.assertRaises(ValueError):
            PUBLIC_ASSAY.perturb(candidate, [float("nan")] * 42)

    def test_independent_perturbed_energies_and_residuals(self):
        for candidate in (AUTHOR, PREVIOUS):
            for uniforms in worker.hidden_uniforms()[:4]:
                perturbed = worker.perturb(candidate, uniforms)
                public = PUBLIC_MODEL.compute(perturbed)
                private = worker.NOMINAL.calculate(perturbed["virtual_hopping"], perturbed["virtual_density"])
                for field in ("subset_energies_eh", "increments_eh"):
                    for key in public[field]:
                        self.assertAlmostEqual(public[field][key], private[field][key], delta=2e-11)
                for field in ("hf_weight", "spectral_gap_eh", "diagonal_margin_eh"):
                    self.assertAlmostEqual(public[field], private[field], delta=2e-11)
                self.assertLess(private["eigen_residual_eh"], 5e-10)
                self.assertLess(private["closure_error_eh"], 5e-10)

    def test_acceptance_count_and_objective(self):
        nominal = worker.evaluate_case(AUTHOR)
        failed = copy.deepcopy(nominal)
        failed["passed"] = False
        failed["core_score"] = 0.5
        failed["witness_checks"]["all_triples_small"] = False
        for successes in (0, 121, 122, 128):
            report = worker.combine(nominal, [nominal] * successes + [failed] * (128 - successes))
            expected = min(1.0, (successes / 128) / 0.95)
            self.assertEqual(report["passed"], successes >= 122)
            self.assertAlmostEqual(report["core_score"], (1 + expected) / 2)
            self.assertAlmostEqual(report["worst_family_score"], expected)
        physically_failed = copy.deepcopy(failed)
        physically_failed["valid"] = False
        physically_failed["admissibility"]["hf_weight"] = False
        self.assertTrue(worker.combine(nominal, [nominal] * 122 + [physically_failed] * 6)["passed"])
        numerically_failed = copy.deepcopy(nominal)
        numerically_failed["numerical_valid"] = False
        report = worker.combine(nominal, [nominal] * 127 + [numerically_failed])
        self.assertFalse(report["valid"])
        self.assertEqual(report["core_score"], 0.0)

    def test_public_and_private_assay_agree(self):
        directions = worker.hidden_uniforms()[:8]
        public = PUBLIC_ASSAY.evaluate(PREVIOUS, directions)
        private = worker.combine(worker.evaluate_case(PREVIOUS), [worker.evaluate_case(worker.perturb(PREVIOUS, row)) for row in directions])
        for field in ("valid", "passed"):
            self.assertEqual(public[field], private[field])
        self.assertEqual(public["perturbed_assay"]["successes"], private["perturbed_assay"]["successes"])
        self.assertAlmostEqual(public["core_score"], private["core_score"], delta=1e-10)
        self.assertAlmostEqual(public["worst_family_score"], private["worst_family_score"], delta=1e-10)
        self.assertTrue(public["diagnostic_only"])
        self.assertFalse(public["official_hidden_assay"])

    def test_deterministic_full_assay(self):
        first = worker.evaluate(ROOT / "adversary/baseline_witness.json")
        second = worker.evaluate(ROOT / "adversary/baseline_witness.json")
        for report in (first, second):
            report.pop("worker_runtime_seconds")
            report.pop("peak_memory_mib")
        self.assertEqual(first, second)
        self.assertTrue(first["valid"])
        self.assertFalse(first["passed"])
        self.assertEqual(first["perturbed_assay"]["case_count"], 128)

    def test_malformed_worker_inputs(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as directory:
            path = Path(directory) / "witness.json"
            for payload in ('{"schema_version":NaN}', '{"schema_version":1,"schema_version":1}', '[' * 1200 + ']' * 1200, ' ' * 32769):
                path.write_text(payload)
                result = worker.evaluate(path)
                self.assertFalse(result["valid"])
                self.assertFalse(result["passed"])
                self.assertEqual(result["resource_score"], 0.0)
                self.assertFalse(result["evaluation_complete"])

    def test_writable_root_artifact_and_public_cli(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as directory:
            subprocess.run([sys.executable, "-B", str(ROOT / "participant/workspace/baseline.py")], cwd=directory, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, check=True)
            artifact = Path(directory) / "witness.json"
            self.assertEqual(artifact.read_bytes(), (ROOT / "participant/input/baseline_witness.json").read_bytes())
            self.assertFalse((Path(directory) / "output").exists())
            process = subprocess.run([sys.executable, "-B", str(ROOT / "participant/workspace/check.py"), "witness.json", "--seed", "917", "--samples", "2"], cwd=directory, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True, check=True)
            report = json.loads(process.stdout)
            self.assertTrue(report["valid"])
            self.assertFalse(report["passed"])
            self.assertTrue(report["diagnostic_only"])


if __name__ == "__main__":
    unittest.main()
