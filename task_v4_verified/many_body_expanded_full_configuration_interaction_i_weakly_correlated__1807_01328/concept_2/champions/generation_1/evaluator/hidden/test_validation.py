import contextlib
import copy
import importlib.util
import json
import math
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

import verify


ROOT = Path(__file__).resolve().parents[2]


def module_at(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


PUBLIC = module_at("public_model", ROOT / "participant/workspace/model.py")
EVALUATOR = module_at("trusted_evaluator", ROOT / "evaluator/evaluate.py")
BASELINE = json.loads((ROOT / "participant/input/baseline_witness.json").read_text())
KNOWN = json.loads((ROOT / "adversary/known_witness.json").read_text())


@contextlib.contextmanager
def target_override(target):
    public_original, private_original = PUBLIC.TARGET, verify.TARGET
    PUBLIC.TARGET = target
    verify.TARGET = target
    try:
        yield
    finally:
        PUBLIC.TARGET, verify.TARGET = public_original, private_original


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.directory = Path(self.temporary.name)
        self.path = self.directory / "witness.json"

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, value):
        self.path.write_text(json.dumps(value))
        return self.path

    def assert_rejected(self, candidate):
        self.write(candidate)
        with self.assertRaises((ValueError, TypeError, OverflowError, OSError)):
            verify.read_candidate(self.path)
        with self.assertRaises((ValueError, TypeError, OverflowError, OSError)):
            PUBLIC.decode_witness(PUBLIC.load_witness(self.path))

    def compare(self, candidate):
        self.write(candidate)
        public = PUBLIC.compute(candidate)
        private = verify.calculate(*verify.read_candidate(self.path))
        for field in ("subset_energies_eh", "increments_eh", "order_sums_eh"):
            self.assertEqual(set(public[field]), set(private[field]))
            for key in public[field]:
                self.assertAlmostEqual(public[field][key], private[field][key], delta=2e-11)
        for field in ("full_energy_eh", "third_order_energy_eh", "hf_weight", "spectral_gap_eh", "diagonal_margin_eh", "max_abs_triple_eh", "tail_eh"):
            self.assertAlmostEqual(public[field], private[field], delta=2e-11)
        self.assertEqual(PUBLIC.score(public)["passed"], verify.assess(private)["passed"])
        return private

    def test_frozen_targets_equal(self):
        self.assertEqual((ROOT / "participant/input/target.json").read_bytes(), (ROOT / "evaluator/hidden/target.json").read_bytes())

    def test_admissible_nonpassing_baseline(self):
        report = verify.assess(self.compare(BASELINE))
        self.assertTrue(report["valid"])
        self.assertFalse(report["passed"])
        self.assertGreater(report["core_score"], 0.0)
        self.assertLess(report["core_score"], 0.001)

    def test_known_witness_passes_independently(self):
        metrics = self.compare(KNOWN)
        report = verify.assess(metrics)
        self.assertTrue(report["valid"])
        self.assertTrue(report["passed"])
        self.assertEqual(report["core_score"], 1.0)
        self.assertEqual(metrics["discarded_quadruples"], 35)

    def test_random_energy_and_increment_agreement(self):
        generator = np.random.default_rng(86420)
        for repetition in range(4):
            candidate = copy.deepcopy(BASELINE)
            for field in ("virtual_hopping", "virtual_density"):
                upper = np.triu(generator.uniform(-0.25, 0.25, (7, 7)), 1)
                candidate[field] = (upper + upper.T).tolist()
            self.compare(candidate)

    def test_analytic_two_level_energy_weight(self):
        target = copy.deepcopy(verify.TARGET)
        target["occupied_virtual_hopping"] = [[0.0] * 7 for row in range(3)]
        target["occupied_virtual_hopping"][2][0] = 0.08
        target["background_density"] = [[0.0] * 10 for row in range(10)]
        separation = target["pair_energy_eh"][3] - target["pair_energy_eh"][2]
        root = math.sqrt(separation ** 2 + 4 * 0.08 ** 2)
        expected_energy = math.fsum(target["pair_energy_eh"][:3]) + (separation - root) / 2
        with target_override(target):
            metrics = self.compare(BASELINE)
        self.assertAlmostEqual(metrics["full_energy_eh"], expected_energy, delta=1e-12)
        self.assertAlmostEqual(metrics["hf_weight"], (1 + separation / root) / 2, delta=1e-12)
        self.assertLess(metrics["max_abs_triple_eh"], 1e-12)

    def test_diagonal_limit(self):
        target = copy.deepcopy(verify.TARGET)
        target["occupied_virtual_hopping"] = [[0.0] * 7 for row in range(3)]
        target["background_density"] = [[0.0] * 10 for row in range(10)]
        with target_override(target):
            metrics = self.compare(BASELINE)
        self.assertAlmostEqual(metrics["full_energy_eh"], -3.15, places=12)
        self.assertAlmostEqual(metrics["hf_weight"], 1.0, places=12)
        self.assertAlmostEqual(metrics["spectral_gap_eh"], 1.25, places=12)
        self.assertLess(metrics["tail_eh"], 1e-12)

    def test_bitmask_fermionic_pair_signs(self):
        for state in range(1 << 10):
            if state.bit_count() != 3:
                continue
            for source in range(10):
                for destination in range(10):
                    if state & (1 << source) and not state & (1 << destination):
                        self.assertEqual(verify.fermionic_pair_move(state, source, destination), 1)

    def test_low_only_agrees(self):
        complete = PUBLIC.compute(KNOWN)
        partial = PUBLIC.compute(KNOWN, complete=False)
        for field in ("full_energy_eh", "third_order_energy_eh", "max_abs_triple_eh", "tail_eh", "hf_weight"):
            self.assertEqual(complete[field], partial[field])

    def test_nonnumeric_nonfinite_and_bounds(self):
        for value in (True, "0.1", None, float("nan"), float("inf"), -float("inf"), 0.450000001, 10 ** 500):
            candidate = copy.deepcopy(BASELINE)
            candidate["virtual_hopping"][0][1] = value
            candidate["virtual_hopping"][1][0] = value
            self.assert_rejected(candidate)
        candidate = copy.deepcopy(BASELINE)
        candidate["virtual_density"][0][1] = candidate["virtual_density"][1][0] = -0.600000001
        self.assert_rejected(candidate)

    def test_shapes_symmetry_diagonal_and_schema(self):
        for field, replacement in (("schema_version", True), ("schema_version", 1.0), ("schema_version", 2), ("virtual_hopping", []), ("virtual_density", [[0.0] * 6 for row in range(7)])):
            candidate = copy.deepcopy(BASELINE)
            candidate[field] = replacement
            self.assert_rejected(candidate)
        for positions in (((0, 0),), ((0, 1),)):
            candidate = copy.deepcopy(BASELINE)
            for row, column in positions:
                candidate["virtual_density"][row][column] = 0.1
            self.assert_rejected(candidate)
        candidate = copy.deepcopy(BASELINE)
        candidate["claimed_energy"] = -10.0
        self.assert_rejected(candidate)
        self.assert_rejected([])

    def test_duplicate_overflow_malformed_and_size(self):
        documents = ['{"schema_version":1,"schema_version":1}', '{"bad":1e999}', '{"bad":NaN}', '[', '"' + 'a' * 32768 + '"', '[' * 1200 + ']' * 1200]
        for document in documents:
            self.path.write_text(document)
            report = verify.run(self.path)
            self.assertFalse(report["valid"])
            self.assertEqual(report["core_score"], 0.0)

    def test_symlink_fifo_and_missing_file(self):
        real_path = self.directory / "real.json"
        real_path.write_text(json.dumps(BASELINE))
        self.path.symlink_to(real_path)
        self.assertFalse(verify.run(self.path)["valid"])
        self.path.unlink()
        os.mkfifo(self.path)
        self.assertFalse(verify.run(self.path)["valid"])
        self.assertFalse(verify.run(self.directory / "missing.json")["valid"])

    def test_each_admissibility_and_witness_gate(self):
        metrics = verify.calculate(KNOWN["virtual_hopping"], KNOWN["virtual_density"])
        for field, value in (("hf_weight", 0.94999), ("spectral_gap_eh", 0.39999), ("diagonal_margin_eh", 0.59999), ("eigen_residual_eh", 1e-8), ("closure_error_eh", 1e-8)):
            changed = dict(metrics, **{field: value})
            self.assertFalse(verify.assess(changed)["valid"])
            self.assertEqual(verify.assess(changed)["core_score"], 0.0)
        for field, value in (("max_abs_triple_eh", 1.00001e-6), ("tail_eh", 49.999e-6), ("tail_to_parent_ratio", 99.999)):
            report = verify.assess(dict(metrics, **{field: value}))
            self.assertTrue(report["valid"])
            self.assertFalse(report["passed"])
        for value in (float("nan"), float("inf")):
            self.assertFalse(verify.assess(dict(metrics, tail_eh=value))["valid"])

    def test_static_evaluator_and_closed_stdin(self):
        self.write(BASELINE)
        (self.directory / "model.py").write_text("raise RuntimeError('must never import participant code')\n")
        report = EVALUATOR.evaluate(self.path)
        self.assertTrue(report["valid"])
        self.assertFalse(report["passed"])
        self.assertFalse(report["submitted_code_executed"])
        self.assertEqual(report["resource_score"], 1.0)
        self.assertIsNone(report["worst_family_score"])


if __name__ == "__main__":
    unittest.main()
