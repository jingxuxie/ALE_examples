import json
import os

from evaluate import ROOT, PARTICIPANT, evaluate
from qualify import execute


def save(name, report):
    (ROOT / "attempts" / (name + ".json")).write_text(json.dumps(report, indent=2) + "\n")


def main():
    os.environ["ALE_HIDDEN_CANARY"] = "must_not_reach_worker"
    checks = []
    baseline = evaluate(PARTICIPANT / "baseline/submission.py", "both")
    save("baseline_isolated", baseline)
    checks.append(dict(name="frozen_baseline", passed=baseline.get("valid") is True and baseline.get("passed") is False
        and baseline.get("status") == "FAIL" and baseline.get("core_score") == 0 and baseline["gates"]["runtime"]))
    zero = evaluate(ROOT / "adversary/zero_probe/submission.py", "both")
    save("zero_full", zero)
    checks.append(dict(name="valid_nonpassing_distinct_from_invalid", passed=zero.get("valid") is True and zero.get("passed") is False and zero.get("status") == "FAIL"))
    reports = {}
    for name, path, expected_valid in [
        ("short_baseline", PARTICIPANT / "baseline/submission.py", True),
        ("isolation_probe", ROOT / "adversary/isolation_probe/submission.py", True),
        ("cpu_probe", ROOT / "adversary/cpu_probe/submission.py", True),
        ("invalid_probe", ROOT / "adversary/invalid_probe/submission.py", False),
    ]:
        report = execute(path, shots=2, cpu_seconds=20)
        reports[name] = report
        save(name, report)
        passed = report["valid"] == expected_valid and (not expected_valid or report["baseline_equal"])
        checks.append(dict(name=name, passed=passed, cpu_seconds=report["execution"]["cpu_seconds"]))
        print(json.dumps(checks[-1]), flush=True)
    increment = reports["cpu_probe"]["execution"]["cpu_seconds"] - reports["short_baseline"]["execution"]["cpu_seconds"]
    checks.append(dict(name="trusted_cpu_burn_increment", passed=increment >= 1.7, measured_increment_seconds=increment))
    result = dict(all_passed=all(check["passed"] for check in checks), checks=checks, fresh_runner_launched=False,
        cpu_accounting="Trusted parent wait4; bwrap --as-pid-1; seccomp prohibits descendants; CPU-burn probe checked")
    save("validation_summary", result)
    print(json.dumps(result, indent=2))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
