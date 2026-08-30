import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator" / "hidden"))
from physics import fields, metrics
from reference_operator import ReferenceModel

specification = importlib.util.spec_from_file_location("immutable_public_operator", ROOT / "participant" / "input" / "eliashberg.py")
public_operator = importlib.util.module_from_spec(specification)
specification.loader.exec_module(public_operator)


def small_instance():
    random = np.random.default_rng(317)
    coupling = random.uniform(0.3, 1.7, (3, 4, 4))
    coupling = (coupling + coupling.transpose(0, 2, 1)) / 2
    return {"temperature": np.array(0.027), "n_freq": np.array(23),
            "weights": np.array([0.11, 0.21, 0.37, 0.31]), "omega": np.array([0.2, 1.0, 4.0]),
            "coupling": coupling, "coulomb": np.full((4, 4), 0.13),
            "initial_delta": random.uniform(0.1, 1.0, (4, 23))}


class Numerics(unittest.TestCase):
    def test_fft_vs_independent_folded_sum(self):
        instance = small_instance()
        delta = instance["initial_delta"]
        direct_z, pairing = fields(instance, delta)
        for model in (public_operator.Model(instance), ReferenceModel(instance)):
            renormalization, mapped = model.map(delta)
            np.testing.assert_allclose(renormalization, direct_z, rtol=3e-14, atol=3e-14)
            np.testing.assert_allclose(mapped, pairing / direct_z, rtol=3e-14, atol=3e-14)

    def test_folded_sum_vs_full_signed_frequencies(self):
        instance = small_instance()
        delta = instance["initial_delta"]
        count = int(instance["n_freq"])
        frequencies = np.pi * float(instance["temperature"]) * (2 * np.arange(-count, count) + 1)
        full_delta = np.concatenate((delta[:, ::-1], delta), axis=1)
        radius = np.hypot(frequencies, full_delta)
        normal = np.zeros_like(delta)
        pairing = np.zeros_like(delta)
        difference = frequencies[count:, None] - frequencies[None, :]
        for mode_index, energy in enumerate(instance["omega"]):
            kernel = energy ** 2 / (energy ** 2 + difference ** 2)
            matrix = instance["coupling"][mode_index] * instance["weights"]
            normal += matrix @ ((frequencies / radius) @ kernel.T)
            pairing += matrix @ ((full_delta / radius) @ kernel.T)
        pairing -= ((instance["coulomb"] * instance["weights"]) @ (full_delta / radius).sum(axis=1))[:, None]
        full_z = 1 + np.pi * float(instance["temperature"]) * normal / frequencies[count:]
        direct_z, direct_pairing = fields(instance, delta)
        np.testing.assert_allclose(full_z, direct_z, rtol=1e-14, atol=1e-14)
        np.testing.assert_allclose(np.pi * float(instance["temperature"]) * pairing, direct_pairing, rtol=1e-14, atol=1e-14)

    def test_analytic_jacobian(self):
        instance = small_instance()
        delta = instance["initial_delta"]
        direction = np.random.default_rng(931).normal(size=delta.shape)
        model = public_operator.Model(instance)
        epsilon = 2e-6
        difference = (model.residual(delta + epsilon * direction) - model.residual(delta - epsilon * direction)) / (2 * epsilon)
        np.testing.assert_allclose(model.linearize(delta)(direction), difference, rtol=2e-7, atol=2e-8)

    def test_normal_solution_is_rejected_by_branch(self):
        instance = small_instance()
        normal = np.zeros_like(instance["initial_delta"])
        renormalization = fields(instance, normal)[0]
        measurement = metrics(instance, normal, renormalization, instance["initial_delta"])
        self.assertEqual(measurement["gap_residual"], 0)
        self.assertEqual(measurement["z_residual"], 0)
        self.assertEqual(measurement["branch_error"], 1)
        self.assertFalse(measurement["sign_correct"])

    def test_gauge_invariance(self):
        instance = small_instance()
        delta = instance["initial_delta"]
        renormalization = fields(instance, delta)[0]
        measurement = metrics(instance, -delta, renormalization, delta)
        self.assertEqual(measurement["branch_error"], 0)
        self.assertTrue(measurement["sign_correct"])

    def test_energy_rescaling(self):
        instance = small_instance()
        model = public_operator.Model(instance)
        renormalization, mapped = model.map(instance["initial_delta"])
        scaled = dict(instance)
        for key in ("temperature", "omega", "initial_delta"):
            scaled[key] = instance[key] * 1e-4
        scaled_z, scaled_mapped = public_operator.Model(scaled).map(scaled["initial_delta"])
        np.testing.assert_allclose(renormalization, scaled_z, rtol=1e-13, atol=1e-13)
        np.testing.assert_allclose(mapped, scaled_mapped / 1e-4, rtol=1e-13, atol=1e-13)

    def test_tiny_nonzero_normal_state_trap(self):
        case_path = ROOT / "evaluator" / "hidden" / "cases" / "case_08.npz"
        reference_path = ROOT / "evaluator" / "hidden" / "references" / "case_08.npz"
        with np.load(case_path, allow_pickle=False) as archive:
            instance = {key: archive[key] for key in archive.files}
        with np.load(reference_path, allow_pickle=False) as archive:
            reference = archive["delta"]
        almost_normal = reference * 1e-150
        renormalization = fields(instance, almost_normal)[0]
        measurement = metrics(instance, almost_normal, renormalization, reference)
        self.assertLess(measurement["gap_residual"], 2e-8)
        self.assertEqual(measurement["z_residual"], 0)
        self.assertTrue(measurement["sign_correct"])
        self.assertGreater(measurement["branch_error"], 0.99)

    def test_private_weak_gap_cannot_be_dropped(self):
        with np.load(ROOT / "evaluator" / "hidden" / "cases" / "case_17.npz", allow_pickle=False) as archive:
            instance = {key: archive[key] for key in archive.files}
        with np.load(ROOT / "evaluator" / "hidden" / "references" / "case_17.npz", allow_pickle=False) as archive:
            reference = archive["delta"]
        renormalization = fields(instance, reference)[0]
        gauge = metrics(instance, -reference, renormalization, reference)
        self.assertLess(gauge["gap_residual"], 5e-11)
        self.assertEqual(gauge["branch_error"], 0)
        weakened = reference.copy()
        weakened[np.argmin(reference[:, 0])] = 0
        measurement = metrics(instance, weakened, fields(instance, weakened)[0], reference)
        self.assertGreater(measurement["branch_error"], 0.99)
        self.assertFalse(measurement["sign_correct"])


if __name__ == "__main__":
    unittest.main()
