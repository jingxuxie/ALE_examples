import itertools
import json
import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant" / "input"))
sys.path.insert(0, str(ROOT / "evaluator"))
from simulator import CONTRACT, Device, ProtocolError, anchor_mask, component_edges
from evaluate import PolicyFailure, PolicyProcess, evaluate, hidden_cases, run_case, sandbox_command


class ModelTests(unittest.TestCase):
    def test_matched_graph_invariants_and_distinct_motifs(self):
        clique_counts = {}
        for kind in ("R", "S"):
            edges = set(component_edges(kind))
            self.assertEqual(len(edges), 48)
            neighbors = [{other for other in range(16) if tuple(sorted((site, other))) in edges}
                         for site in range(16)]
            self.assertTrue(all(len(adjacent) == 6 for adjacent in neighbors))
            for first, second in itertools.combinations(range(16), 2):
                self.assertEqual(len(neighbors[first] & neighbors[second]), 2)
            clique_counts[kind] = sum(
                all(tuple(sorted(pair)) in edges for pair in itertools.combinations(vertices, 2))
                for vertices in itertools.combinations(range(16), 4)
            )
        self.assertEqual(clique_counts, {"R": 8, "S": 0})

    def test_parity_invisibility_and_echo_decoding(self):
        for family in CONTRACT["families"]:
            for denominator in CONTRACT["contamination_denominators"]:
                device = Device(family, denominator, 137)
                for source in range(32):
                    device.handle({"op": "start", "source": source})
                    self.assertEqual(device.residual.bit_count(), 4)
                    active = [site for site in range(32) if (device.residual >> (8 * site)) & 255]
                    self.assertEqual(len(active), 2)
                    self.assertIn(source, active)
                    for site in range(32):
                        self.assertEqual(((device.residual >> (8 * site)) & 255).bit_count() % 2, 0)
                    echo = 0
                    for coordinate in range(5):
                        mask = anchor_mask(site for site in range(32) if (site >> coordinate) & 1)
                        reply = device.handle({"op": "parity", "mask": format(mask, "x")})
                        echo |= (reply["value"] ^ ((source >> coordinate) & 1)) << coordinate
                    self.assertEqual(set(active), {source, echo})

    def test_reproducible_public_simulator(self):
        first = Device("RS", 32, 1234)
        second = Device("RS", 32, 1234)
        for source in range(12):
            request = {"op": "start", "source": source}
            self.assertEqual(first.handle(request), second.handle(request))
            self.assertEqual(first.residual, second.residual)

    def test_invalid_operations_and_budgets(self):
        device = Device("RR", 0, 17)
        for request in ({"op": "start", "source": True}, {"op": "parity", "mask": "1"},
                        {"op": "guess", "family": []}, {"op": "unknown"}):
            with self.assertRaises(ProtocolError):
                device.handle(request)
        device.handle({"op": "start", "source": 0})
        with self.assertRaises(ProtocolError):
            device.handle({"op": "parity", "mask": "f" * 64})
        for query_index in range(8):
            device.handle({"op": "parity", "mask": "0"})
        with self.assertRaises(ProtocolError):
            device.handle({"op": "parity", "mask": "0"})
        device.queries = CONTRACT["parity_queries"]
        device.frame_queries = 0
        with self.assertRaises(ProtocolError):
            device.handle({"op": "parity", "mask": "0"})
        device.frames = CONTRACT["frames"]
        with self.assertRaises(ProtocolError):
            device.handle({"op": "start", "source": 0})

    def test_frozen_suite(self):
        cases = hidden_cases()
        self.assertEqual(len(cases), 180)
        self.assertEqual(len({case["seed"] for case in cases}), 180)
        self.assertEqual(CONTRACT["target_total_correct"], 171)
        self.assertEqual(CONTRACT["target_cell_correct"], 18)


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.case = {"family": "SS", "contamination_denominator": 0, "seed": 123}

    def test_mount_allowlist(self):
        command = sandbox_command(ROOT / "participant" / "baseline" / "policy.py")
        self.assertNotIn("--proc", command)
        self.assertNotIn("--share-net", command)
        self.assertIn("--unshare-pid", command)
        self.assertIn("--unshare-net", command)
        self.assertNotIn(str(ROOT / "evaluator"), command)

    def test_private_paths_environment_and_imports(self):
        os.environ["ALE_PRIVATE_ISOLATION_SENTINEL"] = "never expose this"
        try:
            result = run_case(ROOT / "adversary" / "isolation_probe.py", self.case)
        finally:
            del os.environ["ALE_PRIVATE_ISOLATION_SENTINEL"]
        self.assertIsNone(result["failure"], result)
        self.assertTrue(result["correct"])

    def test_oversized_line_fails(self):
        result = run_case(ROOT / "adversary" / "oversized_policy.py", self.case)
        self.assertEqual(result["failure"], "oversized protocol line")

    def test_wall_deadline(self):
        result = run_case(ROOT / "adversary" / "idle_policy.py", self.case, wall_seconds=0.5)
        self.assertEqual(result["failure"], "wall time exceeded")

    def test_blocked_input_deadline(self):
        with PolicyProcess(ROOT / "adversary" / "idle_policy.py", wall_seconds=0.3) as process:
            with self.assertRaisesRegex(PolicyFailure, "wall time exceeded"):
                process.send({"padding": "x" * 1048576})

    def test_missing_policy(self):
        report = evaluate(ROOT / "adversary" / "missing.py", [self.case], "hidden")
        self.assertFalse(report["passed"])
        self.assertFalse(report["valid"])

    def test_development_cannot_pass_hidden_target(self):
        report = evaluate(ROOT / "adversary" / "isolation_probe.py", [self.case], "development")
        self.assertEqual(report["accuracy"], 1.0, report)
        self.assertFalse(report["target_passed"])


if __name__ == "__main__":
    unittest.main()
