import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CHANGED = ("evaluator/sandbox_runner.py", "evaluator/worker.py")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    original_path = HERE / "original/calibration.json"
    current_path = ROOT / "evaluator/hidden/calibration.json"
    original = json.loads(original_path.read_text())
    if digest(current_path) != digest(original_path):
        raise ValueError("calibration changed before infrastructure revision")
    validation = json.loads((HERE / "validation.json").read_text())
    security = json.loads((ROOT / "adversary/runner_validation.json").read_text())
    if validation["passed"] != 4 or validation["failed"] or security["passed"] != 6 or security["failed"]:
        raise ValueError("resource regression checks have not passed")
    updated = copy.deepcopy(original)
    changes = {}
    for relative, expected in original["frozen_hashes"].items():
        actual = digest(ROOT / relative)
        if relative in CHANGED:
            if digest(HERE / "original" / Path(relative).name) != expected:
                raise ValueError("original infrastructure archive mismatch")
            changes[relative] = {"before": expected, "after": actual}
            updated["frozen_hashes"][relative] = actual
        elif actual != expected:
            raise ValueError("unapproved frozen asset change: " + relative)
    updated["infrastructure_revision"] = 2
    updated["infrastructure_change"] = "Enforce and score wall time in protected direct-child supervisor; exclude trusted bubblewrap startup. CPU, physical cases, reference states, targets and participant are unchanged."
    current_path.write_text(json.dumps(updated, indent=2, allow_nan=False) + "\n")
    manifest = {
        "revision": 2,
        "kind": "scoring infrastructure correction, not a scientific ratchet",
        "original_calibration_sha256": digest(original_path),
        "corrected_calibration_sha256": digest(current_path),
        "changed_sources": changes,
        "participant_unchanged": True,
        "physical_cases_unchanged": updated["cases"] == original["cases"],
        "target_unchanged": updated["target_frozen_before_launch"] == original["target_frozen_before_launch"],
        "resource_regressions_passed": validation["passed"] + security["passed"],
        "raw_fresh_reports_preserved": ["attempts/v_1_audit/evaluation.json", "attempts/v_2_audit/evaluation.json"],
        "raw_wall_failures_are_hardness_evidence": False,
        "regrade_requires_unchanged_submissions": True,
    }
    (HERE / "freeze_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
