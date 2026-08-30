import json
from pathlib import Path
import sys
import unittest

from evaluate import ROOT, HIDDEN, run_case
from independent import checked_field, energy_gradient, read_case


class SandboxTests(unittest.TestCase):
    def test_baseline_through_real_helper(self):
        case_id = "h01"
        case = read_case(HIDDEN / "cases" / (case_id + ".json"))
        field = checked_field(ROOT / "attempts/baseline" / (case_id + ".npz"), case)
        baseline = energy_gradient(case, field)[0]
        reference = {"case_id": case_id, "family": "strong_pinning", "case_path": "evaluator/hidden/cases/h01.json", "baseline_energy": baseline, "witness_energy": baseline - 10}
        target = read_case(HIDDEN / "target.json")
        record = run_case(ROOT / "participant/workspace", reference, target)
        (ROOT / "attempts/sandbox_smoke.json").write_text(json.dumps(record, indent=2) + "\n")
        self.assertTrue(record["valid"], record)
        self.assertLess(record["wall_seconds"], 60)
        self.assertAlmostEqual(record["checked_energy"], baseline, delta=1e-8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
