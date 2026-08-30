import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.linalg import expm


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "input"))
sys.path.insert(0, str(ROOT / "participant" / "baseline"))
from model import BOUNDS, CONFIG, MEASUREMENTS, PAULIS, compile_experiments, draw_parameters, probabilities, unitaries, validate_experiment
from runtime import run_episode, start_message
from solution import fixed_schedule
from evaluate import SubmissionError, evaluate, failure_report, load_sandbox


def independent_probability(parameters, experiment):
    identity = np.eye(2, dtype=complex)
    pauli_x = np.array([[0, 1], [1, 0]], dtype=complex)
    pauli_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    pauli_z = np.array([[1, 0], [0, -1]], dtype=complex)
    axes = {"I": identity, "X": pauli_x, "Y": pauli_y, "Z": pauli_z}
    omega_ix, omega_zx, omega_iz, omega_zz, omega_zi, visibility, contrast, bias, decay = parameters
    dense_hamiltonian = (omega_ix * np.kron(identity, pauli_x) + omega_zx * np.kron(pauli_z, pauli_x)
                         + omega_iz * np.kron(identity, pauli_z) + omega_zz * np.kron(pauli_z, pauli_z)
                         + omega_zi * np.kron(pauli_z, identity)) / 2
    density_parts = [(identity + (1 if state[1] == "+" else -1) * visibility * axes[state[0]]) / 2 for state in experiment["prep"]]
    density = np.kron(*density_parts)
    evolution = expm(-1j * experiment["time"] * dense_hamiltonian)
    density = evolution @ density @ evolution.conj().T
    damping = np.exp(-decay * experiment["time"])
    density = damping * density + (1 - damping) * np.eye(4) / 4
    observable = np.kron(axes[experiment["measure"][0]], axes[experiment["measure"][1]])
    return (1 + bias + contrast * np.trace(observable @ density).real) / 2, evolution


