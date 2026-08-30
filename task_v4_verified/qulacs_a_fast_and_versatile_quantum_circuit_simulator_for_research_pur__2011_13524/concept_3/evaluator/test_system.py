import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "input"))
sys.path.insert(0, str(ROOT / "evaluator"))

from evaluate import ProtocolError, load_suite, parse_message, run_episode
from simulator import BOUNDS, BUDGET, FAMILIES, MODES, parameter_dict, probabilities, sample_prior, score_estimate, validate_action, validate_estimate


def density_probability(theta, action):
    f1, f2, coupling, sigma1, sigma2, rho, vis1, vis2, bias1, bias2 = theta
    basis_signs = np.array([[1, 1], [1, -1], [-1, 1], [-1, -1]])
    energies = np.pi * (f1 * basis_signs[:, 0] + f2 * basis_signs[:, 1] + coupling * basis_signs[:, 0] * basis_signs[:, 1])
    mode = action["mode"]
    if mode == "q1+":
        state = np.array([1, 0, 1, 0]) / np.sqrt(2)
    elif mode == "q1-":
        state = np.array([0, 1, 0, 1]) / np.sqrt(2)
    elif mode == "q2+":
        state = np.array([1, 1, 0, 0]) / np.sqrt(2)
    elif mode == "q2-":
        state = np.array([0, 0, 1, 1]) / np.sqrt(2)
    elif mode == "bell+":
        state = np.array([1, 0, 0, 1]) / np.sqrt(2)
    else:
        state = np.array([0, 1, 1, 0]) / np.sqrt(2)
    evolution = np.exp(-1j * energies * action["time"])
    density = np.outer(state * evolution, (state * evolution).conj())
    covariance = np.array([[sigma1 ** 2, rho * sigma1 * sigma2], [rho * sigma1 * sigma2, sigma2 ** 2]])
    differences = basis_signs[:, None, :] - basis_signs[None, :, :]
    exponent = np.einsum("abi,ij,abj->ab", differences, covariance, differences)
    density *= np.exp(-action["time"] ** 2 * exponent / 8)
    phase = action["phase"]
    rotated = np.array([[0, np.exp(-1j * phase)], [np.exp(1j * phase), 0]])
    pauli_x = np.array([[0, 1], [1, 0]])
    identity = np.eye(2)
    if mode.startswith("q1"):
        observable = np.kron(bias1 * identity + vis1 * rotated, identity)
    elif mode.startswith("q2"):
        observable = np.kron(identity, bias2 * identity + vis2 * rotated)
    else:
        observable = np.kron(bias1 * identity + vis1 * rotated, bias2 * identity + vis2 * pauli_x)
    return (1 + np.trace(density @ observable).real) / 2, density


