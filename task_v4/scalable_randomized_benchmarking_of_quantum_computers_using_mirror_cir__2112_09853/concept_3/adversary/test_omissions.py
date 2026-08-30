import itertools
import json
import math
import random
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from core import circuit_weights
from faults import compiled_schedule, fault_weights, omission_profile
import test_evaluator as existing_tests

REFERENCE = existing_tests.REFERENCE


def explicit_deletion(layers, positions):
    omitted = set(positions)
    return [{"local": layer["local"][:],
             "cx": [gate[:] for gate_index, gate in enumerate(layer["cx"])
                    if (round_index, gate_index) not in omitted]}
            for round_index, layer in enumerate(layers)]


class OmissionTests(unittest.TestCase):
    def setUp(self):
        self.layers = [
            {"local": ["H", "S", "HS", "SH"], "cx": [[0, 1], [2, 3]]},
            {"local": ["SH", "HSH", "S", "H"], "cx": [[1, 2]]},
            {"local": ["S", "I", "H", "SH"], "cx": [[0, 1], [2, 3]]},
        ]

    def test_every_small_fault_subset_against_explicit_scalar_propagation(self):
        schedule, instances = compiled_schedule(self.layers)
        positions = [(round_index, gate_index) for round_index, layer in enumerate(self.layers)
                     for gate_index in range(len(layer["cx"]))]
        self.assertEqual(positions, [(instance["round"], instance["cx_index"]) for instance in instances])
        for count in range(4):
            for omitted in itertools.combinations(range(len(positions)), count):
                deleted = explicit_deletion(self.layers, [positions[index] for index in omitted])
                expected = REFERENCE.measurements({"n": 4}, {"layers": deleted})
                observed = [values.tolist() for strata in fault_weights(4, schedule, omitted) for values in strata]
                self.assertEqual(observed, expected)

    def test_dense_unitary_for_every_small_fault_subset(self):
        layers = [{"local": ["H", "S", "SH"], "cx": [[0, 1]]},
                  {"local": ["S", "HSH", "H"], "cx": [[1, 2]]},
                  {"local": ["HS", "I", "S"], "cx": [[0, 2]]}]
        schedule, _ = compiled_schedule(layers)
        dense_checks = existing_tests.PhysicsTests()
        for count in range(4):
            for omitted in itertools.combinations(range(3), count):
                deleted = explicit_deletion(layers, [(index, 0) for index in omitted])
                dense_checks.check_dense(3, deleted)
                for first, second in zip(fault_weights(3, schedule, omitted), circuit_weights(3, deleted)):
                    for observed, expected in zip(first, second):
                        np.testing.assert_array_equal(observed, expected)

    def test_counts_same_round_and_repeated_coupler_instances(self):
        records = []
        profile = omission_profile(4, self.layers, on_scenario=lambda omitted, minima: records.append((omitted, minima)))
        self.assertEqual(profile["scenarios"], 1 + 5 + math.comb(5, 2) + math.comb(5, 3))
        self.assertEqual([profile["by_omission_count"][str(count)]["scenarios"] for count in range(4)], [1, 5, 10, 10])
        subsets = {omitted for omitted, _ in records}
        self.assertIn((0, 1), subsets)
        self.assertIn((0, 3), subsets)
        self.assertNotIn((0, 0), subsets)
        self.assertIn((0, 1, 3), subsets)
        self.assertEqual(len(subsets), 26)
        self.assertEqual(profile["minimum"], min(min(minima) for _, minima in records))
        self.assertEqual(profile["pauli_checks"], 26 * (24 + 9 * 4 * 3))
        self.assertEqual(profile["max_live_scenarios"], 1)
        self.assertNotIn("scenario_records", profile)

    def test_random_actual_champion_scenarios_against_explicit_deletions(self):
        artifact = json.loads((ROOT / "champions/generation_2/artifact.json").read_text())
        sizes = {"ladder16": 16, "grid20": 20, "bridge18": 18}
        rng = random.Random(2026082803)
        for circuit in artifact["circuits"]:
            layers = circuit["layers"]
            positions = [(round_index, gate_index) for round_index, layer in enumerate(layers)
                         for gate_index in range(len(layer["cx"]))]
            schedule, _ = compiled_schedule(layers)
            scenarios = [()] + [(rng.randrange(len(positions)),) for _ in range(8)]
            scenarios += [tuple(sorted(rng.sample(range(len(positions)), 2))) for _ in range(24)]
            scenarios += [tuple(sorted(rng.sample(range(len(positions)), 3))) for _ in range(24)]
            for omitted in scenarios:
                deleted = explicit_deletion(layers, [positions[index] for index in omitted])
                expected = REFERENCE.measurements({"n": sizes[circuit["family"]]}, {"layers": deleted})
                observed = [values.tolist() for strata in fault_weights(sizes[circuit["family"]], schedule, omitted) for values in strata]
                self.assertEqual(observed, expected)

    def test_counterexample_uses_original_positions_and_exact_inverse(self):
        profile = omission_profile(4, self.layers)
        witness = profile["worst_witness"]
        deleted = explicit_deletion(self.layers, [(entry["round"], entry["cx_index"]) for entry in witness["omissions"]])
        packed = 0
        for entry in witness["input"]:
            if entry["pauli"] in ("X", "Y"):
                packed |= 1 << entry["qubit"]
            if entry["pauli"] in ("Z", "Y"):
                packed |= 1 << (4 + entry["qubit"])
        output = REFERENCE.propagate(4, packed, deleted, witness["direction"] == "inverse")
        self.assertEqual(((output | (output >> 4)) & 15).bit_count(), witness["output_weight"])

    def test_zero_entanglers_and_fault_target_boundary(self):
        profile = omission_profile(4, [])
        self.assertEqual(profile["scenarios"], 1)
        self.assertEqual(profile["minimum"], 1)
        self.assertEqual(profile["core_score"], 1 / 3)
        self.assertFalse(profile["passed"])
        self.assertIsNone(profile["by_omission_count"]["1"]["minimum"])
        self.assertEqual(omission_profile(4, [], minimum_weight=1)["core_score"], 1)
        with self.assertRaises(ValueError):
            omission_profile(4, [], maximum=4)

    def test_four_omissions_duplicates_and_nonstreaming_triples_rejected(self):
        schedule, _ = compiled_schedule(self.layers)
        with self.assertRaises(ValueError):
            fault_weights(4, schedule, (0, 1, 2, 3))
        with self.assertRaises(ValueError):
            fault_weights(4, schedule, (0, 0))
        with self.assertRaises(ValueError):
            omission_profile(4, self.layers, maximum=3, collect=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
