import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from evaluate import POLICY, accepted, read_output
from physics import fields, metrics

specification = importlib.util.spec_from_file_location("supplied_operator", ROOT / "participant" / "input" / "eliashberg.py")
operator = importlib.util.module_from_spec(specification)
specification.loader.exec_module(operator)


def example(count=31):
    random = np.random.default_rng(318031 + count)
    coupling = random.uniform(0.2, 1.7, (3, 4, 4))
    coupling = (coupling + coupling.transpose(0, 2, 1)) / 2
    coulomb = random.uniform(0, 0.13, (4, 4))
    coulomb = (coulomb + coulomb.T) / 2
    return {"temperature": np.array(0.027), "n_freq": np.array(count),
            "weights": np.array([0.11, 0.21, 0.37, 0.31]),
            "omega": np.array([0.002, 0.31, 4.0]), "coupling": coupling,
            "coulomb": coulomb, "initial_delta": random.uniform(-0.4, 1, (4, count))}


def explicit_signed_fields(instance, delta):
    count = int(instance["n_freq"])
    temperature = float(instance["temperature"])
    positive = np.pi * temperature * (2 * np.arange(count) + 1)
    signed = np.concatenate((-positive[::-1], positive))
    full_delta = np.concatenate((delta[:, ::-1], delta), axis=1)
    radius = np.hypot(signed, full_delta)
    normal = np.zeros_like(delta)
    pairing = np.zeros_like(delta)
    difference = positive[:, None] - signed[None, :]
    for mode_index, energy in enumerate(instance["omega"]):
        kernel = energy ** 2 / (energy ** 2 + difference ** 2)
        matrix = instance["coupling"][mode_index] * instance["weights"]
        normal += matrix @ ((signed / radius) @ kernel.T)
        pairing += matrix @ ((full_delta / radius) @ kernel.T)
    pairing -= ((instance["coulomb"] * instance["weights"]) @ (full_delta / radius).sum(axis=1))[:, None]
    return 1 + np.pi * temperature * normal / positive, np.pi * temperature * pairing


class NumericalValidation(unittest.TestCase):
    def test_all_frequency_convolution_against_full_direct_sums(self):
        for count in (7, 31, 64, 129):
            instance = example(count)
            direct = explicit_signed_fields(instance, instance["initial_delta"])
            actual = fields(instance, instance["initial_delta"])
            for result, expected in zip(actual, direct):
                np.testing.assert_allclose(result, expected, rtol=3e-13, atol=3e-13)

    def test_supplied_operator_on_long_grid(self):
        instance = example(4096)
        instance["temperature"] = np.array(0.0003)
        expected_z, pairing = fields(instance, instance["initial_delta"])
        renormalization, mapped = operator.Model(instance).map(instance["initial_delta"])
        np.testing.assert_allclose(renormalization, expected_z, rtol=3e-12, atol=3e-12)
        np.testing.assert_allclose(mapped, pairing / expected_z, rtol=3e-12, atol=3e-12)

    def test_public_jacobian(self):
        instance = example()
        model = operator.Model(instance)
        delta = instance["initial_delta"]
        direction = np.random.default_rng(8379).normal(size=delta.shape)
        epsilon = 2e-6
        finite = (model.residual(delta + epsilon * direction) - model.residual(delta - epsilon * direction)) / (2 * epsilon)
        np.testing.assert_allclose(model.linearize(delta)(direction), finite, rtol=3e-7, atol=3e-8)

    def test_exact_normal_state_is_not_success(self):
        instance = example()
        delta = np.zeros_like(instance["initial_delta"])
        renormalization = fields(instance, delta)[0]
        measured = metrics(instance, delta, renormalization, np.abs(instance["initial_delta"]))
        self.assertEqual(measured["gap_residual"], 0)
        self.assertEqual(measured["z_residual"], 0)
        self.assertEqual(measured["branch_error"], 1)
        self.assertFalse(accepted(measured))

    def test_one_global_gauge_and_not_relative_signs(self):
        instance = example()
        delta = np.abs(instance["initial_delta"]) + 0.01
        renormalization = fields(instance, delta)[0]
        global_flip = metrics(instance, -delta, renormalization, delta)
        self.assertEqual(global_flip["branch_error"], 0)
        self.assertTrue(global_flip["sign_correct"])
        mixed = delta.copy()
        mixed[0] *= -1
        mixed_flip = metrics(instance, mixed, renormalization, delta)
        self.assertFalse(mixed_flip["sign_correct"])
        self.assertGreater(mixed_flip["branch_error"], 1)

    def test_tiny_induced_gap_has_per_patch_guard(self):
        instance = example()
        reference = np.abs(instance["initial_delta"]) + 0.01
        reference[0] *= 1e-8
        candidate = reference.copy()
        candidate[0] = 0
        renormalization = fields(instance, candidate)[0]
        measured = metrics(instance, candidate, renormalization, reference)
        self.assertEqual(measured["branch_error"], 1)
        self.assertFalse(accepted(measured))

    def test_energy_rescaling(self):
        instance = example()
        normal, pairing = fields(instance, instance["initial_delta"])
        scaled = dict(instance)
        for key in ("temperature", "omega", "initial_delta"):
            scaled[key] = instance[key] * 1e-4
        scaled_normal, scaled_pairing = fields(scaled, scaled["initial_delta"])
        np.testing.assert_allclose(scaled_normal, normal, rtol=2e-12, atol=2e-12)
        np.testing.assert_allclose(scaled_pairing / 1e-4, pairing, rtol=2e-12, atol=2e-12)


