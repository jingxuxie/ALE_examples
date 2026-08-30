import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "participant/input/runtime"), str(ROOT / "participant/input"), str(ROOT / "participant"), str(ROOT / "evaluator")]

import numpy as np
import stim
from baseline.decoder import Decoder
from evaluate import paired_report, read_predictions, snapshot_submission, verify_freeze
from models import SPECS, load_model, sample_model


def rank_binary(matrix):
    work = matrix.copy()
    rank = 0
    for column in range(work.shape[1]):
        candidates = np.flatnonzero(work[rank:, column])
        if not len(candidates):
            continue
        pivot = rank + candidates[0]
        work[[rank, pivot]] = work[[pivot, rank]]
        affected = np.flatnonzero(work[rank + 1:, column]) + rank + 1
        work[affected] ^= work[rank]
        rank += 1
        if rank == work.shape[0]:
            break
    return rank


class ScientificAudit(unittest.TestCase):
    def test_stim_independent_incidence_and_logical_rank(self):
        for spec in SPECS:
            with self.subTest(case=spec["case_id"]):
                model = load_model(ROOT / "participant/input/cases" / spec["case_id"])
                dem = stim.DetectorErrorModel(model["dem_text"])
                detectors, labels, errors = dem.compile_sampler(seed=719).sample(shots=96, return_errors=True)
                np.testing.assert_array_equal((errors.astype(np.uint8) @ model["detector_matrix"].T) % 2, detectors)
                np.testing.assert_array_equal((errors.astype(np.uint8) @ model["observable_matrix"].T) % 2, labels)
                detector_rank = rank_binary(model["detector_matrix"])
                augmented_rank = rank_binary(np.vstack([model["detector_matrix"], model["observable_matrix"]]))
                self.assertEqual(augmented_rank - detector_rank, 4)
                self.assertGreaterEqual(model["num_mechanisms"], 294)

    def test_unconditional_sampler_moments_and_parity(self):
        model = load_model(ROOT / "participant/input/cases/biased_7")
        syndromes, labels, faults = sample_model(model, 16384, 32719)
        np.testing.assert_array_equal(syndromes, (faults @ model["detector_matrix"].T) % 2)
        np.testing.assert_array_equal(labels, (faults @ model["observable_matrix"].T) % 2)
        empirical = faults.mean(axis=0)
        standard_error = np.sqrt(model["probabilities"] * (1 - model["probabilities"]) / len(faults))
        self.assertLess(float(np.max(np.abs(empirical - model["probabilities"]) / standard_error)), 6)
        self.assertGreater(len(np.unique(faults.sum(axis=1))), 10)

    def test_seed_independence_and_split_sizes(self):
        seeds = json.loads((ROOT / "evaluator/hidden/seeds.json").read_text())
        flattened = [seed for splits in seeds.values() for seed in splits.values()]
        self.assertEqual(len(flattened), len(set(flattened)))
        for spec in SPECS:
            for split in ["challenge", "holdout"]:
                with np.load(ROOT / "evaluator/hidden" / split / (spec["case_id"] + ".npz"), allow_pickle=False) as data:
                    self.assertEqual(data["labels"].shape, (1024, 4))

    def test_baseline_reproduction_and_permutation(self):
        for spec in SPECS:
            model = load_model(ROOT / "participant/input/cases" / spec["case_id"])
            with np.load(ROOT / "evaluator/hidden/challenge" / (spec["case_id"] + ".npz"), allow_pickle=False) as data:
                syndromes, baseline = data["syndromes"][:64], data["baseline"][:64]
            decoder = Decoder(model)
            np.testing.assert_array_equal(decoder.decode(syndromes), baseline)
            np.testing.assert_array_equal(decoder.decode(syndromes[::-1].copy())[::-1], baseline)

    def test_paired_statistics(self):
        report = paired_report([1, 1, 0, 0], [0, 1, 0, 1])
        self.assertEqual(report["corrected"], 1)
        self.assertEqual(report["spoiled"], 1)
        self.assertEqual(report["error_reduction"], 0)
        identical = paired_report([1, 0, 0, 1], [1, 0, 0, 1])
        self.assertEqual(identical["paired_absolute_ci95"], [0, 0])

    def test_prediction_schema_rejects_bad_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "predictions.npz"
            for invalid in [np.zeros((8, 4), dtype=float), np.full((8, 4), 2, dtype=np.uint8), np.zeros((8,), dtype=np.uint8)]:
                np.savez_compressed(path, predictions=invalid)
                with self.assertRaises(ValueError):
                    read_predictions(path, 8)
            np.savez_compressed(path, predictions=np.zeros((8, 4), dtype=np.uint8))
            self.assertEqual(read_predictions(path, 8).shape, (8, 4))

    def test_frozen_artifacts(self):
        frozen = verify_freeze()
        self.assertFalse(frozen["fresh_runner_launched"])
        self.assertEqual(frozen["targets"]["pooled_error_reduction"], 0.25)

    def test_attempt_subdirectory_allowed_but_private_roots_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "attempts") as source, tempfile.TemporaryDirectory() as temporary:
            submission = Path(source) / "submission.py"
            submission.write_text("value = 1\n")
            snapshot_submission(submission, Path(temporary) / "snapshot")
            self.assertTrue((Path(temporary) / "snapshot/submission.py").exists())
            for private in ["attempts", "champions", "adversary", "hidden", "evaluator"]:
                with self.assertRaises(ValueError):
                    snapshot_submission(ROOT / private / "submission.py", Path(temporary) / "bad")

    def test_runtime_has_no_symlinks(self):
        self.assertFalse(any(path.is_symlink() for path in (ROOT / "participant/input/runtime").rglob("*")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
