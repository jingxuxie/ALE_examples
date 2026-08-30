import copy
import importlib.util
import itertools
import json
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator/hidden"))
from core import (InvalidSubmission, LOCAL_WORDS, circuit_weights, generator_images,
                  load_json, output_rows, score_metrics, summarize, validate_submission)
from design import random_layers

MODULE = importlib.util.spec_from_file_location("reference", ROOT / "participant/baseline/solve.py")
REFERENCE = importlib.util.module_from_spec(MODULE)
MODULE.loader.exec_module(REFERENCE)
EVALUATOR_MODULE = importlib.util.spec_from_file_location("evaluate", ROOT / "evaluator/evaluate.py")
EVALUATOR = importlib.util.module_from_spec(EVALUATOR_MODULE)
EVALUATOR_MODULE.loader.exec_module(EVALUATOR)


def tensor_pauli(n, packed):
    identity = np.eye(2, dtype=complex)
    pauli_x = np.array([[0, 1], [1, 0]], dtype=complex)
    pauli_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    pauli_z = np.diag([1, -1]).astype(complex)
    result = np.ones((1, 1), dtype=complex)
    for qubit in reversed(range(n)):
        xbit, zbit = (packed >> qubit) & 1, (packed >> (n + qubit)) & 1
        result = np.kron(result, {(0, 0): identity, (1, 0): pauli_x,
                                  (1, 1): pauli_y, (0, 1): pauli_z}[xbit, zbit])
    return result


def dense_unitary(n, layers):
    hadamard = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
    phase = np.diag([1, 1j])
    unitary = np.eye(1 << n, dtype=complex)
    for layer in layers:
        for qubit, word in enumerate(layer["local"]):
            for gate in word:
                if gate == "I":
                    continue
                local = hadamard if gate == "H" else phase
                full = np.ones((1, 1), dtype=complex)
                for position in reversed(range(n)):
                    full = np.kron(full, local if position == qubit else np.eye(2))
                unitary = full @ unitary
        for control, target in layer["cx"]:
            cnot = np.zeros_like(unitary)
            for basis in range(1 << n):
                destination = basis ^ (1 << target) if (basis >> control) & 1 else basis
                cnot[destination, basis] = 1
            unitary = cnot @ unitary
    return unitary


