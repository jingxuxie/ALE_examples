import argparse
import hashlib
import json
from pathlib import Path
import time

from reproduce import reproduce

ROOT = Path(__file__).resolve().parents[1]


def evaluate(submission):
    started = time.monotonic()
    report = {"core_score": 0.0, "worst_family_score": 0.0, "runtime_resource_score": 0.0, "valid": False, "passed": False}
    try:
        artifact = Path(submission)
        if artifact.is_dir():
            artifact = artifact / "witness.json"
        if artifact.is_symlink() or not artifact.is_file() or artifact.stat().st_size > 65536:
            raise ValueError("missing, symlinked or oversized witness.json")
        value = json.loads(artifact.read_text())
        if not isinstance(value, dict) or set(value) != {"errors"}:
            raise ValueError("witness must have exactly the errors field")
        errors = value["errors"]
        if not isinstance(errors, list) or not 1 <= len(errors) <= 24:
            raise ValueError("require 1 to 24 errors")
        deployment_path = ROOT / "participant/input/deployment.json"
        expected = json.loads((ROOT / "evaluator/hidden/manifest.json").read_text())
        if hashlib.sha256(deployment_path.read_bytes()).hexdigest() != expected["deployment_sha256"]:
            raise ValueError("deployment integrity failure")
        deployment = json.loads(deployment_path.read_text())
        if any(type(position) is not int or not 0 <= position < deployment["n"] for position in errors) or len(set(errors)) != len(errors):
            raise ValueError("invalid discrepancy indices")
        families = {}
        for priority in ("earliest", "shortest"):
            result = reproduce(deployment, errors, priority)
            result["passed"] = result["initial_odd"] >= 6 and len(result["corrected"]) >= 6 and len(result["residual"]) >= 8
            result["score"] = min(1.0, len(result["residual"]) / 8.0) * min(1.0, len(result["corrected"]) / 6.0) * min(1.0, result["initial_odd"] / 6.0)
            families[priority] = result
        report.update(valid=True, families=families, error_weight=len(errors), core_score=sum(result["score"] for result in families.values()) / 2, worst_family_score=min(result["score"] for result in families.values()), passed=all(result["passed"] for result in families.values()), runtime_resource_score=1.0)
        report["reason"] = "valid activated residual counterexample" if report["passed"] else "valid input, but activated residual witness conditions not met"
    except (ValueError, TypeError, KeyError, OSError, AssertionError) as exception:
        report["reason"] = str(exception)
    report["runtime_seconds"] = time.monotonic() - started
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--report")
    arguments = parser.parse_args()
    report = evaluate(arguments.submission)
    text = json.dumps(report, indent=2) + "\n"
    if arguments.report:
        Path(arguments.report).write_text(text)
    print(text, end="")