def information_audit():
    episodes = json.loads((ROOT / "evaluator" / "hidden" / "episodes.json").read_text())["episodes"]
    schedule = fixed_schedule()
    batch = compile_experiments(schedule)
    scales = np.array(CONFIG["normalization"] + [1, 1, 1, 1])
    records = []
    for episode in episodes:
        parameters = np.array(episode["parameters"])
        center = probabilities(parameters, batch)
        columns = []
        for parameter_index in range(9):
            step = np.zeros(9)
            step[parameter_index] = 1e-5
            columns.append((probabilities(parameters + step, batch) - probabilities(parameters - step, batch)) / 2e-5)
        jacobian = np.stack(columns, axis=1)
        scaled = jacobian * scales
        singular_values = np.linalg.svd(scaled, compute_uv=False)
        fisher = scaled.T @ ((128 / (center * (1 - center)))[:, None] * scaled)
        covariance = np.linalg.inv(fisher)
        records.append({"family": episode["family"], "rank": int(np.linalg.matrix_rank(scaled, tol=1e-7)),
                        "minimum_singular_value": float(singular_values[-1]),
                        "fixed_design_local_crlb_rms": float(np.sqrt(np.trace(covariance[:5, :5]) / 5))})
    report = {"all_rank_nine": all(record["rank"] == 9 for record in records),
              "minimum_singular_value": min(record["minimum_singular_value"] for record in records),
              "family_mean_local_crlb_rms": {family: float(np.mean([record["fixed_design_local_crlb_rms"] for record in records if record["family"] == family])) for family in CONFIG["suite"]["families"]},
              "interpretation": "Local unbiased fixed-design Fisher diagnostic, not a global achievability proof or an adaptive-design bound",
              "episodes": records}
    (ROOT / "adversary" / "identifiability.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


class PhysicsTests(unittest.TestCase):
    def test_dense_exponential_and_sampling_law(self):
        rng = np.random.default_rng(19047)
        for family in CONFIG["suite"]["families"]:
            for repetition in range(4):
                parameters = draw_parameters(rng, family)
                for measurement in MEASUREMENTS:
                    experiment = {"type": "experiment", "prep": [str(rng.choice(["X+", "Y-", "Z+"])), str(rng.choice(["X-", "Y+", "Z-"]))],
                                  "measure": measurement, "time": float(rng.uniform(0, 12)), "shots": 128}
                    expected, dense = independent_probability(parameters, experiment)
                    np.testing.assert_allclose(unitaries(parameters, [experiment["time"]])[0], dense, atol=2e-13)
                    self.assertAlmostEqual(float(probabilities(parameters, [experiment])[0]), expected, places=12)

    def test_zero_block_and_unitarity(self):
        parameters = np.array([0.3, -0.3, 0.2, -0.2, 1.4, 0.9, 0.9, 0.02, 0.03])
        for duration in [0, 0.03, 12]:
            unitary = unitaries(parameters, [duration])[0]
            np.testing.assert_allclose(unitary @ unitary.conj().T, np.eye(4), atol=1e-13)
            experiment = {"prep": ["Y+", "X-"], "measure": "YX", "time": duration}
            expected, dense = independent_probability(parameters, experiment)
            np.testing.assert_allclose(unitary, dense, atol=1e-13)

    def test_phase_sign_anchor(self):
        parameters = np.array([0, 0, 0, 0, 0.7, 0.95, 0.9, 0, 0.02])
        experiment = {"prep": ["X+", "Z+"], "measure": "YI", "time": 0.3}
        self.assertGreater(float(probabilities(parameters, [experiment])[0]), 0.5)
        parameters[4] *= -1
        self.assertLess(float(probabilities(parameters, [experiment])[0]), 0.5)

    def test_jacobian_rank(self):
        self.assertTrue(information_audit()["all_rank_nine"])

    def test_baseline_budget(self):
        schedule = fixed_schedule()
        self.assertEqual(len(schedule), 192)
        self.assertEqual(sum(experiment["shots"] for experiment in schedule), 24576)
        for experiment in schedule:
            validate_experiment(experiment)

    def test_hello_does_not_reveal_secrets(self):
        self.assertEqual(set(start_message()), {"type", "protocol", "budget", "parameter_order", "bounds", "normalization"})

    def test_failure_reports(self):
        with self.assertRaises(SubmissionError):
            evaluate(ROOT / "not_a_submission_9913287")
        invalid = failure_report("missing submission")
        self.assertEqual(invalid["core_score"], 30.0)
        self.assertEqual(invalid["worst_family_score"], 30.0)
        self.assertEqual(invalid["resource_score"], 0.0)
        self.assertFalse(invalid["infrastructure_error"])
        unavailable = failure_report("manifest unavailable", infrastructure=True)
        self.assertIsNone(unavailable["core_score"])
        self.assertTrue(unavailable["infrastructure_error"])


class ProtocolTests(unittest.TestCase):
    def run_script(self, text, seconds=3, sandbox=False):
        parameters = draw_parameters(np.random.default_rng(2), "aliasing")
        with tempfile.TemporaryDirectory(prefix="cr-selftest-", dir=ROOT / "adversary") as directory:
            script = Path(directory) / "solution.py"
            script.write_text(text)
            command = load_sandbox()(ROOT / "participant", directory, ready_marker=True) if sandbox else [sys.executable, "-u", str(script)]
            return run_episode(command, parameters, 991, wall_seconds=seconds, startup_handshake=sandbox)

    def test_valid_sandbox_and_isolation(self):
        text = "import json, pathlib, sys\nimport numpy, scipy.optimize\njson.loads(sys.stdin.readline())\n"
        text += "assert pathlib.Path('/task/input/model.py').is_file()\nassert not pathlib.Path('/task/../evaluator').exists()\n"
        text += "assert not pathlib.Path(" + repr(str(ROOT / "evaluator" / "hidden" / "episodes.json")) + ").exists()\n"
        text += "print(json.dumps({'type':'estimate','omega':[0,0,0,0,0]}),flush=True)\n"
        result = self.run_script(text, seconds=20, sandbox=True)
        self.assertTrue(result["valid"], result)

    def test_invalid_json_and_nonfinite(self):
        for payload in ['{"type":"estimate","omega":[NaN,0,0,0,0]}', '{"type":"estimate","type":"estimate","omega":[0,0,0,0,0]}', '[]', '{"type":"estimate","omega":[true,0,0,0,0]}', '{"type":"estimate","omega":[18446744073709551616,0,0,0,0]}']:
            result = self.run_script("print(" + repr(payload) + ",flush=True)\n")
            self.assertFalse(result["valid"])

    def test_hang_and_output_caps(self):
        result = self.run_script("import time\ntime.sleep(60)\n", seconds=0.3)
        self.assertFalse(result["valid"])
        self.assertLess(result["wall_seconds"], 2)
        result = self.run_script("print('x'*300000,flush=True)\n")
        self.assertFalse(result["valid"])

    def test_trusted_startup_separate_clock(self):
        parameters = draw_parameters(np.random.default_rng(2), "aliasing")
        text = "import sys,time\ntime.sleep(.4)\nprint('{\"sandbox_ready\":true}',flush=True)\nsys.stdin.readline()\nprint('{\"type\":\"estimate\",\"omega\":[0,0,0,0,0]}',flush=True)\n"
        result = run_episode([sys.executable, "-u", "-c", text], parameters, 3, wall_seconds=0.3, startup_handshake=True)
        self.assertTrue(result["valid"], result)
        self.assertGreater(result["startup_wall_seconds"], 0.39)
        self.assertLess(result["wall_seconds"], 0.3)
        result = run_episode([sys.executable, "-u", "-c", "print('{}',flush=True)"], parameters, 3, startup_handshake=True)
        self.assertTrue(result["infrastructure_error"])

    def test_budget_excess(self):
        text = "import json,sys\njson.loads(sys.stdin.readline())\n"
        text += "for index in range(7):\n print(json.dumps({'type':'experiment','prep':['Z+','Z+'],'measure':'IZ','time':0,'shots':4096}),flush=True)\n sys.stdin.readline()\n"
        result = self.run_script(text)
        self.assertFalse(result["valid"])
        self.assertIn("budget", result["reason"])
        self.assertEqual(result["shots"], 24576)

    def test_exit_and_extra_output(self):
        for suffix in ["raise SystemExit(2)\n", "print('extra',flush=True)\n"]:
            result = self.run_script("print('{\"type\":\"estimate\",\"omega\":[0,0,0,0,0]}',flush=True)\n" + suffix)
            self.assertFalse(result["valid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
