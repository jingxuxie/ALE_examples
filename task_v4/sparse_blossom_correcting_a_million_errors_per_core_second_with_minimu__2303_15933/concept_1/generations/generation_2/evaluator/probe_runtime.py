import json
import os

from evaluate import ROOT, PARTICIPANT
from qualify import execute


def main():
    os.environ["ALE_HIDDEN_CANARY"] = "must_not_reach_worker"
    reports = {}
    for name, path in [
        ("baseline", PARTICIPANT / "baseline/submission.py"),
        ("isolation", ROOT / "adversary/isolation_probe/submission.py"),
        ("cpu_burn", ROOT / "adversary/cpu_probe/submission.py"),
    ]:
        reports[name] = execute(path, shots=2, cpu_seconds=20)
        print(json.dumps(dict(probe=name, **reports[name])), flush=True)
    increment = reports["cpu_burn"]["execution"]["cpu_seconds"] - reports["baseline"]["execution"]["cpu_seconds"]
    result = dict(all_passed=all(report["valid"] and report["baseline_equal"] for report in reports.values()) and increment >= 1.7,
        measured_cpu_burn_increment=increment, reports=reports, fresh_runner_launched=False)
    (ROOT / "evaluator/hidden/runtime_probe.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
