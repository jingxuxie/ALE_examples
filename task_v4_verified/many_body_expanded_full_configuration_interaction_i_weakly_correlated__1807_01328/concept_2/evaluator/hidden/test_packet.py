import ast
import copy
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tokenize
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant/workspace"))
import assay
import baseline
import model


def module_at(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


PRIVATE = module_at("private_worker_test", ROOT / "evaluator/hidden/assay_worker.py")
WRAPPER = module_at("static_wrapper_test", ROOT / "evaluator/evaluate.py")


class PacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = baseline.sample()
        cls.center = model.full_coefficients(cls.candidate)
        cls.nominal = PRIVATE.evaluate_case(cls.center)
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "adversary")
        cls.directory = Path(cls.temporary.name)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def read_private(self, candidate):
        path = self.directory / "candidate.json"
        path.write_text(json.dumps(candidate))
        return PRIVATE.NOMINAL.read_candidate(path)

    def good_case(self):
        case = copy.deepcopy(self.nominal)
        case.update(valid=True, passed=True, core_score=1.0, numerical_valid=True)
        case["admissibility"] = {name: True for name in case["admissibility"]}
        case["witness_checks"] = {name: True for name in case["witness_checks"]}
        return case

    def test_nominal_target_commitment(self):
        for relative in ("participant/input/target.json", "evaluator/hidden/target.json"):
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), PRIVATE.SPEC["nominal_target_sha256"])

    def test_original_zero_baseline(self):
        self.assertTrue(self.nominal["valid"])
        self.assertFalse(self.nominal["passed"])
        self.assertEqual(self.candidate, json.loads((ROOT / "participant/input/baseline_witness.json").read_text()))

    def test_independent_builders_and_energies(self):
        generator = np.random.default_rng(170013)
        for family in ("vv", "full"):
            for sample_index in range(3):
                candidate = copy.deepcopy(self.candidate)
                for field, bound in (("virtual_hopping", 0.25), ("virtual_density", 0.35)):
                    for source in range(7):
                        for destination in range(source + 1, 7):
                            candidate[field][source][destination] = candidate[field][destination][source] = float(generator.uniform(-bound, bound))
                directions = generator.random(assay.DIMENSIONS[family])
                coefficients = assay.perturb(candidate, directions, family)
                private_coefficients = PRIVATE.perturb(PRIVATE.NOMINAL.full_coefficients(*self.read_private(candidate)), directions, family)
                for public_entries, private_entries in zip(coefficients, private_coefficients):
                    np.testing.assert_allclose(public_entries, private_entries, atol=2e-16, rtol=0)
                energies, hopping, density = coefficients
                public_matrix = model.hamiltonian(127, hopping, density, energies)
                private_matrix, states = PRIVATE.NOMINAL.build_coefficients(*private_coefficients)
                public_basis = list(itertools.combinations(range(10), 3))
                permutation = [public_basis.index(tuple(orbital for orbital in range(10) if state & (1 << orbital))) for state in states]
                np.testing.assert_allclose(public_matrix[np.ix_(permutation, permutation)], private_matrix, atol=2e-15, rtol=0)
                public_metrics = model.compute_coefficients(coefficients)
                private_metrics = PRIVATE.NOMINAL.calculate_coefficients(private_coefficients)
                for field in ("reference_energy_eh", "full_energy_eh", "third_order_energy_eh", "tail_eh", "max_abs_triple_eh", "hf_weight", "spectral_gap_eh", "diagonal_margin_eh"):
                    self.assertLess(abs(public_metrics[field] - private_metrics[field]), 5e-10, (family, sample_index, field))
                self.assertLess(public_metrics["closure_error_eh"], 5e-10)
                self.assertLess(private_metrics["closure_error_eh"], 5e-10)
                self.assertLess(private_metrics["eigen_residual_eh"], 5e-10)

    def test_vv_changes_only_original_controls(self):
        coefficients = assay.perturb(self.candidate, np.zeros(42), "vv")
        np.testing.assert_array_equal(coefficients[0], self.center[0])
        for actual, original in zip(coefficients[1:], self.center[1:]):
            np.testing.assert_array_equal(actual[:3], original[:3])
            np.testing.assert_array_equal(actual[:, :3], original[:, :3])

    def test_full_order_and_new_directions(self):
        directions = np.full(100, 0.5)
        for coordinate in (0, 9, 10, 54, 55, 99):
            changed = directions.copy()
            changed[coordinate] = 0.0
            actual = assay.perturb(self.candidate, changed, "full")
            expected = [entries.copy() for entries in self.center]
            if coordinate < 10:
                expected[0][coordinate] -= 0.001
            else:
                matrix_index = 1 if coordinate < 55 else 2
                edge_index = coordinate - (10 if coordinate < 55 else 55)
                source, destination = assay.EDGES[edge_index]
                expected[matrix_index][source, destination] -= 0.001
                expected[matrix_index][destination, source] -= 0.001
            for actual_entries, expected_entries in zip(actual, expected):
                np.testing.assert_allclose(actual_entries, expected_entries, atol=2e-16, rtol=0)

    def test_box_truncation_not_clipping(self):
        candidate = copy.deepcopy(self.candidate)
        candidate["virtual_hopping"][0][1] = candidate["virtual_hopping"][1][0] = 0.45
        for uniform in (0.0, 0.25, 0.75, np.nextafter(1.0, 0.0)):
            changed = assay.perturb(candidate, np.full(42, uniform), "vv")
            self.assertAlmostEqual(changed[1][3, 4], 0.449 + 0.001 * uniform, places=15)
            self.assertLessEqual(np.max(np.abs(changed[1])), 0.45)
            np.testing.assert_array_equal(changed[1], changed[1].T)
            np.testing.assert_array_equal(np.diag(changed[1]), np.zeros(10))

    def test_independent_new_pools(self):
        pools = PRIVATE.hidden_uniforms()
        self.assertEqual(pools["vv"].shape, (128, 42))
        self.assertEqual(pools["full"].shape, (128, 100))
        provenance = json.loads((ROOT / "adversary/draw_provenance.json").read_text())
        seeds = provenance["private_seeds"]
        self.assertNotEqual(seeds["vv"], seeds["full"])
        self.assertTrue(all(value > 2 ** 64 for value in seeds.values()))
        self.assertFalse(np.array_equal(pools["vv"], pools["full"][:, :42]))
        public = assay.training_uniforms()
        self.assertFalse(np.array_equal(pools["vv"][:64], public["vv"]))
        self.assertFalse(np.array_equal(pools["full"][:64], public["full"]))

    def test_public_default_seed_reproduction(self):
        stored = assay.training_uniforms()
        reproduced = assay.training_uniforms(assay.SPEC["public_training_seed"], 64)
        for family in ("vv", "full"):
            np.testing.assert_array_equal(stored[family], reproduced[family])

    def test_repeat_and_no_mutation(self):
        original = copy.deepcopy(self.candidate)
        uniforms = np.random.default_rng(77321).random(100)
        first = assay.perturb(self.candidate, uniforms, "full")
        second = assay.perturb(self.candidate, uniforms, "full")
        for earlier, later in zip(first, second):
            np.testing.assert_array_equal(earlier, later)
        self.assertEqual(self.candidate, original)
        self.assertEqual(PRIVATE.evaluate_case(first), PRIVATE.evaluate_case(second))

    def test_reference_energy_and_density_gauges(self):
        original = PRIVATE.NOMINAL.calculate_coefficients(self.center)
        energy_shift = [entries.copy() for entries in self.center]
        energy_shift[0] += 0.002
        density_shift = [entries.copy() for entries in self.center]
        density_shift[2] += 0.002 * (np.ones((10, 10)) - np.eye(10))
        for changed in (energy_shift, density_shift):
            metrics = PRIVATE.NOMINAL.calculate_coefficients(changed)
            self.assertLess(abs(metrics["full_energy_eh"] - original["full_energy_eh"] - 0.006), 5e-10)
            for field in ("tail_eh", "max_abs_triple_eh", "hf_weight", "spectral_gap_eh", "diagonal_margin_eh"):
                self.assertLess(abs(metrics[field] - original[field]), 5e-10)

    def test_all_pair_operator_phases(self):
        for state in range(1024):
            if state.bit_count() == 3:
                for source in range(10):
                    for destination in range(10):
                        if state & (1 << source) and not state & (1 << destination):
                            self.assertEqual(PRIVATE.NOMINAL.fermionic_pair_move(state, source, destination), 1)

    def test_malformed_coefficients(self):
        for value in (float("nan"), float("inf"), True, "0.0", 0.451):
            candidate = copy.deepcopy(self.candidate)
            candidate["virtual_hopping"][0][1] = candidate["virtual_hopping"][1][0] = value
            with self.assertRaises((ValueError, TypeError)):
                self.read_private(candidate)
            with self.assertRaises((ValueError, TypeError)):
                model.decode_witness(candidate)

    def test_schema_shape_diagonal_symmetry(self):
        candidates = []
        for field, replacement in (("schema_version", True), ("virtual_density", [])):
            changed = copy.deepcopy(self.candidate)
            changed[field] = replacement
            candidates.append(changed)
        changed = copy.deepcopy(self.candidate)
        changed["extra"] = 0
        candidates.append(changed)
        changed = copy.deepcopy(self.candidate)
        changed["virtual_density"][0][0] = 0.1
        candidates.append(changed)
        changed = copy.deepcopy(self.candidate)
        changed["virtual_hopping"][0][1] = 0.1
        candidates.append(changed)
        for candidate in candidates:
            with self.assertRaises((ValueError, TypeError)):
                self.read_private(candidate)
            with self.assertRaises((ValueError, TypeError)):
                model.decode_witness(candidate)

    def test_duplicate_oversize_and_nonregular_files(self):
        path = self.directory / "malformed.json"
        for payload in ('{"schema_version":1,"schema_version":1}', ' ' * 32769, '{"number":1e999}', '[]'):
            path.write_text(payload)
            with self.assertRaises((ValueError, TypeError)):
                PRIVATE.NOMINAL.read_candidate(path)
        path.write_text(json.dumps(self.candidate))
        link = self.directory / "linked.json"
        link.symlink_to(path)
        fifo = self.directory / "pipe.json"
        os.mkfifo(fifo)
        for nonregular in (link, fifo, self.directory):
            with self.assertRaises((ValueError, OSError)):
                PRIVATE.NOMINAL.read_candidate(nonregular)

    def test_bad_directions_and_full_structure(self):
        for uniforms in (np.zeros(99), np.full(100, np.nan), np.full(100, 1.0), np.full(100, -0.1)):
            with self.assertRaises(ValueError):
                assay.perturb(self.candidate, uniforms, "full")
            with self.assertRaises(ValueError):
                PRIVATE.perturb(self.center, uniforms, "full")
        invalid = [entries.copy() for entries in self.center]
        invalid[0][0] = np.nan
        with self.assertRaises(ValueError):
            PRIVATE.NOMINAL.calculate_coefficients(invalid)
        invalid = [entries.copy() for entries in self.center]
        invalid[1][0, 1] = 0.2
        with self.assertRaises(ValueError):
            model.compute_coefficients(invalid)

    def test_both_families_and_nominal_required(self):
        good = self.good_case()
        failed = copy.deepcopy(good)
        failed.update(passed=False, core_score=0.5)
        failed["witness_checks"]["all_triples_small"] = False
        for deficient in ("vv", "full"):
            cases = {family: [copy.deepcopy(good) for index in range(128)] for family in ("vv", "full")}
            cases[deficient][:7] = [failed] * 7
            self.assertFalse(PRIVATE.combine(good, cases)["passed"])
            cases[deficient][6] = good
            self.assertTrue(PRIVATE.combine(good, cases)["passed"])
        self.assertFalse(PRIVATE.combine(failed, {family: [good] * 128 for family in ("vv", "full")})["passed"])

    def test_physical_failures_count_without_replacement(self):
        good = self.good_case()
        physical_failure = copy.deepcopy(good)
        physical_failure.update(valid=False, passed=False, core_score=0.0)
        physical_failure["admissibility"]["hf_weight"] = False
        cases = {"vv": [good] * 128, "full": [physical_failure] * 6 + [good] * 122}
        report = PRIVATE.combine(good, cases)
        self.assertTrue(report["valid"])
        self.assertTrue(report["passed"])
        self.assertEqual(report["robustness_families"]["full"]["case_count"], 128)
        self.assertEqual(report["robustness_families"]["full"]["physically_valid_cases"], 122)
        cases["full"][6] = physical_failure
        self.assertFalse(PRIVATE.combine(good, cases)["passed"])

    def test_numerical_failure_invalidates_whole_evaluation(self):
        good = self.good_case()
        failed = copy.deepcopy(good)
        failed.update(valid=False, passed=False, numerical_valid=False)
        report = PRIVATE.combine(good, {"vv": [good] * 128, "full": [failed] + [good] * 127})
        self.assertFalse(report["valid"])
        self.assertEqual(report["core_score"], 0)

    def test_scoring_mean_and_worst(self):
        good = self.good_case()
        failed = copy.deepcopy(good)
        failed["passed"] = False
        report = PRIVATE.combine(good, {"vv": [good] * 128, "full": [failed] * 128})
        self.assertAlmostEqual(report["core_score"], 2 / 3)
        self.assertEqual(report["worst_family_score"], 0)
        self.assertFalse(report["passed"])

    def test_timeout_and_closed_stdin(self):
        with patch.object(WRAPPER.subprocess, "run", side_effect=subprocess.TimeoutExpired("worker", 90)) as mocked:
            report = WRAPPER.evaluate(self.directory / "none.json")
        self.assertFalse(report["valid"])
        self.assertEqual(report["resource_score"], 0)
        self.assertEqual(mocked.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertIn("-I", mocked.call_args.args[0])
        self.assertIn("-B", mocked.call_args.args[0])
        self.assertNotIn("PYTHONPATH", mocked.call_args.kwargs["env"])

    def test_worker_limits_and_no_submission_execution(self):
        candidate = self.directory / "witness.json"
        candidate.write_text("invalid")
        (self.directory / "sitecustomize.py").write_text("raise RuntimeError('must not import submitted code')\n")
        report = WRAPPER.evaluate(candidate)
        self.assertFalse(report["valid"])
        self.assertFalse(report["submitted_code_executed"])
        self.assertEqual(report["resource_limits"]["cpu_seconds"], 60)
        self.assertEqual(report["resource_limits"]["address_space_bytes"], 512 * 1024 ** 2)
        self.assertEqual(report["resource_limits"]["core_dump_bytes"], 0)

    def test_public_and_private_aggregation(self):
        good = self.good_case()
        failed = copy.deepcopy(good)
        failed["passed"] = False
        failed["witness_checks"]["all_triples_small"] = False
        for cases in ([good] * 128, [failed] * 128, [good] * 122 + [failed] * 6):
            self.assertEqual(assay.summarize(cases), PRIVATE.summarize(cases))

    def test_source_conventions(self):
        for source in list((ROOT / "participant").rglob("*.py")) + list((ROOT / "evaluator").rglob("*.py")):
            tree = ast.parse(source.read_text())
            self.assertFalse(any(isinstance(node, ast.Name) and len(node.id) == 1 for node in ast.walk(tree)), source)
            with source.open("rb") as stream:
                self.assertFalse(any(token.type == tokenize.COMMENT for token in tokenize.tokenize(stream.readline)), source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
