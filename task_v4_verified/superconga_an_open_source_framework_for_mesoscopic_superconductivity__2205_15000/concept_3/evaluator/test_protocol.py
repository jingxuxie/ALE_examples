import os
import unittest

import evaluate


@unittest.skipUnless(os.environ.get("LDOS_SANDBOX_TESTS") == "1", "requires escalated outer bubblewrap execution")
class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.case = {"id": "public-probe", "family": "dispersed", "scene": evaluate.model.draw_scene(71, "dispersed")}

    def run_entry(self, entry, wall=10):
        return evaluate.run_episode(self.case, evaluate.ROOT / "participant", evaluate.ROOT / "adversary", entry, wall_seconds=wall)

    def test_mounts_metadata_and_freshness(self):
        for _ in range(2):
            result = self.run_entry("probe.py")
            self.assertTrue(result["protocol_valid"], result.get("error"))
            self.assertEqual(result["metrics"]["joint_success"], 1)
            self.assertEqual(result["queries"], 1)
            self.assertIn('"scratch_ok": true', result["stderr"])
            self.assertIn('"public_metadata_only": true', result["stderr"])

    def test_rejects_invalid_and_unbounded_clients(self):
        for entry in ("overflow.py", "nan.py", "duplicate.py", "extra.py", "oversized.py", "stderr.py", "invalid.py", "eof.py", "nonzero.py"):
            with self.subTest(entry=entry):
                result = self.run_entry(entry)
                self.assertFalse(result["protocol_valid"])
                self.assertEqual(result["metrics"]["joint_success"], 0)
                if entry == "overflow.py":
                    self.assertEqual(result["queries"], 56)
                    self.assertIn("budget", result["error"])

    def test_wall_timeout(self):
        for entry in ("stall.py", "unread.py"):
            result = self.run_entry(entry, wall=0.4)
            self.assertFalse(result["protocol_valid"])
            self.assertLess(result["wall_seconds"], 3)


if __name__ == "__main__":
    unittest.main()
