import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

from evaluate import ROOT, launch, load_frozen_input
from kernel import WitnessError, circuit_unitary, parse_json, read_json, score_payload, target_matrix, unitary_metrics

sys.path.insert(0, str(ROOT / "authoring"))
from dense_reference import dense_unitary


class EvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specification, cls.contents, cls.digest = load_frozen_input()
        cls.witness = read_json(ROOT / "evaluator/hidden/witness.json")

    def test_private_witness_passes(self):
        report = score_payload(self.specification, self.witness)
        self.assertTrue(report["target_met"])
        self.assertEqual(report["core_score"], 1.0)

    def test_independent_dense_reconstruction(self):
        for target in self.specification["targets"]:
            gates = self.witness[target["id"]]
            dense = dense_unitary(target["n_qubits"], gates)
            efficient = circuit_unitary(target["n_qubits"], gates)
            np.testing.assert_allclose(dense, efficient, atol=5e-13, rtol=0)
            self.assertLess(unitary_metrics(target_matrix(target), dense)["normalized_frobenius"], 1e-12)

    def test_global_phase_is_ignored(self):
        target = self.specification["targets"][0]
        matrix = target_matrix(target)
        metrics = unitary_metrics(matrix, np.exp(0.371j) * matrix)
        self.assertLess(metrics["infidelity"], 1e-12)
        self.assertLess(metrics["normalized_frobenius"], 1e-12)

    def test_identity_is_valid_but_fails(self):
        report = score_payload(self.specification, {name: [] for name in self.witness})
        self.assertTrue(report["valid"])
        self.assertFalse(report["target_met"])
        self.assertEqual(report["core_score"], 0.0)

    def test_full_operator_not_first_column(self):
        demo, contents, digest = load_frozen_input(True)
        identity = np.eye(4)
        np.testing.assert_allclose(target_matrix(demo["targets"][0])[:, 0], identity[:, 0])
        self.assertFalse(score_payload(demo, {"demo_2q": []})["target_met"])

    def test_demo_and_cnot_direction(self):
        demo, contents, digest = load_frozen_input(True)
        correct = read_json(ROOT / "participant/input/demo_witness.json")
        self.assertTrue(score_payload(demo, correct)["target_met"])
        reverse = {"demo_2q": [{"gate": "CNOT", "control": 1, "target": 0}]}
        self.assertFalse(score_payload(demo, reverse)["target_met"])

    def test_invalid_gates_and_scalars(self):
        rotation = {"gate": "U3", "qubit": 0, "theta": 0.1, "phi": 0.2, "lambda": 0.3}
        invalid = [
            {"gate": "CNOT", "control": 0, "target": 2},
            {"gate": "CNOT", "control": 0, "target": 0},
            {"gate": "CNOT", "control": True, "target": 1},
            {"gate": "CNOT", "control": 0.0, "target": 1},
            {"gate": "DenseMatrix", "matrix": [[1]]},
            {**rotation, "theta": float("nan")},
            {**rotation, "phi": float("inf")},
            {**rotation, "lambda": "0.3"},
            {**rotation, "theta": True},
            {**rotation, "theta": 10 ** 400},
            {**rotation, "qubit": -1},
            {**rotation, "qubit": 4},
            {**rotation, "extra": 1},
        ]
        for gate in invalid:
            with self.subTest(gate=str(gate)[:80]):
                answer = copy.deepcopy(self.witness)
                answer["unitary_4q"] = [gate]
                report = score_payload(self.specification, answer)
                self.assertFalse(report["valid"])
                self.assertFalse(report["cases"][0]["passed"])

    def test_budget_caps(self):
        for kind, count in (("CNOT", 13), ("U3", 81)):
            answer = copy.deepcopy(self.witness)
            gate = ({"gate": "CNOT", "control": 0, "target": 1} if kind == "CNOT" else
                    {"gate": "U3", "qubit": 0, "theta": 0, "phi": 0, "lambda": 0})
            answer["unitary_4q"] = [gate] * count
            self.assertFalse(score_payload(self.specification, answer)["valid"])

    def test_strict_json_and_target_ids(self):
        for contents in ('{"same":1,"same":2}', '{"value":NaN}', '{"value":Infinity}'):
            with self.assertRaises(WitnessError):
                parse_json(contents)
        for answer in ({}, [], {**self.witness, "extra": []}):
            with self.assertRaises(WitnessError):
                score_payload(self.specification, answer)

    def test_finite_large_angles(self):
        gate = {"gate": "U3", "qubit": 0, "theta": 1e308, "phi": 1e308, "lambda": 1e308}
        matrix = circuit_unitary(1, [gate])
        self.assertTrue(np.all(np.isfinite(matrix)))
        np.testing.assert_allclose(matrix.conj().T @ matrix, np.eye(2), atol=1e-14)

    def test_tolerance_rejects_nearby_but_wrong_operator(self):
        answer = copy.deepcopy(self.witness)
        answer["unitary_4q"][0]["theta"] += 0.002
        report = score_payload(self.specification, answer)
        self.assertFalse(report["cases"][0]["passed"])
        self.assertEqual(report["core_score"], 0.5)

    def test_isolated_baseline(self):
        answer, process = launch(ROOT / "participant/baseline", self.contents, seconds=20)
        self.assertEqual(process["returncode"], 0, process)
        self.assertEqual(process["remaining_owned_descendants"], [])
        self.assertTrue(score_payload(self.specification, answer)["valid"])

    def test_isolation_hides_private_witness(self):
        with tempfile.TemporaryDirectory(prefix="probe-", dir=ROOT / "adversary") as temporary:
            submission = Path(temporary)
            private_path = str(ROOT / "evaluator/hidden/witness.json")
            program = (
                "import json, sys\nfrom pathlib import Path\n"
                "try:\n    Path(" + repr(private_path) + ").read_text()\n"
                "except (FileNotFoundError, PermissionError):\n    pass\n"
                "else:\n    raise RuntimeError('private witness exposed')\n"
                "specification = json.loads(Path(sys.argv[1]).read_text())\n"
                "Path(sys.argv[2]).write_text(json.dumps({target['id']: [] for target in specification['targets']}))\n"
            )
            (submission / "solution.py").write_text(program)
            answer, process = launch(submission, self.contents, seconds=20)
            self.assertEqual(process["returncode"], 0, process)
            self.assertTrue(score_payload(self.specification, answer)["valid"])


if __name__ == "__main__":
    (ROOT / "adversary").mkdir(exist_ok=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(EvaluatorTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    (ROOT / "adversary/checker_tests.json").write_text(json.dumps({
        "tests_run": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "successful": result.wasSuccessful(),
        "fresh_agents_launched": 0,
    }, indent=2) + "\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
