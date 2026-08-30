import copy
import itertools
import json
import math
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant"))
from baseline import baseline_policy
from cascade_sim import Cascade, FEATURES, block_size, choose_action, load_policy, run_frame, validate_policy
from scoring import wilson_upper


class ProtocolTests(unittest.TestCase):
    def test_exhaustive_small_frames(self):
        for error_count in range(9):
            for errors in itertools.combinations(range(8), error_count):
                engine = Cascade(8, errors)
                engine.run_pass(tuple(range(8)), 4, 0)
                engine.run_pass((0, 2, 4, 6, 1, 3, 5, 7), 2, 1)
                engine.run_pass(tuple(range(8)), 1, 2)
                self.assertEqual(engine.current, 0)
                self.assertEqual(engine.corrected, len(errors))
                self.assertTrue(all(not engine.odd(node) for node in engine.known.values()))

    def test_parallel_queries_and_known_parities(self):
        engine = Cascade(8, [0, 4])
        first = engine.run_pass(tuple(range(8)), 4, 0)
        self.assertEqual((first["disclosed"], first["rounds"], first["corrected"]), (6, 3, 2))
        second = engine.run_pass(tuple(range(8)), 4, 1)
        self.assertEqual((second["disclosed"], second["rounds"]), (0, 0))

    def test_inferred_last_root(self):
        engine = Cascade(8, [])
        engine.run_pass(tuple(range(8)), 4, 0)
        result = engine.run_pass((0, 2, 4, 6, 1, 3, 5, 7), 4, 1)
        self.assertEqual(result["disclosed"], 1)
        self.assertEqual(result["rounds"], 1)

    def test_cascade_and_reuse(self):
        engine = Cascade(8, [0, 1])
        engine.run_pass(tuple(range(8)), 4, 0)
        self.assertEqual(engine.current.bit_count(), 2)
        engine.run_pass((0, 2, 3, 4, 1, 5, 6, 7), 4, 1)
        self.assertEqual(engine.current, 0)
        self.assertTrue(all(not engine.odd(node) for node in engine.known.values()))

    def test_no_oracle_stop(self):
        case = {"frame_bits": 64, "q_true": 0.01, "estimate_bias": 1, "sample_size": 128, "latency": 0.002}
        result = run_frame(case, 25, baseline_policy(), errors=[], trace=True)
        self.assertEqual(result["passes"], 14)
        self.assertEqual(result["failure"], 0)
        for step in result["trace"]:
            self.assertEqual(set(step["features"]), FEATURES)
            self.assertNotIn("q_true", step["features"])
            self.assertNotIn("seed", step["features"])

    def test_determinism_and_modes(self):
        case = {"frame_bits": 128, "q_true": 0.05, "estimate_bias": 0.5, "sample_size": 128, "latency": 0.002}
        for reuse in ["all", "roots", "recent"]:
            for batch in ["pass", "smallest"]:
                policy = baseline_policy()
                for action in policy["schedule"]:
                    action.update(reuse=reuse, batch=batch)
                first = run_frame(case, 7451, policy, trace=True)
                self.assertEqual(first, run_frame(case, 7451, policy, trace=True))
                self.assertEqual(first["failure"], 0)

    def test_failure_cost(self):
        case = {"frame_bits": 64, "q_true": 0.01, "estimate_bias": 1, "sample_size": 128, "latency": 0.002}
        policy = baseline_policy()
        policy["max_passes"] = 4
        for action in policy["schedule"]:
            action["size"] = {"basis": "frame", "scale": 0.5, "round": "nearest"}
        failures = [run_frame(case, seed, policy, errors=[0, 1]) for seed in range(40)]
        failures = [result for result in failures if result["failure"]]
        self.assertTrue(failures)
        entropy = -0.01 * math.log2(0.01) - 0.99 * math.log2(0.99)
        for result in failures:
            self.assertEqual(result["effective_leakage"], 1)
            self.assertAlmostEqual(result["cost"], 1 / entropy + case["latency"] * result["rounds"])