class PhysicsTests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(98765)

    def test_priors_are_physical_and_in_range(self):
        for family in FAMILIES:
            for _ in range(100):
                theta = sample_prior(family, self.rng)
                validate_estimate({"type": "estimate", "parameters": parameter_dict(theta)})
                self.assertLessEqual(theta[6] + abs(theta[8]), 1)
                self.assertLessEqual(theta[7] + abs(theta[9]), 1)

    def test_independent_density_matrix_reference(self):
        for family in FAMILIES:
            for _ in range(12):
                theta = sample_prior(family, self.rng)
                for mode in MODES:
                    action = {"mode": mode, "time": self.rng.uniform(0, 6), "phase": self.rng.uniform(-np.pi, np.pi)}
                    reference, density = density_probability(theta, action)
                    self.assertAlmostEqual(reference, probabilities(theta, [action])[0], places=12)
                    self.assertAlmostEqual(float(np.trace(density).real), 1, places=12)
                    self.assertGreaterEqual(np.linalg.eigvalsh(density).min(), -1e-12)

    def test_probability_bounds_across_corners(self):
        for _ in range(300):
            theta = np.where(self.rng.integers(0, 2, 10), BOUNDS[:, 0], BOUNDS[:, 1])
            actions = [{"mode": mode, "time": self.rng.uniform(0, 6), "phase": self.rng.uniform(-np.pi, np.pi)} for mode in MODES]
            predicted = probabilities(theta, actions)
            self.assertTrue(np.all((predicted >= 0) & (predicted <= 1)))

    def test_analytic_jacobian(self):
        theta = sample_prior("close_coupled", self.rng)
        actions = [{"mode": mode, "time": 2.13, "phase": 0.67} for mode in MODES]
        _, gradient = probabilities(theta, actions, jacobian=True)
        for column in range(10):
            delta = np.zeros(10)
            delta[column] = 1e-6
            numerical = (probabilities(theta + delta, actions) - probabilities(theta - delta, actions)) / 2e-6
            np.testing.assert_allclose(gradient[:, column], numerical, atol=2e-8, rtol=1e-6)

    def test_local_measurements_cannot_identify_rho(self):
        theta = sample_prior("resolved", self.rng)
        changed = theta.copy()
        changed[5] *= -1
        actions = [{"mode": mode, "time": 2.9, "phase": 0.4} for mode in MODES[:4]]
        np.testing.assert_array_equal(probabilities(theta, actions), probabilities(changed, actions))

    def test_integer_time_alias_and_off_grid_resolution(self):
        theta = sample_prior("resolved", self.rng)
        changed = theta.copy()
        changed[0] += 1
        actions = [{"mode": mode, "time": 2.0, "phase": 0.4} for mode in MODES]
        np.testing.assert_allclose(probabilities(theta, actions), probabilities(changed, actions), atol=1e-12)
        actions[0]["time"] = 0.31
        self.assertGreater(abs(probabilities(theta, actions)[0] - probabilities(changed, actions)[0]), 0.05)

    def test_decoherence_free_bell_limit(self):
        theta = sample_prior("resolved", self.rng)
        theta[3:5] = 0.3
        theta[5] = 1.0
        action = {"mode": "bell-", "time": 5.1, "phase": 0.0}
        reference = theta.copy()
        reference[3:5] = 0
        np.testing.assert_allclose(probabilities(theta, [action]), probabilities(reference, [action]))

    def test_perfect_score(self):
        theta = sample_prior("resolved", self.rng)
        self.assertEqual(score_estimate(theta, theta)["score"], 100)

    def test_fixed_suite_is_balanced_and_disjoint(self):
        hidden, _ = load_suite()
        public, _ = load_suite(True)
        self.assertEqual(len(hidden), 18)
        self.assertEqual(set(item["outcome_seed"] for item in hidden) & set(item["outcome_seed"] for item in public), set())

    def test_frozen_target_is_consistent(self):
        objective = json.loads((ROOT / "participant" / "input" / "OBJECTIVE.json").read_text())
        config = json.loads((ROOT / "evaluator" / "config.json").read_text())
        self.assertEqual(objective["target"], {"mean": 88.0, "worst_family": 85.0})
        self.assertEqual(objective["target"], config["target"])
        self.assertEqual(objective["target_status"], config["target_status"])


class ProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "evaluator" / "config.json").read_text())
        cls.episode = load_suite(True)[0][0]

    def run_code(self, code, wall_seconds=None):
        config = dict(self.config)
        if wall_seconds is not None:
            config["episode_wall_seconds"] = wall_seconds
        with tempfile.TemporaryDirectory(prefix="ramsey-test-") as temporary:
            directory = Path(temporary)
            (directory / "solution.py").write_text(code)
            return run_episode(directory, self.episode, config)

    def reject_output(self, output, expected):
        result = self.run_code("import sys\nsys.stdin.readline()\nprint(" + repr(output) + ", flush=True)\n")
        self.assertFalse(result["valid"], result)
        self.assertEqual(result["score"], 0)
        self.assertIn(expected, result["reason"])

    def test_malformed_and_nonfinite_json(self):
        for output in ("not-json", '{"type": NaN}', '{"type": Infinity}', '{"type": 1, "type": 2}'):
            with self.subTest(output=output):
                self.reject_output(output, "malformed JSON")
        self.reject_output("[]", "JSON object")

    def test_invalid_actions(self):
        base = {"type": "experiment", "mode": "q1+", "time": 1.0, "phase": 0.0, "shots": 10}
        changes = [("time", -0.1), ("time", 6.1), ("time", True), ("phase", 3.2),
                   ("shots", 1.5), ("shots", True), ("shots", 0), ("shots", 1025), ("mode", "oracle")]
        for name, value in changes:
            with self.subTest(name=name, value=value):
                message = dict(base, **{name: value})
                result = self.run_code("import sys\nsys.stdin.readline()\nprint(" + repr(json.dumps(message)) + ")\n")
                self.assertFalse(result["valid"], result)
                self.assertEqual(result["queries"], 0)
        self.reject_output(json.dumps(dict(base, extra=1)), "exactly")
        self.reject_output(json.dumps(base).replace('1.0', '1e309'), "finite")

    def test_invalid_estimates(self):
        message = {"type": "estimate", "parameters": dict(self.episode["parameters"])}
        message["parameters"]["rho"] = 1.1
        self.reject_output(json.dumps(message), "out of range")
        message["parameters"]["rho"] = "0.1"
        self.reject_output(json.dumps(message), "finite")
        message["parameters"].pop("rho")
        self.reject_output(json.dumps(message), "ten named")
        self.reject_output('{"type":"estimate", "parameters":{"rho":NaN}}', "malformed JSON")

    def test_query_budget(self):
        action = {"type": "experiment", "mode": "q1+", "time": 0, "phase": 0, "shots": 1}
        result = self.run_code("import sys\nfor line in sys.stdin:\n    print(" + repr(json.dumps(action)) + ", flush=True)\n")
        self.assertIn("query budget", result["reason"])
        self.assertEqual(result["queries"], BUDGET["queries"])

    def test_shot_budget(self):
        action = {"type": "experiment", "mode": "q1+", "time": 0, "phase": 0, "shots": 1024}
        result = self.run_code("import sys\nfor line in sys.stdin:\n    print(" + repr(json.dumps(action)) + ", flush=True)\n")
        self.assertIn("shot budget", result["reason"])
        self.assertEqual(result["shots"], BUDGET["shots"])

    def test_line_limit_exit_and_timeout(self):
        self.reject_output(" " * 17000, "line limit")
        self.reject_output("", "malformed JSON")
        result = self.run_code("import time\ntime.sleep(10)\n", wall_seconds=0.1)
        self.assertIn("wall-time", result["reason"])
        result = self.run_code("import sys\nsys.stdin.readline()\n", wall_seconds=1)
        self.assertIn("child exited", result["reason"])

    def test_controlled_input_and_process_boundary(self):
        estimate = {"type": "estimate", "parameters": self.episode["parameters"]}
        code = (
            "import json, os, sys\n"
            "message=json.loads(sys.stdin.readline())\n"
            "assert sys.argv == ['solution.py']\n"
            "assert message['type']=='start' and 'parameters' not in message\n"
            "assert not any('seed' in key or 'hidden' in key for key in message)\n"
            "assert 'PYTHONPATH' not in os.environ\n"
            "assert len(os.sched_getaffinity(0)) == 1\n"
            "assert not os.path.exists(" + repr(str(ROOT / "evaluator" / "hidden" / "episodes.json")) + ")\n"
            "assert not os.path.exists('/proc/" + str(__import__('os').getpid()) + "/environ')\n"
            "assert not os.path.exists('evaluator')\n"
            "print(" + repr(json.dumps(estimate)) + ", flush=True)\n"
        )
        result = self.run_code(code)
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["score"], 100)

    def test_final_extra_output_and_nonzero_exit(self):
        estimate = json.dumps({"type": "estimate", "parameters": self.episode["parameters"]})
        self.reject_output(estimate + "\n{}", "multiple responses")
        code = "import sys\nsys.stdin.readline()\nprint(" + repr(estimate) + ", flush=True)\nsys.exit(2)\n"
        result = self.run_code(code)
        self.assertFalse(result["valid"])
        self.assertIn("nonzero", result["reason"])

    def test_reject_symlink_submission(self):
        with tempfile.TemporaryDirectory(prefix="ramsey-test-") as temporary:
            directory = Path(temporary)
            (directory / "solution.py").symlink_to(ROOT / "participant" / "baseline" / "solution.py")
            result = run_episode(directory, self.episode, self.config)
            self.assertFalse(result["valid"])
            self.assertIn("symlink", result["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
