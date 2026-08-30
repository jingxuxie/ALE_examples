"""Privileged tests; no labels or seeds are copied into participant assets."""

import hashlib
import json
import runpy
import sys
import tempfile
import unittest
from unittest import mock
from itertools import combinations
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(ROOT / "participant/input/workspace"))
from evaluate import evaluate, read_prediction
from generator import Hamiltonian, PAIR_INDEX, TRIPLE_INDEX, ground, matrix


def load_data(name):
    with np.load(ROOT / f"participant/input/workspace/data/{name}.npz", allow_pickle=False) as archive:
        return dict(archive)


def restore(record):
    fields = {key: record[key] for key in ("n_pairs", "n_virtual", "family")}
    fields.update({key: np.asarray(record[key]) for key in
                   ("onsite", "density", "hopping", "occupied_profile", "positions", "groups")})
    return Hamiltonian(**fields)


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train = load_data("train")
        cls.validation = load_data("validation")
        cls.test = load_data("test_features")
        cls.models = json.loads((ROOT / "evaluator/hidden/audit_models.json").read_text())
        cls.limits = threadpool_limits(limits=1)

    @classmethod
    def tearDownClass(cls):
        cls.limits.restore_original_limits()

    def test_split_counts_disjoint_ids_and_heldout_families(self):
        sets = []
        fingerprints = set()
        for data, count, families in ((self.train, 1280, range(4)),
                                      (self.validation, 384, range(4)),
                                      (self.test, 288, range(6))):
            self.assertEqual(len(data["ids"]), count)
            self.assertEqual(len(set(data["ids"])), count)
            self.assertEqual(set(data["family"].tolist()), set(families))
            sets.append(set(data["ids"].tolist()))
            for family in families:
                for n_pairs in (2, 3):
                    for n_virtual in (6, 7, 8, 9):
                        mask = ((data["family"] == family) & (data["n_pairs"] == n_pairs) &
                                (data["n_virtual"] == n_virtual))
                        self.assertEqual(int(mask.sum()), count // (len(families) * 8))
            for row in range(count):
                signature = hashlib.sha256(data["onsite"][row].tobytes() + data["inc1"][row].tobytes()).digest()
                self.assertNotIn(signature, fingerprints)
                fingerprints.add(signature)
        for first, second in combinations(sets, 2):
            self.assertFalse(first & second)

    def test_low_order_tensor_consistency_and_padding(self):
        for data in (self.train, self.validation, self.test):
            np.testing.assert_allclose(data["cas1"], data["inc1"], atol=0, rtol=0)
            pair_lookup = {tuple(pair): index for index, pair in enumerate(PAIR_INDEX)}
            for index, (first, second) in enumerate(PAIR_INDEX):
                mask = data["n_virtual"] > second
                np.testing.assert_allclose(data["cas2"][mask, index], data["inc2"][mask, index] +
                                           data["inc1"][mask, first] + data["inc1"][mask, second], atol=1e-13)
                self.assertTrue(np.all(data["cas2"][~mask, index] == 0))
            for index, triple in enumerate(TRIPLE_INDEX):
                mask = data["n_virtual"] > triple[-1]
                reconstructed = data["inc3"][mask, index] + data["inc1"][mask][:, triple].sum(axis=1)
                reconstructed += sum(data["inc2"][mask, pair_lookup[pair]] for pair in combinations(triple, 2))
                np.testing.assert_allclose(data["cas3"][mask, index], reconstructed, atol=1e-13)
            np.testing.assert_allclose(data["truncated_correlation"],
                                       sum(data[key].sum(axis=1) for key in ("inc1", "inc2", "inc3")), atol=1e-13)

    def test_all_release_residuals_and_curated_conditions(self):
        for split in ("train", "validation", "test"):
            with np.load(ROOT / f"evaluator/hidden/{split}_truth.npz", allow_pickle=False) as truth:
                self.assertLess(float(truth["residual"].max()), 5e-12)
                self.assertGreaterEqual(float(truth["reference_weight"].min()), .85)
                self.assertGreaterEqual(float(np.abs(truth["tail"]).min()), 1.5e-4)
                self.assertTrue(np.any(truth["tail"] > 0) and np.any(truth["tail"] < 0))
            data = self.test if split == "test" else getattr(self, split)
            for row in range(len(data["ids"])):
                self.assertGreaterEqual(float(data["diagonal_gaps"][row, :data["n_pairs"][row],
                                                              :data["n_virtual"][row]].min()), .80)

    def test_independent_matrix_and_solver(self):
        for record in self.models[::7]:
            model = restore(record)
            states = list(combinations(range(len(model.onsite)), model.n_pairs))
            independent = np.zeros((len(states), len(states)))
            for row, state in enumerate(states):
                independent[row, row] = sum(model.onsite[list(state)]) + sum(
                    model.density[first, second] for first, second in combinations(state, 2))
                for column in range(row):
                    leaving = set(state) - set(states[column])
                    entering = set(states[column]) - set(state)
                    if len(leaving) == len(entering) == 1:
                        independent[row, column] = model.hopping[next(iter(leaving)), next(iter(entering))]
                        independent[column, row] = independent[row, column]
            np.testing.assert_allclose(matrix(model), independent, atol=1e-14)
            energy, weight, residual = ground(model, vectors=True)
            self.assertLess(abs(energy - np.linalg.eigvalsh(independent)[0]), 3e-12)
            self.assertLess(residual, 5e-12)
            self.assertGreaterEqual(weight, .85)

    def test_full_inclusion_exclusion_and_alternating_orders(self):
        alternating = 0
        for record in self.models:
            model = restore(record)
            order_sums = np.asarray(record["order_sums"])
            correlation = ground(model) - ground(model, ())
            self.assertLess(abs(order_sums.sum() - correlation), 2e-11)
            data = self.test if record["split"] == "test" else getattr(self, record["split"])
            row = int(np.flatnonzero(data["ids"] == record["id"])[0])
            self.assertLess(abs(order_sums[1:4].sum() - data["truncated_correlation"][row]), 2e-11)
            self.assertGreaterEqual(abs(order_sums[4:].sum()), 1.5e-4 - 2e-11)
            present = order_sums[2:][np.abs(order_sums[2:]) > 1e-7]
            alternating += int(np.any(present[1:] * present[:-1] < 0))
        self.assertGreaterEqual(alternating, len(self.models) // 4)

    def test_latent_information_is_locally_identifiable(self):
        for record in self.models[::5]:
            model = restore(record)
            step = 1e-5
            virtual = 0
            orbital = model.n_pairs + virtual
            original = model.hopping[:model.n_pairs, orbital].copy()
            observations = []
            for offset in (-step, step):
                model.hopping[:model.n_pairs, orbital] = original - offset * model.occupied_profile
                model.hopping[orbital, :model.n_pairs] = model.hopping[:model.n_pairs, orbital]
                observations.append(ground(model, (virtual,)))
            model.hopping[:model.n_pairs, orbital] = original
            model.hopping[orbital, :model.n_pairs] = original
            self.assertLess((observations[1] - observations[0]) / (2 * step), -1e-4)
            for first, second in ((0, 1), (0, model.n_virtual - 1)):
                left, right = model.n_pairs + first, model.n_pairs + second
                original = model.hopping[left, right]
                for magnitude in (.012, .146, .28):
                    observations = []
                    for offset in (-step, step):
                        model.hopping[left, right] = np.sign(original) * (magnitude + offset)
                        model.hopping[right, left] = model.hopping[left, right]
                        observations.append(ground(model, (first, second)))
                    derivative = (observations[1] - observations[0]) / (2 * step)
                    self.assertGreater(derivative * np.sign(original), 1e-7)
                model.hopping[left, right] = model.hopping[right, left] = original

    def test_no_hidden_labels_seeds_or_models_in_participant(self):
        self.assertNotIn("tail", self.test)
        self.assertEqual(set(self.train) - {"tail"}, set(self.test))
        self.assertEqual(set(self.validation) - {"tail"}, set(self.test))
        forbidden = ("test_truth", "audit_models", "seeds.json", "target_freeze", "predictions.npz")
        private_seeds = json.loads((ROOT / "evaluator/hidden/seeds.json").read_text())
        for path in (ROOT / "participant").rglob("*"):
            self.assertFalse(path.is_symlink())
            self.assertFalse(any(fragment in path.name for fragment in forbidden))
            if path.is_file():
                payload = path.read_bytes()
                for seed in private_seeds.values():
                    self.assertNotIn(str(seed).encode(), payload)
                if path.suffix == ".npz":
                    with np.load(path, allow_pickle=False) as archive:
                        self.assertFalse({"hopping", "reference_weight", "residual", "correlation"} & set(archive.files))

    def test_static_submission_validation(self):
        ids = self.test["ids"]
        with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as directory:
            path = Path(directory) / "prediction.npz"
            values = np.linspace(-.01, .01, len(ids))
            np.savez_compressed(path, ids=ids[::-1], tail=values[::-1])
            np.testing.assert_array_equal(read_prediction(path, ids, 8388608), values)
            bad_cases = [dict(ids=ids[:-1], tail=values[:-1]),
                         dict(ids=np.repeat(ids[0], len(ids)), tail=values),
                         dict(ids=ids, tail=np.full(len(ids), np.nan)),
                         dict(ids=ids, tail=np.full(len(ids), np.inf)),
                         dict(ids=ids, tail=values[:, None]),
                         dict(ids=ids, tail=values.astype(int)),
                         dict(ids=ids.astype(object), tail=values),
                         dict(ids=ids, tail=values, extra=np.zeros(1))]
            for bad in bad_cases:
                np.savez_compressed(path, **bad)
                with self.assertRaises(ValueError):
                    read_prediction(path, ids, 8388608)
            unknown = ids.copy()
            unknown[0] = "f" * 32
            np.savez_compressed(path, ids=unknown, tail=values)
            with self.assertRaises(ValueError):
                read_prediction(path, ids, 8388608)
            result = evaluate(path)
            self.assertFalse(result["valid"])
            self.assertFalse(result["passed"])

    def test_frozen_baseline_is_valid_and_not_passing(self):
        result = evaluate(ROOT / "attempts/baseline/predictions.npz")
        self.assertTrue(result["valid"], result)
        self.assertFalse(result["passed"], result)
        self.assertEqual(result["limits"]["core_score"], 3e-5)
        self.assertEqual(result["limits"]["worst_family_score"], 6e-5)
        freeze = json.loads((ROOT / "evaluator/hidden/target_freeze.json").read_text())
        report = json.loads((ROOT / "evaluator/hidden/generation_report.json").read_text())
        self.assertLess(freeze["targets_frozen_utc"], report["completed_utc"])
        self.assertLess(report["completed_utc"], freeze["sealed_utc"])

    def test_top_level_wrapper_uses_writable_outputs(self):
        wrapper = ROOT / "participant/baseline/run.py"
        canonical = ROOT / "participant/input/workspace/baseline/predict.py"
        output = ROOT / "adversary/wrapper_check/predictions.npz"
        for explicit_report in (False, True):
            arguments = [str(wrapper), "--output", str(output)]
            report = output.with_name("baseline_report.json")
            if explicit_report:
                report = output.with_name("explicit_report.json")
                arguments.extend(["--report", str(report)])
            with mock.patch.object(sys, "argv", arguments), mock.patch("os.execv") as execute:
                runpy.run_path(str(wrapper), run_name="__main__")
            execute.assert_called_once_with(sys.executable, [sys.executable, "-B", str(canonical),
                                            "--output", str(output), "--report", str(report)])
        self.assertTrue((ROOT / "participant/workspace/README.md").is_file())

    def test_interface_amendment_preserves_scientific_freeze(self):
        report = json.loads((ROOT / "adversary/prelaunch_interface_amendments.json").read_text())
        for relative, expected in report["preserved_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected, relative)
        current = json.loads((ROOT / "evaluator/hidden/target_freeze.json").read_text())
        original = dict(report["target_freeze_before"])
        current.pop("sha256")
        original.pop("sha256")
        self.assertEqual(current, original)


if __name__ == "__main__":
    unittest.main()