class ContractTests(unittest.TestCase):
    def test_invalid_policies(self):
        candidates = []
        for field, value in [("max_passes", True), ("max_passes", 21), ("version", 2), ("rules", [{}])]:
            policy = baseline_policy()
            policy[field] = value
            candidates.append(policy)
        for value in [float("nan"), float("inf"), 0, True]:
            policy = baseline_policy()
            policy["schedule"][0]["size"]["scale"] = value
            candidates.append(policy)
        policy = baseline_policy()
        policy["rules"] = [{"when": [["residual_bits", "gt", 0]], "action": {"stop": True}}]
        candidates.append(policy)
        policy = baseline_policy()
        policy["python"] = "raise SystemExit"
        candidates.append(policy)
        for policy in candidates:
            with self.assertRaises(ValueError):
                validate_policy(policy)

    def test_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text('{"version":1,"version":1}')
            with self.assertRaises(ValueError):
                load_policy(path)

    def test_first_matching_rule(self):
        policy = baseline_policy()
        policy["rules"] = [{"when": [["latency", "gt", 0]], "action": {"batch": "smallest"}},
                           {"when": [["latency", "gt", 0]], "action": {"reuse": "roots"}}]
        action = choose_action(policy, {"latency": 0.1, "pass_index": 1})
        self.assertEqual(action["batch"], "smallest")
        self.assertEqual(action["reuse"], "all")

    def test_split_independence(self):
        previous_seeds = set()
        previous_tuples = set()
        for relative in ["participant/inputs/train.json", "participant/inputs/dev.json", "evaluator/hidden/cases.json"]:
            suite = json.loads((ROOT / relative).read_text())
            seeds = []
            configurations = set()
            for case in suite["cases"]:
                configurations.add(tuple(case[field] for field in ["frame_bits", "q_true", "estimate_bias", "sample_size", "latency"]))
                seeds.extend(case["frame_seeds"])
            for case in suite["stress"]:
                seeds.extend(case["frame_seeds"])
            self.assertEqual(len(seeds), len(set(seeds)))
            self.assertFalse(set(seeds) & previous_seeds)
            self.assertFalse(configurations & previous_tuples)
            previous_seeds.update(seeds)
            previous_tuples.update(configurations)

    def test_stress_reaches_third_pass(self):
        suite = json.loads((ROOT / "participant/inputs/train.json").read_text())
        for case in suite["stress"]:
            for frame_seed, errors in zip(case["frame_seeds"][:3], case["errors"][:3]):
                result = run_frame(case, frame_seed, baseline_policy(), errors=errors, trace=True)
                self.assertEqual(result["trace"][0]["corrected"], 0)
                self.assertEqual(result["trace"][1]["corrected"], 0)

    def test_confidence_interval(self):
        self.assertGreater(wilson_upper(0, 64), 0.01)
        self.assertLess(wilson_upper(0, 1024), 0.01)

    def test_structured_invalid_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            candidate = directory / "policy.json"
            output = directory / "report.json"
            invalid_inputs = ["{broken", '{"version":NaN}', " " * 65537, '[]', '{"version":1,"version":1}']
            for contents in invalid_inputs:
                candidate.write_text(contents)
                completed = subprocess.run([sys.executable, "-I", str(ROOT / "evaluator/evaluate.py"),
                                            "--policy", str(candidate), "--output", str(output)],
                                           capture_output=True, text=True, check=True)
                result = json.loads(output.read_text())
                self.assertFalse(result["valid"])
                self.assertFalse(result["passed"])
                self.assertTrue(result["reason"])
                self.assertNotIn("Traceback", completed.stderr)
                for field in ["core_score", "worst_family_score", "runtime_resource_score"]:
                    self.assertTrue(math.isfinite(result[field]))
            for arguments in [[], ["--policy", str(directory / "missing.json")]]:
                completed = subprocess.run([sys.executable, "-I", str(ROOT / "evaluator/evaluate.py"),
                                            "--output", str(output), *arguments],
                                           capture_output=True, text=True, check=True)
                self.assertFalse(json.loads(output.read_text())["valid"])
                self.assertNotIn("Traceback", completed.stderr)

    def test_required_public_directories(self):
        for name in ["input", "workspace", "baseline"]:
            self.assertTrue((ROOT / "participant" / name).is_dir())
        for name in ["train.json", "dev.json", "distribution.json"]:
            self.assertEqual((ROOT / "participant/input" / name).read_bytes(),
                             (ROOT / "participant/inputs" / name).read_bytes())
        self.assertEqual(json.loads((ROOT / "participant/baseline/policy.json").read_text()), baseline_policy())

    def test_frozen_manifest(self):
        import hashlib
        manifest = json.loads((ROOT / "evaluator/frozen.json").read_text())
        for relative, digest in manifest["sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest)

    def test_read_only_safe_baseline_entrypoint(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "policy.json"
            subprocess.run([sys.executable, "-I", str(ROOT / "participant/baseline/run.py"),
                            "--output", str(destination)], check=True, cwd=directory)
            self.assertEqual(load_policy(destination), baseline_policy())


if __name__ == "__main__":
    unittest.main(verbosity=2)
