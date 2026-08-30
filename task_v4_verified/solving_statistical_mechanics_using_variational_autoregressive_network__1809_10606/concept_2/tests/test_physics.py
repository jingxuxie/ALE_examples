import copy
import importlib.util
import itertools
import json
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    module_spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


physics = load_module("physics", ROOT / "evaluator" / "physics.py")
baseline = load_module("baseline", ROOT / "participant" / "workspace" / "baseline.py")
SPEC = json.loads((ROOT / "participant" / "input" / "spec.json").read_text())


class ExactPhysicsChecks(unittest.TestCase):
    def test_topology_and_baseline(self):
        edges = physics.torus_edges()
        self.assertEqual(len(edges), 32)
        self.assertEqual(len({tuple(sorted(edge)) for edge in edges}), 32)
        self.assertEqual([sum(site in edge for edge in edges) for site in range(16)], [4] * 16)
        witness = baseline.make_witness()
        self.assertEqual(physics.frustrated_plaquettes(witness["bonds"]), 4)
        report = physics.evaluate_document(witness, SPEC)
        self.assertTrue(report["valid"])
        self.assertFalse(report["passed"])
        self.assertAlmostEqual(report["metrics"]["entropy"], 16 * math.log(2), places=11)
        self.assertAlmostEqual(report["metrics"]["reward_variance"], 32.0, places=10)
        expected_mass = 2 * sum(math.comb(16, distance) for distance in range(3)) / 65536
        self.assertAlmostEqual(report["metrics"]["proposal_sector_mass"], expected_mass, places=13)

    def test_zero_weights_gradient(self):
        report = physics.evaluate_document(baseline.make_witness(), SPEC)
        gradient = np.asarray(report["gradient"])
        expected = np.zeros((16, 16))
        for coupling, (first, second) in zip(baseline.make_witness()["bonds"], physics.torus_edges()):
            expected[max(first, second), min(first, second)] = -coupling / 2.0
        np.testing.assert_allclose(gradient, expected, atol=2e-13, rtol=0)

    def test_exact_ideal_chain(self):
        count = 7
        spins = physics.enumerate_spins(count)
        order = [3, 0, 6, 1, 5, 2, 4]
        couplings = np.array([0.2, -0.7, 1.2, -0.3, 0.5, 0.9])
        weights = np.zeros((count, count))
        energy = np.zeros(len(spins))
        for position, coupling in enumerate(couplings, start=1):
            weights[position, position - 1] = 2 * coupling
            energy -= coupling * spins[:, order[position - 1]] * spins[:, order[position]]
        metrics, gradient = physics.exact_statistics(spins, energy, weights, order, [1] * count, 2)
        expected_partition = math.log(2) + sum(math.log(2 * math.cosh(coupling)) for coupling in couplings)
        self.assertAlmostEqual(metrics["log_partition"], expected_partition, places=13)
        self.assertLess(abs(metrics["reverse_kl"]), 1e-13)
        self.assertLess(metrics["reward_variance"], 1e-26)
        self.assertLess(np.max(np.abs(gradient)), 1e-13)

    def test_scalar_enumeration_and_finite_difference(self):
        count = 5
        generator = np.random.default_rng(98213)
        weights = np.tril(generator.normal(0, 0.35, (count, count)), -1)
        order = [4, 0, 2, 1, 3]
        interactions = np.tril(generator.normal(0, 0.4, (count, count)), -1)
        spins = physics.enumerate_spins(count)
        energy = -np.einsum("bi,ij,bj->b", spins, interactions, spins)
        pattern = [1, -1, 1, -1, 1]
        metrics, gradient = physics.exact_statistics(spins, energy, weights, order, pattern, 1)
        records = []
        for state in itertools.product((-1, 1), repeat=count):
            ordered = [state[site] for site in order]
            local_energy = -sum(interactions[first, second] * state[first] * state[second] for first in range(count) for second in range(first))
            probability = 1.0
            scores = np.zeros_like(weights)
            for position in range(count):
                logit = sum(weights[position, previous] * ordered[previous] for previous in range(position))
                positive = 1.0 / (1.0 + math.exp(-logit))
                probability *= positive if ordered[position] == 1 else 1 - positive
                for previous in range(position):
                    scores[position, previous] = ((ordered[position] + 1) / 2 - positive) * ordered[previous]
            records.append((state, local_energy, probability, scores))
        partition = math.fsum(math.exp(-entry[1]) for entry in records)
        mean_reward = math.fsum(probability * (local_energy + math.log(probability)) for state, local_energy, probability, scores in records)
        expected_variance = math.fsum(probability * (local_energy + math.log(probability) - mean_reward) ** 2 for state, local_energy, probability, scores in records)
        expected_entropy = -math.fsum(probability * math.log(probability) for state, local_energy, probability, scores in records)
        expected_gradient = sum(probability * (local_energy + math.log(probability) - mean_reward) * scores for state, local_energy, probability, scores in records)
        target_energy = math.fsum(math.exp(-local_energy) * local_energy / partition for state, local_energy, probability, scores in records)
        proposal_energy = math.fsum(probability * local_energy for state, local_energy, probability, scores in records)
        sector_records = [entry for entry in records if min(sum(spin != center for spin, center in zip(entry[0], pattern)), sum(spin == center for spin, center in zip(entry[0], pattern))) <= 1]
        target_sector = math.fsum(math.exp(-entry[1]) / partition for entry in sector_records)
        proposal_sector = math.fsum(entry[2] for entry in sector_records)
        self.assertAlmostEqual(metrics["log_partition"], math.log(partition), places=13)
        self.assertAlmostEqual(metrics["entropy"], expected_entropy, places=13)
        self.assertAlmostEqual(metrics["reward_variance"], expected_variance, places=13)
        self.assertAlmostEqual(metrics["reverse_kl"], mean_reward + math.log(partition), places=13)
        self.assertAlmostEqual(metrics["energy_error_per_spin"], abs(proposal_energy - target_energy) / count, places=13)
        self.assertAlmostEqual(metrics["target_sector_mass"], target_sector, places=13)
        self.assertAlmostEqual(metrics["proposal_sector_mass"], proposal_sector, places=13)
        np.testing.assert_allclose(gradient, expected_gradient, atol=1e-13, rtol=0)
        for position in range(1, count):
            for previous in range(position):
                positive_weights = weights.copy()
                negative_weights = weights.copy()
                positive_weights[position, previous] += 1e-5
                negative_weights[position, previous] -= 1e-5
                positive_metrics, unused = physics.exact_statistics(spins, energy, positive_weights, order, pattern, 1)
                negative_metrics, unused = physics.exact_statistics(spins, energy, negative_weights, order, pattern, 1)
                numerical = (positive_metrics["reverse_kl"] - negative_metrics["reverse_kl"]) / 2e-5
                self.assertAlmostEqual(gradient[position, previous], numerical, places=8)

    def test_weight_limit_and_full_support(self):
        witness = baseline.make_witness()
        witness["weights"][1][0] = math.log(9999)
        report = physics.evaluate_document(witness, SPEC)
        self.assertAlmostEqual(report["metrics"]["minimum_binary_conditional"], 1e-4, places=14)
        self.assertLess(report["metrics"]["proposal_symmetry_error"], 1e-14)
        witness["weights"][1][0] = math.nextafter(math.log(9999), math.inf)
        with self.assertRaises(physics.InvalidWitness):
            physics.validate_witness(witness, SPEC)

    def test_malformed_documents(self):
        original = baseline.make_witness()
        mutations = [("beta", True), ("beta", float("nan")), ("beta", float("inf")),
                     ("beta", 10 ** 1000), ("beta", 0.99), ("beta", 3.01),
                     ("radius", True), ("radius", 3.0), ("schema_version", True),
                     ("order", [0] * 16), ("pattern", [True] * 16), ("bonds", [1] * 32),
                     ("weights", [[0] * 15 for position in range(16)])]
        for key, value in mutations:
            with self.subTest(key=key, value=str(value)[:40]):
                witness = copy.deepcopy(original)
                witness[key] = value
                with self.assertRaises(physics.InvalidWitness):
                    physics.validate_witness(witness, SPEC)
        for position, previous, value in [(0, 0, 1e-20), (1, 0, True), (1, 0, float("inf")), (1, 0, 10.0)]:
            witness = copy.deepcopy(original)
            witness["weights"][position][previous] = value
            with self.assertRaises(physics.InvalidWitness):
                physics.validate_witness(witness, SPEC)

    def test_json_parser_boundaries(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tests") as directory:
            path = Path(directory) / "witness.json"
            for content in ('{"beta":1,"beta":2}', '{"beta":NaN}', '{"beta":Infinity}', '[', ' ' * (SPEC["maximum_json_bytes"] + 1)):
                path.write_text(content)
                with self.assertRaises(physics.InvalidWitness):
                    physics.read_witness(directory, SPEC)
            path.unlink()
            path.symlink_to(ROOT / "participant" / "input" / "spec.json")
            with self.assertRaises(physics.InvalidWitness):
                physics.read_witness(directory, SPEC)


if __name__ == "__main__":
    unittest.main()
