import argparse
import json
from pathlib import Path
import unittest

from common import ROOT, SIDE, private_path

import numpy as np
import stim
from models import SPECS, make_model, sample_model
from diagnostics import component_features, residual_report, summarize_pair, wilson
from harness import register_champion, sample_sparse
from regimes import catalog, make_stress_model


class SidecarTests(unittest.TestCase):
    def test_catalog_scope_and_nontrivial_dimensions(self):
        specs = catalog()
        self.assertEqual(len(specs), 33)
        self.assertEqual(len({spec["case_id"] for spec in specs}), 33)
        self.assertEqual(len({spec["stress_group"] for spec in specs}), 10)
        self.assertEqual(max(spec["distance"] for spec in specs), 15)
        self.assertEqual(max(spec["rounds"] for spec in specs), 7)
        self.assertGreaterEqual(min(spec["distance"] for spec in specs), 7)

    def test_uniform_anchor_models_unchanged(self):
        specs = catalog()
        for original in SPECS:
            spec = next(spec for spec in specs if spec["case_id"] == original["case_id"])
            expected = make_model(original)
            observed = make_stress_model(spec)
            self.assertEqual(expected["dem_text"], observed["dem_text"])
            np.testing.assert_array_equal(expected["probabilities"], observed["probabilities"])

    def test_sampler_is_identical_to_public_law(self):
        model = make_stress_model(catalog()[0])
        dense = sample_model(model, 48, 27183)
        sparse = sample_sparse(model, 48, 27183)
        for expected, observed in zip(dense, sparse):
            np.testing.assert_array_equal(expected, observed)

    def test_profiles_have_known_correct_dem_probabilities(self):
        for profile in ["detector_support_strip", "noisy_middle_round"]:
            spec = next(spec for spec in catalog() if spec["profile"] == profile)
            base = make_model(spec)
            observed = make_stress_model(spec)
            self.assertTrue(np.any(observed["probabilities"] > base["probabilities"]))
            self.assertTrue(np.any(observed["probabilities"] == base["probabilities"]))
            dem = stim.DetectorErrorModel(observed["dem_text"])
            probabilities = [instruction.args_copy()[0] for instruction in dem if instruction.type == "error"]
            np.testing.assert_allclose(probabilities, observed["probabilities"], rtol=0, atol=1e-15)
            detectors, labels, faults = dem.compile_sampler(seed=1729).sample(shots=32, return_errors=True)
            np.testing.assert_array_equal((faults.astype(np.uint8) @ observed["detector_matrix"].T) % 2, detectors)
            np.testing.assert_array_equal((faults.astype(np.uint8) @ observed["observable_matrix"].T) % 2, labels)

    def test_component_geometry_and_time_extent(self):
        supports = [np.array([0, 1]), np.array([1, 2]), np.array([3, 4])]
        coordinates = np.array([[0, 0, 0, 0], [1, 0, 0, 0], [1, 0, 2, 0], [5, 5, 1, 0], [5, 6, 1, 0]])
        self.assertEqual(component_features([0, 1, 2], supports, coordinates), (2, 2, 2))
        self.assertEqual(component_features([], supports, coordinates), (0, 0, 0))

    def test_hotspot_and_logical_confusion_are_correct(self):
        syndromes = np.zeros((64, 2), dtype=np.uint8)
        syndromes[:16, 0] = 1
        syndromes[::2, 1] = 1
        labels = np.zeros((64, 4), dtype=np.uint8)
        predictions = labels.copy()
        predictions[:16, 3] = 1
        model = dict(distance=7, detector_coordinates=np.array([[0, 0, 0, 0], [1, 0, 0, 0]]))
        features = dict(largest_fault_component=np.ones(64), syndrome_cancellation_fraction=np.zeros(64))
        report = residual_report(model, syndromes, labels, labels, predictions, features, minimum_exposure=8)
        self.assertEqual(report["logical_confusion_masks"]["8"], 16)
        self.assertEqual(report["detector_hotspots"][0]["detector"], 0)
        self.assertEqual(report["detector_hotspots"][0]["descriptive_lift"], 4)
        json.dumps(report, allow_nan=False)

    def test_small_samples_have_finite_uncertainty(self):
        for baseline, candidate in [([], []), ([False], [False]), ([True], [False]), ([False] * 20, [False] * 20)]:
            json.dumps(summarize_pair(baseline, candidate), allow_nan=False)
        self.assertGreater(wilson(0, 100)[1], 0)

    def test_output_confinement(self):
        self.assertEqual(private_path(SIDE / "reports/check.json"), SIDE / "reports/check.json")
        with self.assertRaises(ValueError):
            private_path(ROOT / "status.json")

    def test_active_attempt_is_rejected_without_reading_it(self):
        arguments = argparse.Namespace(confirm_promoted=True, submission=ROOT / "attempts/v_1/submission.py",
                                       official_report=SIDE / "nonexistent_report.json", name="must_not_register")
        with self.assertRaisesRegex(ValueError, "active attempts/v_1"):
            register_champion(arguments)
        self.assertFalse((SIDE / "snapshots/must_not_register").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
