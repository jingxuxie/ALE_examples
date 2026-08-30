import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import evaluate
from resources import CpuTreeMonitor


@unittest.skipUnless(os.environ.get("LDOS_SANDBOX_TESTS") == "1", "requires escalated outer bubblewrap execution")
class ResourceTests(unittest.TestCase):
    records = []

    @classmethod
    def setUpClass(cls):
        case = {"id": "resource-control", "family": "dispersed",
                "scene": evaluate.model.draw_scene(71, "dispersed")}
        result = evaluate.run_episode(case, evaluate.ROOT / "participant",
                                      evaluate.ROOT / "evaluator" / "resource_clients",
                                      "control.py", cpu_seconds=2, wall_seconds=8)
        if not result["protocol_valid"] or not result["resource_accounting"]["complete"]:
            raise AssertionError(result)
        cls.records = [result]
        cls.control_overhead = result["cpu_seconds"] - json.loads(result["stderr"])["client_accounted_cpu"]

    @classmethod
    def tearDownClass(cls):
        destination = os.environ.get("LDOS_RESOURCE_REPORT")
        if destination:
            Path(destination).write_text(json.dumps({"episodes": cls.records}, indent=2) + "\n")

    def run_entry(self, entry, cpu=90, wall=8):
        case = {"id": "resource-" + entry, "family": "dispersed",
                "scene": evaluate.model.draw_scene(71, "dispersed")}
        result = evaluate.run_episode(case, evaluate.ROOT / "participant",
                                      evaluate.ROOT / "evaluator" / "resource_clients",
                                      entry + ".py", cpu_seconds=cpu, wall_seconds=wall)
        self.records.append(result)
        return result

    def evidence(self, result):
        return [json.loads(line) for line in result["stderr"].splitlines()]

    def assert_complete(self, result):
        self.assertTrue(result["protocol_valid"], result.get("error", result.get("stderr")))
        accounting = result["resource_accounting"]
        self.assertTrue(accounting["complete"])
        self.assertEqual(result["cpu_seconds"], accounting["final_wait4_cpu_seconds"])
        evidence = self.evidence(result)
        client_cpu = sum(item.get("client_accounted_cpu", 0) + item.get("orphan_cpu", 0) for item in evidence)
        self.assertGreaterEqual(result["cpu_seconds"], client_cpu - 0.002)
        self.assertLessEqual(result["cpu_seconds"], result["wall_seconds"] + 0.02)
        self.assertLessEqual(accounting["confirmed_tree_cpu_seconds"], result["cpu_seconds"] + 0.02)
        self.assertEqual(evidence[-1].get("affinity_count", evidence[0].get("affinity_count")), 1)

    def test_busy_cpu_limit(self):
        result = self.run_entry("busy", cpu=0.60)
        self.assertFalse(result["protocol_valid"])
        self.assertIn("CPU", result["error"])
        self.assertTrue(result["resource_accounting"]["cpu_limit_exceeded"])
        self.assertGreaterEqual(result["cpu_seconds"], 0.60)
        self.assertLess(result["cpu_seconds"], 0.85)
        self.assertLess(result["wall_seconds"], 5)

    def test_forked_aggregate_cpu_limit(self):
        result = self.run_entry("forked", cpu=0.80)
        self.assertFalse(result["protocol_valid"])
        self.assertIn("CPU", result["error"])
        self.assertTrue(result["resource_accounting"]["cpu_limit_exceeded"])
        self.assertGreaterEqual(result["cpu_seconds"], 0.80)
        self.assertLess(result["cpu_seconds"], 1.10)
        self.assertGreaterEqual(result["resource_accounting"]["max_live_processes"], 7)

    def test_rapid_reaped_children_no_double_count(self):
        result = self.run_entry("rapid", cpu=2)
        self.assert_complete(result)
        self.assertGreaterEqual(result["cpu_seconds"], 0.24)

    def test_orphan_grandchild_is_reaped(self):
        result = self.run_entry("orphan", cpu=2)
        self.assert_complete(result)
        self.assertTrue(any(item.get("orphan_cpu", 0) >= 0.30 for item in self.evidence(result)))

    def test_children_forked_by_nonleader_thread(self):
        result = self.run_entry("threaded", cpu=2)
        self.assert_complete(result)
        self.assertGreaterEqual(result["resource_accounting"]["max_live_processes"], 4)

    def test_known_numpy_cpu_and_strict_production_rlimit(self):
        result = self.run_entry("numpy_work")
        self.assert_complete(result)
        evidence = self.evidence(result)[0]
        self.assertGreater(evidence["numpy_eigendecompositions"], 0)
        self.assertGreaterEqual(result["cpu_seconds"], 0.40)
        self.assertEqual(evidence["rlimit_cpu"], [90, 90])

    def test_autoreap_and_affinity_escape_blocked(self):
        result = self.run_entry("restrictions")
        self.assert_complete(result)
        evidence = self.evidence(result)[0]
        for name in ("sigchld_autoreap_denied", "affinity_change_denied", "cpu_hard_limit_increase_denied"):
            self.assertTrue(evidence.get(name), name)

    def test_wall_limit_is_separate(self):
        result = self.run_entry("sleep", cpu=2, wall=0.5)
        self.assertFalse(result["protocol_valid"])
        self.assertIn("wall", result["error"])
        self.assertLess(result["cpu_seconds"], 2)
        self.assertLessEqual(result["cpu_seconds"], result["wall_seconds"] + 0.02)
        self.assertFalse(result["resource_accounting"]["cpu_limit_exceeded"])

    def test_final_wait4_enforces_budget_after_missed_samples(self):
        with patch("resources.SAMPLE_INTERVAL", 1000):
            result = self.run_entry("rapid", cpu=0.70)
        self.assertFalse(result["protocol_valid"])
        self.assertIn("CPU", result["error"])
        self.assertGreater(result["resource_accounting"]["final_wait4_cpu_seconds"], 0.70)
        self.assertTrue(result["resource_accounting"]["cpu_limit_exceeded"])
        self.assertLessEqual(result["resource_accounting"]["samples"], 1)

    def test_no_unsandboxed_launch_fallback(self):
        with patch("resources.subprocess.Popen", side_effect=OSError("sandbox unavailable")) as launch:
            with self.assertRaisesRegex(OSError, "sandbox unavailable"):
                self.run_entry("control")
        self.assertEqual(launch.call_count, 1)
        self.assertEqual(launch.call_args.args[0][0], "bwrap")

    def test_normal_subprocess_compilation_remains_usable(self):
        result = self.run_entry("compile_work", cpu=4)
        self.assert_complete(result)
        self.assertTrue(self.evidence(result)[0]["compiled_in_writable_scratch"])

    def test_reaped_cpu_transfer_is_not_accumulated_twice(self):
        process = SimpleNamespace(poll=lambda: None, returncode=0,
                                  pid=10, usage=SimpleNamespace(ru_utime=0.41, ru_stime=0.005))
        monitor = CpuTreeMonitor(process, 2)
        before = {10: {"ticks": 1}, 20: {"ticks": 40}}
        after = {10: {"ticks": 41}}
        with patch("resources.tree_snapshot", side_effect=[before, after]):
            monitor.check(force=True)
            monitor.check(force=True)
        self.assertAlmostEqual(monitor.last_sample, 0.41)
        self.assertAlmostEqual(monitor.peak_sample, 0.41)
        self.assertAlmostEqual(monitor.report(True)["cpu_seconds"], 0.415)


if __name__ == "__main__":
    unittest.main()