class PackageValidation(unittest.TestCase):
    def test_public_code_is_only_original_baseline_and_operator(self):
        expected = {
            "baseline/solve.py": "edb61dd1bf707942bd1056d5ddfebdcda29c63756acb5b2742f73735c70769dd",
            "workspace/solve.py": "edb61dd1bf707942bd1056d5ddfebdcda29c63756acb5b2742f73735c70769dd",
            "input/eliashberg.py": "1b904dc549f4984331b1d227c43c338d7197ca6e6ada16169738793aab190661",
        }
        actual = {str(path.relative_to(ROOT / "participant")): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in (ROOT / "participant").rglob("*.py")}
        self.assertEqual(actual, expected)
        self.assertFalse(any(path.is_symlink() for path in (ROOT / "participant").rglob("*")))

    def test_public_examples_contain_only_public_input_fields(self):
        expected = {"temperature", "n_freq", "weights", "omega", "coupling", "coulomb", "initial_delta"}
        for path in (ROOT / "participant" / "input" / "examples").glob("*.npz"):
            with np.load(path, allow_pickle=False) as archive:
                self.assertEqual(set(archive.files), expected)
                self.assertTrue(all(np.isfinite(archive[key]).all() for key in expected))

    def test_largest_declared_output_is_accepted_by_parser(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "large.npz"
            shape = (40, 32768)
            np.savez(path, delta=np.ones(shape), z=np.ones(shape))
            self.assertGreater(path.stat().st_size, 16 * 1024 ** 2)
            self.assertEqual(read_output(path, shape)["delta"].shape, shape)

    def test_fixed_target_and_public_anchor_are_feasible(self):
        anchor = json.loads((ROOT / "evaluator" / "hidden" / "baseline_anchor.json").read_text())
        self.assertEqual(POLICY["overall_target"], 0.9)
        self.assertEqual(POLICY["worst_family_target"], 0.75)
        self.assertEqual(POLICY["improvement_target"], 0.25)
        self.assertLessEqual(anchor["score"] + POLICY["improvement_target"], 1)
        self.assertEqual(anchor["baseline_identity"], "original_public_damped_fixed_point_solver")

    def test_four_new_references_have_independent_certificates(self):
        hidden = ROOT / "evaluator" / "hidden"
        for case_id in ("case_08", "case_09", "case_16", "case_17"):
            certificate = json.loads((hidden / "references" / (case_id + ".json")).read_text())
            self.assertTrue(certificate["valid"])
            for key in ("primary_all_frequency", "second_start_all_frequency", "primary_direct_rows", "second_start_direct_rows"):
                self.assertLess(certificate[key]["gap_residual"], 5e-11)
                self.assertLess(certificate[key]["z_residual"], 5e-11)
            self.assertLess(certificate["second_start_all_frequency"]["branch_error"], 2e-6)
            for directory, key in (("cases", "instance_sha256"), ("references", "reference_sha256")):
                path = hidden / directory / (case_id + ".npz")
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), certificate[key])


if __name__ == "__main__":
    unittest.main()
