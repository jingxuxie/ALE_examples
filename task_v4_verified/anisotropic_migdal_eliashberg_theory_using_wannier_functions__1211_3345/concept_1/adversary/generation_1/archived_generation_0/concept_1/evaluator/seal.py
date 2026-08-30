"""One-shot privileged prelaunch seal; no candidate execution or imports."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HIDDEN = ROOT / "evaluator" / "hidden"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    policy_path = HIDDEN / "policy.json"
    policy = json.loads(policy_path.read_text())
    report_path = ROOT / "attempts" / "baseline_report.json"
    report = json.loads(report_path.read_text())
    if not report["complete_suite"] or report["policy_sha256"] != digest(policy_path):
        raise ValueError("cannot seal incomplete or different-policy baseline")
    if not 0 <= report["score"] <= 1 - policy["improvement_target"]:
        raise ValueError("unattainable baseline improvement target")
    manifest = json.loads((HIDDEN / "manifest.json").read_text())
    records = manifest["cases"]
    for family in policy["families"]:
        if sum(record["family"] == family for record in records) != policy["cases_per_family"]:
            raise ValueError("incorrect family coverage")
    for record in records:
        case_id = record["case_id"]
        certificate = json.loads((HIDDEN / "references" / (case_id + ".json")).read_text())
        if not certificate["valid"] or certificate["instance_sha256"] != digest(HIDDEN / "cases" / (case_id + ".npz")):
            raise ValueError("uncertified or changed case: " + case_id)
    timestamp = datetime.now(timezone.utc).isoformat()
    anchor = {"score": report["score"], "core_score": report["overall"],
              "family_rates": report["family_rates"], "sealed_at": timestamp,
              "report_sha256": digest(report_path), "policy_sha256": digest(policy_path)}
    with (HIDDEN / "baseline_anchor.json").open("x") as output:
        output.write(json.dumps(anchor, indent=2) + "\n")
    public = dict(anchor, worst_family_score=report["score"], overall=report["overall"],
                  target_worst_family=policy["worst_family_target"], target_overall=policy["overall_target"],
                  target_improvement=policy["improvement_target"])
    (ROOT / "participant" / "input" / "baseline_result.json").write_text(json.dumps(public, indent=2) + "\n")
    paths = [ROOT / "TASK.md", ROOT / "participant" / "baseline" / "solve.py",
             ROOT / "participant" / "input" / "FORMAT.md", ROOT / "participant" / "input" / "eliashberg.py",
             ROOT / "participant" / "input" / "baseline_result.json", ROOT / "evaluator" / "evaluate.py",
             ROOT / "evaluator" / "launch.py", HIDDEN / "physics.py", policy_path,
             HIDDEN / "manifest.json", HIDDEN / "baseline_anchor.json"]
    paths += sorted((HIDDEN / "cases").glob("*.npz"))
    paths += sorted((HIDDEN / "references").glob("*.*"))
    seal = {"sealed_at": timestamp, "fresh_agent_launched_by_builder": False,
            "policy_sha256": digest(policy_path), "baseline_report_sha256": digest(report_path),
            "files": {str(path.relative_to(ROOT)): digest(path) for path in paths}}
    with (HIDDEN / "prelaunch_seal.json").open("x") as output:
        output.write(json.dumps(seal, indent=2) + "\n")
    print(json.dumps({"ready": True, "baseline_score": report["score"], "core_score": report["overall"],
                      "policy_sha256": digest(policy_path), "sealed_files": len(paths), "sealed_at": timestamp}))


if __name__ == "__main__":
    main()
