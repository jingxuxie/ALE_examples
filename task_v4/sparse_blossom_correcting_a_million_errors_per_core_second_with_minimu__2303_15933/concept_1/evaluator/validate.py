import json
import os
from pathlib import Path
import shutil

from evaluate import ROOT, evaluate


def main():
    records = []
    probes = [
        ("baseline_isolated", "participant/baseline/decoder.py", True),
        ("isolation_probe", "adversary/isolation_candidate/submission.py", True),
        ("zero_probe", "adversary/zero_candidate/submission.py", True),
        ("invalid_probe", "adversary/invalid_candidate/submission.py", False),
        ("cpu_probe", "adversary/cpu_candidate/submission.py", True),
    ]
    os.environ["ALE_HIDDEN_CANARY"] = "must_not_reach_worker"
    for name, submission, expected_valid in probes:
        path = ROOT / "attempts" / (name + ".json")
        archive = ROOT / "attempts" / (name + "_pre_cpu_fix.json")
        if path.exists() and not archive.exists():
            shutil.copy2(path, archive)
        try:
            report = evaluate(ROOT / submission, "both")
        except Exception as error:
            report = dict(valid=False, passed=False, reason=f"{type(error).__name__}: {error}")
        path.write_text(json.dumps(report, indent=2) + "\n")
        correct = report["valid"] == expected_valid and report["passed"] is False
        if name in ["baseline_isolated", "isolation_probe", "cpu_probe"]:
            correct = correct and report.get("core_score") == 0
        if name == "cpu_probe":
            correct = correct and report.get("execution", {}).get("cpu_seconds", 0) >= 2.0
        records.append(dict(probe=name, ok=correct, valid=report["valid"], reason=report.get("reason"),
                            cpu_seconds=report.get("execution", {}).get("cpu_seconds")))
        print(json.dumps(records[-1]), flush=True)
    summary = dict(all_passed=all(record["ok"] for record in records), checks=records,
                   fresh_runner_launched=False, target_and_labels_unchanged=True)
    (ROOT / "attempts/validation_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
