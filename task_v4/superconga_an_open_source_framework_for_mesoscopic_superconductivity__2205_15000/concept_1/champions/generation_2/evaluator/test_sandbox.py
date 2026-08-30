import json
from pathlib import Path
import sys
import unittest

from evaluate import ROOT, HIDDEN, LimitedSandbox, load_references, run_case
from independent import checked_field, energy_gradient, read_case


class SandboxTests(unittest.TestCase):
    def test_baseline_through_real_helper(self):
        target, references = load_references()
        reference = references[0]
        baseline = reference["baseline_energy"]
        record = run_case(ROOT / "participant/workspace", reference, target)
        (ROOT / "attempts/sandbox_smoke.json").write_text(json.dumps(record, indent=2) + "\n")
        self.assertTrue(record["valid"], record)
        self.assertLess(record["wall_seconds"], 60)
        self.assertAlmostEqual(record["checked_energy"], baseline, delta=1e-8)

    def test_cpu_affinity_cannot_be_changed(self):
        script = "import os\nassert len(os.sched_getaffinity(0)) == 1\ntry:\n os.sched_setaffinity(0,os.sched_getaffinity(0))\nexcept PermissionError:\n print('blocked')\nelse:\n raise RuntimeError('affinity can be changed')"
        with LimitedSandbox(ROOT / "participant", ROOT / "participant" / "baseline", seconds=5, memory_gib=2) as sandbox:
            result = sandbox.run(["/usr/bin/python3", "-c", script])
        self.assertEqual(result["returncode"], 0, result)
        self.assertIn("blocked", result["stdout"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
