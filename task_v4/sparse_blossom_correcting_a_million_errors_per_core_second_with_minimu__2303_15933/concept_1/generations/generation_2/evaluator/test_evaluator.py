import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

from evaluate import ROOT, PARTICIPANT, np, paired_report, read_predictions, snapshot_submission, verify_freeze

sys.path[:0] = [str(PARTICIPANT / "input"), str(PARTICIPANT)]
import stim
from baseline.submission import Decoder
from models import SPECS, load_model, make_model, sample_model


def rank_binary(matrix):
    matrix = matrix.copy()
    rank = 0
    for column in range(matrix.shape[1]):
        candidates = np.flatnonzero(matrix[rank:, column])
        if not len(candidates):
            continue
        pivot = rank + int(candidates[0])
        matrix[[rank, pivot]] = matrix[[pivot, rank]]
        active = np.flatnonzero(matrix[rank + 1:, column]) + rank + 1
        matrix[active] ^= matrix[rank]
        rank += 1
        if rank == matrix.shape[0]:
            break
    return rank


class ScientificTests(unittest.TestCase):
    def test_stim_incidence_and_logical_rank(self):
        for spec in SPECS:
            with self.subTest(case=spec["case_id"]):
                model = load_model(PARTICIPANT / "input/cases" / spec["case_id"])
                dem = stim.DetectorErrorModel(model["dem_text"])
                detectors, labels, errors = dem.compile_sampler(seed=719).sample(shots=48, return_errors=True)
                np.testing.assert_array_equal((errors.astype(np.uint8) @ model["detector_matrix"].T) % 2, detectors)
                np.testing.assert_array_equal((errors.astype(np.uint8) @ model["observable_matrix"].T) % 2, labels)
                self.assertEqual(rank_binary(np.vstack([model["detector_matrix"], model["observable_matrix"]])) - rank_binary(model["detector_matrix"]), 4)
                self.assertGreaterEqual(model["num_mechanisms"], 810)

    def test_profiles_and_public_parameters_reproduce_models(self):
        self.assertEqual(len({spec["family"] for spec in SPECS}), 3)
        for spec in SPECS:
            generated = make_model(spec)
            stored = load_model(PARTICIPANT / "input/cases" / spec["case_id"])
            for name in ["detector_matrix", "observable_matrix", "probabilities"]:
                np.testing.assert_array_equal(generated[name], stored[name])
            self.assertEqual(generated["dem_text"], stored["dem_text"])

    def test_unconditional_sampler_moments(self):
        model = make_model(SPECS[0])
        syndromes, labels, faults = sample_model(model, 8192, 71421)
        empirical = faults.mean(axis=0)
        error = np.sqrt(model["probabilities"] * (1 - model["probabilities"]) / len(faults))
        self.assertLess(float(np.max(np.abs(empirical - model["probabilities"]) / error)), 6)
        self.assertGreater(len(np.unique(faults.sum(axis=1))), 10)
        np.testing.assert_array_equal(labels[:32], (faults[:32] @ model["observable_matrix"].T) % 2)
        np.testing.assert_array_equal(syndromes[:32], (faults[:32] @ model["detector_matrix"].T) % 2)

    def test_seed_independence_and_exact_draw_reproduction(self):
        seeds = json.loads((ROOT / "evaluator/hidden/seeds.json").read_text())
        values = [seed for splits in seeds.values() for seed in splits.values()]
        self.assertEqual(len(values), 18)
        self.assertEqual(len(set(values)), len(values))
        for spec in SPECS:
            model = load_model(PARTICIPANT / "input/cases" / spec["case_id"])
            for split, seed in seeds[spec["case_id"]].items():
                directory = PARTICIPANT / "input/calibration" if split == "calibration" else ROOT / "evaluator/hidden" / split
                with np.load(directory / (spec["case_id"] + ".npz"), allow_pickle=False) as data:
                    syndromes, labels, faults = sample_model(model, 16, seed)
                    self.assertEqual(data["labels"].shape, (256, 4))
                    np.testing.assert_array_equal(syndromes, data["syndromes"][:16])
                    np.testing.assert_array_equal(labels, data["labels"][:16])

    def test_promoted_baseline_exact_files(self):
        provenance = json.loads((ROOT / "evaluator/hidden/baseline_provenance.json").read_text())
        for name, digest in provenance["files"].items():
            self.assertEqual(hashlib.sha256((PARTICIPANT / "baseline" / name).read_bytes()).hexdigest(), digest)

    def test_baseline_reproduction_permutation_repeated_calls(self):
        for spec in SPECS:
            model = load_model(PARTICIPANT / "input/cases" / spec["case_id"])
            with np.load(ROOT / "evaluator/hidden/challenge" / (spec["case_id"] + ".npz"), allow_pickle=False) as data:
                syndromes, baseline = data["syndromes"][:16], data["baseline"][:16]
            decoder = Decoder(model)
            np.testing.assert_array_equal(decoder.decode(syndromes), baseline)
            np.testing.assert_array_equal(decoder.decode(syndromes[::-1].copy())[::-1], baseline)
            np.testing.assert_array_equal(decoder.decode(syndromes[:3]), baseline[:3])

    def test_paired_statistics(self):
        report = paired_report([1, 1, 0, 0], [0, 1, 0, 1])
        self.assertEqual((report["corrected"], report["spoiled"], report["error_reduction"]), (1, 1, 0))
        identical = paired_report([1, 0, 0, 1], [1, 0, 0, 1])
        self.assertEqual(identical["paired_absolute_ci95"], [0, 0])

    def test_prediction_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "predictions.npz"
            for invalid in [np.zeros((8, 4), dtype=float), np.full((8, 4), 2, dtype=np.uint8), np.zeros(8, dtype=np.uint8)]:
                np.savez_compressed(path, predictions=invalid)
                with self.assertRaises(ValueError):
                    read_predictions(path, 8)
            np.savez_compressed(path, predictions=np.zeros((8, 4), dtype=np.uint8))
            self.assertEqual(read_predictions(path, 8).shape, (8, 4))
            np.savez_compressed(path, predictions=np.zeros((8, 4), dtype=np.uint8), labels=np.ones((8, 4), dtype=np.uint8))
            with self.assertRaises(ValueError):
                read_predictions(path, 8)

    def test_snapshot_candidate_subdirectory_and_privileged_ancestry(self):
        for collection in ["attempts", "champions", "adversary"]:
            with tempfile.TemporaryDirectory(dir=ROOT / collection) as source, tempfile.TemporaryDirectory() as directory:
                submission = Path(source) / "submission.py"
                submission.write_text("value = 1\n")
                snapshot_submission(submission, Path(directory) / "snapshot")
                self.assertTrue((Path(directory) / "snapshot/submission.py").is_file())
                (Path(source) / "escape").symlink_to(ROOT / "evaluator/hidden/seeds.json")
                with self.assertRaises(ValueError):
                    snapshot_submission(submission, Path(directory) / "bad")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                snapshot_submission(ROOT / "evaluator/evaluate.py", Path(directory) / "private")
            with self.assertRaises(ValueError):
                snapshot_submission(ROOT / "evaluator/hidden/build_data.py", Path(directory) / "private")

    def test_frozen_targets_and_resources(self):
        frozen = verify_freeze()
        self.assertFalse(frozen["fresh_runner_launched"])
        self.assertEqual(frozen["targets"]["pooled_error_reduction"], 0.20)
        self.assertEqual(frozen["targets"]["holdout_error_reduction"], 0.15)
        self.assertEqual(frozen["targets"]["max_family_failure_ratio"], 1)
        self.assertEqual(frozen["limits"]["cpu_seconds"], math.ceil(1.25 * frozen["limits"]["baseline_cpu_seconds"]))

    def test_runtime_self_contained(self):
        self.assertFalse(any(path.is_symlink() for path in (PARTICIPANT / "input/runtime").rglob("*")))
        self.assertTrue(str(np.__file__).startswith(str(PARTICIPANT / "input/runtime")))
        self.assertTrue(str(stim.__file__).startswith(str(PARTICIPANT / "input/runtime")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
