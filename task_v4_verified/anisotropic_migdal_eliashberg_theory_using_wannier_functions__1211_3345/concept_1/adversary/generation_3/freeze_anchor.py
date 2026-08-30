"""Fix the mode-A anchor to the measured, original public baseline only."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


PENDING = Path(__file__).resolve().parent
PACKAGE = PENDING / "package" / "concept_1"


def main():
    hidden = PACKAGE / "evaluator" / "hidden"
    report_path = PACKAGE / "attempts" / "baseline_report.json"
    report = json.loads(report_path.read_text())
    policy_path = hidden / "policy.json"
    policy = json.loads(policy_path.read_text())
    selection = json.loads((PENDING / "selection.json").read_text())
    target = selection["target_fixed_before_next_fresh_launch"]
    assert policy["overall_target"] == target["core_score_min"]
    assert policy["worst_family_target"] == target["worst_family_score_min"]
    assert policy["improvement_target"] == target["worst_family_improvement_over_public_baseline_min"]
    assert report["complete_suite"] and len(report["cases"]) == 20
    assert report["score"] + policy["improvement_target"] <= 1
    assert report["policy_sha256"] == hashlib.sha256(policy_path.read_bytes()).hexdigest()
    baseline = PACKAGE / "participant" / "baseline" / "solve.py"
    original = PENDING.parents[1] / "participant" / "baseline" / "solve.py"
    assert baseline.read_bytes() == original.read_bytes()
    anchor = {
        "score": report["score"], "worst_family_score": report["worst_family_score"],
        "core_score": report["core_score"], "overall": report["overall"],
        "family_rates": report["family_rates"],
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "baseline_identity": "original_public_damped_fixed_point_solver",
        "baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
        "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "policy_sha256": report["policy_sha256"],
        "prior_fresh_code_is_public": False,
    }
    public = dict(anchor, target_worst_family=policy["worst_family_target"],
                  target_overall=policy["overall_target"],
                  target_improvement=policy["improvement_target"],
                  resources=report["resources"], runtime=report["runtime"])
    patch = "*** Begin Patch\n"
    for path, contents in ((hidden / "baseline_anchor.json", anchor),
                           (PACKAGE / "participant" / "input" / "baseline_result.json", public)):
        if path.exists():
            raise FileExistsError("anchor is already frozen")
        patch += "*** Add File: " + str(path) + "\n"
        patch += "".join("+" + line + "\n" for line in json.dumps(contents, indent=2).splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True)
    print(json.dumps(anchor))


if __name__ == "__main__":
    main()