class PhysicsTests(unittest.TestCase):
    def test_all_local_words_dense(self):
        for word in LOCAL_WORDS:
            self.check_dense(1, [{"local": [word], "cx": []}])

    def check_dense(self, n, layers):
        unitary = dense_unitary(n, layers)
        for packed in range(1 << (2 * n)):
            for inverse, operation in ((False, unitary), (True, unitary.conj().T)):
                predicted = REFERENCE.propagate(n, packed, layers, inverse)
                actual = operation @ tensor_pauli(n, packed) @ operation.conj().T
                expected = tensor_pauli(n, predicted)
                sign = np.trace(expected.conj().T @ actual) / (1 << n)
                self.assertAlmostEqual(abs(sign), 1.0, places=10)
                np.testing.assert_allclose(actual, sign * expected, atol=1e-10)
        forward, inverse = generator_images(n, output_rows(n, layers))
        for index in range(2 * n):
            self.assertEqual(int(forward[index]), REFERENCE.propagate(n, 1 << index, layers))
            self.assertEqual(int(inverse[index]), REFERENCE.propagate(n, 1 << index, layers, True))

    def test_dense_random_circuits_and_inverse(self):
        rng = random.Random(412)
        for n in (2, 3, 4):
            family = {"n": n, "edges": list(itertools.combinations(range(n), 2)),
                      "max_rounds": 4, "max_cx": 4 * (n // 2)}
            self.check_dense(n, random_layers(family, rng))

    def test_exact_low_weight_enumeration_and_round_trip(self):
        rng = random.Random(811)
        for n in (3, 16, 18, 20):
            family = {"n": n, "edges": [[qubit, qubit + 1] for qubit in range(n - 1)],
                      "max_rounds": 6, "max_cx": 3 * n}
            layers = random_layers(family, rng)
            expected = REFERENCE.measurements(family, {"layers": layers})
            observed = [samples.tolist() for strata in circuit_weights(n, layers) for samples in strata]
            self.assertEqual(expected, observed)
            self.assertEqual(len(observed[0]), 3 * n)
            self.assertEqual(len(observed[1]), 9 * n * (n - 1) // 2)
            for _ in range(100):
                packed = rng.randrange(1 << (2 * n))
                transformed = REFERENCE.propagate(n, packed, layers)
                self.assertEqual(REFERENCE.propagate(n, transformed, layers, True), packed)

    def test_dropped_cnot_matches_physical_deletion(self):
        layers = [{"local": ["H", "SH", "S"], "cx": [[0, 1]]},
                  {"local": ["S", "H", "HS"], "cx": [[1, 2]]}]
        for round_index in range(2):
            deleted = copy.deepcopy(layers)
            deleted[round_index]["cx"].pop()
            for expected, observed in zip(circuit_weights(3, deleted), circuit_weights(3, layers, (round_index, 0))):
                for first, second in zip(expected, observed):
                    np.testing.assert_array_equal(first, second)

    def test_exact_mean_threshold_and_no_average_compensation(self):
        metrics = {direction: {kind: {"minimum": 5, "weight_sum": 22, "count": 3}
                              for kind in ("single", "double")} for direction in ("forward", "inverse")}
        targets = {"min_single": 5, "min_double": 5, "mean_single_milli": 7333, "mean_double_milli": 7333}
        self.assertEqual(score_metrics(metrics, targets), (1.0, []))
        targets["mean_double_milli"] = 7334
        self.assertEqual(len(score_metrics(metrics, targets)[1]), 2)
        targets["mean_double_milli"] = 7333
        metrics["inverse"]["single"]["minimum"] = 4
        self.assertEqual(score_metrics(metrics, targets)[0], 0.8)

    def test_symplectic_commutation(self):
        n = 8
        family = {"n": n, "edges": [[qubit, qubit + 1] for qubit in range(n - 1)],
                  "max_rounds": 12, "max_cx": 40}
        layers = random_layers(family, random.Random(713))
        forward, inverse = generator_images(n, output_rows(n, layers))
        mask = (1 << n) - 1
        for images in (forward, inverse):
            for first in range(2 * n):
                for second in range(2 * n):
                    first_image, second_image = int(images[first]), int(images[second])
                    parity = (((first_image & mask) & (second_image >> n)).bit_count()
                              + ((first_image >> n) & (second_image & mask)).bit_count()) % 2
                    self.assertEqual(parity, int(abs(first - second) == n))


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.spec = {"families": [{"id": "test", "n": 4, "edges": [[0, 1], [1, 2], [2, 3]],
                                   "max_rounds": 2, "max_cx": 2}]}
        self.artifact = {"schema_version": 1, "circuits": [{"family": "test", "layers": [
            {"local": ["I", "H", "S", "HS"], "cx": [[0, 1], [2, 3]]}]}]}

    def rejects(self, artifact):
        with self.assertRaises(InvalidSubmission):
            validate_submission(artifact, self.spec)

    def test_valid_and_empty_identity(self):
        validate_submission(self.artifact, self.spec)
        self.artifact["circuits"][0]["layers"] = []
        validate_submission(self.artifact, self.spec)

    def test_bad_schema_family_and_metadata(self):
        for version in (True, 1.0, 2, "1", None):
            artifact = copy.deepcopy(self.artifact)
            artifact["schema_version"] = version
            self.rejects(artifact)
        for family_id in ([], None, "unknown", 12):
            artifact = copy.deepcopy(self.artifact)
            artifact["circuits"][0]["family"] = family_id
            self.rejects(artifact)
        artifact = copy.deepcopy(self.artifact)
        artifact["score"] = 1.0
        self.rejects(artifact)
        self.rejects({"schema_version": 1, "circuits": []})
        self.rejects({"schema_version": 1, "circuits": self.artifact["circuits"] * 2})

    def test_range_matching_topology_and_budget(self):
        bad_gates = [[[-1, 1]], [[0, 4]], [[True, 1]], [[0.0, 1]], [[0, 0]], [[0, 2]],
                     [[0, 1], [1, 2]], [[0, 1], [1, 0]], [[0]], [[0, 1, 2]], [["0", 1]]]
        for gates in bad_gates:
            artifact = copy.deepcopy(self.artifact)
            artifact["circuits"][0]["layers"][0]["cx"] = gates
            self.rejects(artifact)
        artifact = copy.deepcopy(self.artifact)
        artifact["circuits"][0]["layers"] *= 2
        self.rejects(artifact)
        artifact["circuits"][0]["layers"] *= 2
        self.rejects(artifact)

    def test_unsupported_and_malformed_local_gates(self):
        for gate in ("T", "CNOT", "SDG", "HH", "", 2, None, {}, float("inf")):
            artifact = copy.deepcopy(self.artifact)
            artifact["circuits"][0]["layers"][0]["local"][0] = gate
            self.rejects(artifact)
        artifact = copy.deepcopy(self.artifact)
        artifact["circuits"][0]["layers"][0]["local"].pop()
        self.rejects(artifact)

    def test_json_duplicate_nonfinite_malformed_and_size(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as temporary:
            path = Path(temporary) / "bad.json"
            for data in (b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":Infinity}',
                         b'{"x":-Infinity}', b'{"x":1e999}', b'{"x":' + b'9' * 100 + b'}',
                         b'{', b'\xff', b'[' * 2000):
                path.write_bytes(data)
                with self.assertRaises(InvalidSubmission):
                    load_json(path)
            path.write_bytes(b' ' * 33)
            with self.assertRaises(InvalidSubmission):
                load_json(path, limit=32)

    def test_duplicate_family_with_correct_list_length(self):
        self.spec["families"].append(dict(self.spec["families"][0], id="second"))
        self.artifact["circuits"] *= 2
        self.rejects(self.artifact)

    def test_no_execution_and_complete_failure_diagnostics(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as temporary:
            path = Path(temporary) / "artifact.json"
            sentinel = Path(temporary) / "must_not_exist"
            path.write_text(json.dumps({"schema_version": 1, "circuits": [],
                "python": f"open({str(sentinel)!r}, 'w').write('executed')"}))
            report = EVALUATOR.evaluate(path)
            self.assertFalse(sentinel.exists())
            self.assertFalse(report["valid"])
            self.assertFalse(report["passed"])
            self.assertEqual(report["core_score"], 0)
            self.assertEqual(report["resource_score"], 0)
            self.assertEqual(report["worst_family_score"], 0)
            self.assertEqual(report["runtime"], report["runtime_seconds"])
            self.assertGreater(report["runtime_score"], 0)
            self.assertTrue(report["reason"])

    def test_evaluator_identity_resource_accounting(self):
        spec, _ = load_json(ROOT / "evaluator/hidden/frozen_spec.json")
        artifact = {"schema_version": 1, "circuits": [{"family": family["id"], "layers": []}
                                                      for family in spec["families"]]}
        with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as temporary:
            path = Path(temporary) / "artifact.json"
            path.write_text(json.dumps(artifact))
            report = EVALUATOR.evaluate(path)
        self.assertTrue(report["valid"])
        self.assertFalse(report["passed"])
        self.assertEqual(report["resource_score"], 1)
        self.assertEqual(report["resources"]["cx_count"], 0)
        self.assertEqual(report["resources"]["h_count"], 0)
        self.assertEqual(report["resources"]["max_primitive_depth"], 0)

    def test_symlink_rejected_without_following_private_target(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as temporary:
            target = Path(temporary) / "private.json"
            target.write_text('{"secret": "not a submission"}')
            link = Path(temporary) / "artifact.json"
            link.symlink_to(target)
            with self.assertRaises(InvalidSubmission):
                load_json(link)
            report = EVALUATOR.evaluate(link)
            self.assertFalse(report["valid"])
            self.assertIn("symlinks", report["reason"])
            self.assertNotIn("artifact_sha256", report)

    def test_hardlink_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as temporary:
            target = Path(temporary) / "private.json"
            target.write_text("{}")
            link = Path(temporary) / "artifact.json"
            os.link(target, link)
            for path in (target, link):
                with self.assertRaises(InvalidSubmission):
                    load_json(path)

    def test_directory_and_fifo_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as temporary:
            with self.assertRaises(InvalidSubmission):
                load_json(temporary)
            fifo = Path(temporary) / "artifact.json"
            os.mkfifo(fifo)
            with self.assertRaises(InvalidSubmission):
                load_json(fifo)


if __name__ == "__main__":
    unittest.main(verbosity=2)
