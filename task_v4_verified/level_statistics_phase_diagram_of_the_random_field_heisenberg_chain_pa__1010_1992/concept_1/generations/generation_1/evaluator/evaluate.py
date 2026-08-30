import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

from sandbox import run_submission


ROOT = Path(__file__).resolve().parents[1]


class EvaluatorInfrastructureError(RuntimeError):
    pass


class SubmissionEvaluationError(RuntimeError):
    pass


def infrastructure_failure(error):
    if isinstance(error, OSError):
        return True
    text = str(error).lower()
    return any(marker in text for marker in (
        "bwrap:", "libseccomp", "cannot initialize resource filter",
        "cannot create cpu-affinity filter", "cannot export cpu-affinity filter",
        "taskset: failed", "failed to create namespace"))


def failure_report(error):
    infrastructure = isinstance(error, EvaluatorInfrastructureError)
    detail = str(error)
    timing = None
    limit_failure = False
    try:
        diagnostic = json.loads(detail)
        if isinstance(diagnostic, dict):
            timing = diagnostic.get("seconds") if diagnostic.get("phase") != "startup" else None
            limit_failure = bool(diagnostic.get("timeout"))
    except (ValueError, TypeError):
        pass
    reason = "infrastructure_error" if infrastructure else "submission_error"
    if limit_failure and not infrastructure:
        reason = "submission_resource_limit"
    return {"passed": False, "mode": "D HIDDEN PREDICTION",
            "core_score": None, "worst_family_score": None,
            "valid": False, "evaluator_valid": not infrastructure,
            "resource_score": None if infrastructure else 0.0,
            "runtime_seconds": timing, "reason": reason,
            "error_category": "infrastructure" if infrastructure else "submission",
            "error": type(error).__name__, "detail": detail,
            "official_isolated_evaluation": False}


def read_hidden():
    path = ROOT / "evaluator/hidden/test.jsonl"
    manifest = json.loads((ROOT / "evaluator/hidden/manifest.json").read_text())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != manifest["splits"]["test"]["sha256"]:
        raise ValueError("Hidden data integrity check failed")
    cases = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if len(cases) != 320 or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Invalid frozen hidden bank")
    return cases


def validate_predictions(payload, cases):
    if not isinstance(payload, dict) or set(payload) != {"predictions"}:
        raise ValueError("Output must be an object containing only predictions")
    records = payload["predictions"]
    if not isinstance(records, list) or len(records) != len(cases):
        raise ValueError("Exactly one prediction per input is required")
    expected = {case["id"] for case in cases}
    predictions = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != {"id", "f"}:
            raise ValueError("Each prediction must contain exactly id and f")
        identity, estimate = record["id"], record["f"]
        if not isinstance(identity, str) or identity not in expected or identity in predictions:
            raise ValueError("Unknown or duplicate prediction id")
        if type(estimate) not in (float, int) or not math.isfinite(estimate) or not 0 <= estimate <= 1:
            raise ValueError("Every f prediction must be a finite number in [0, 1]")
        predictions[identity] = float(estimate)
    return predictions


def score(cases, predictions, targets):
    squared = [(predictions[case["id"]] - case["f"]) ** 2 for case in cases]
    overall = math.sqrt(math.fsum(squared) / len(squared))
    by_family, by_length = {}, {}
    for key, groups in (("family", by_family), ("L", by_length)):
        for group in sorted({case[key] for case in cases}):
            selected = [error for case, error in zip(cases, squared) if case[key] == group]
            groups[str(group)] = {"count": len(selected), "rmse": math.sqrt(math.fsum(selected) / len(selected))}
    worst = max(group["rmse"] for group in by_family.values())
    passed = overall <= targets["overall_rmse"] and worst <= targets["worst_family_rmse"]
    return {"passed": passed, "overall_rmse": overall, "worst_family_rmse": worst,
            "by_family": by_family, "by_length": by_length, "records": len(cases),
            "normalized_error": max(overall / targets["overall_rmse"], worst / targets["worst_family_rmse"])}


def evaluate(submission):
    try:
        configuration = json.loads((ROOT / "evaluator/targets.json").read_text())
        if not configuration["frozen"]:
            raise ValueError("Targets must be frozen before evaluation")
        cases = read_hidden()
    except Exception as error:
        raise EvaluatorInfrastructureError(str(error)) from error
    public_inputs = {"cases": [{key: case[key] for key in ("id", "L", "fields")} for case in cases]}
    try:
        payload, resources = run_submission(
            submission, public_inputs, timeout=configuration["wall_seconds"],
            startup_timeout=configuration["startup_seconds"], streaming=True,
            memory_mb=configuration["memory_mb"], participant=ROOT / "participant")
    except Exception as error:
        category = EvaluatorInfrastructureError if infrastructure_failure(error) else SubmissionEvaluationError
        raise category(str(error)) from error
    try:
        predictions = validate_predictions(payload, cases)
    except Exception as error:
        raise SubmissionEvaluationError(str(error)) from error
    try:
        result = score(cases, predictions, configuration)
    except Exception as error:
        raise EvaluatorInfrastructureError(str(error)) from error
    result.update({"mode": "D HIDDEN PREDICTION", "resources": resources,
                   "targets": {key: configuration[key] for key in ("overall_rmse", "worst_family_rmse")},
                   "official_isolated_evaluation": True})
    resource_valid = resources["wall_seconds"] <= configuration["wall_seconds"] and resources["startup_seconds"] <= configuration["startup_seconds"]
    result["passed"] = result["passed"] and resource_valid
    result.update({"core_score": result["overall_rmse"],
                   "worst_family_score": result["worst_family_rmse"],
                   "valid": True, "evaluator_valid": True, "resource_score": float(resource_valid),
                   "runtime_seconds": resources["wall_seconds"],
                   "reason": "passed" if result["passed"] else "accuracy_target_not_met" if resource_valid else "submission_resource_limit"})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(args.submission)
    except Exception as error:
        if not isinstance(error, (EvaluatorInfrastructureError, SubmissionEvaluationError)):
            error = EvaluatorInfrastructureError(str(error))
        result = failure_report(error)
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text)
    sys.stdout.write(text)
    return 2 if "error" in result else 0


if __name__ == "__main__":
    raise SystemExit(main())
