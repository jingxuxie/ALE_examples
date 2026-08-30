import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
PAPER = Path(__file__).resolve().parents[1]
GENERATION = PAPER / "concept_1/generations/generation_2"
ARTIFACTS = GENERATION / "adversary"
sys.path.insert(0, str(GENERATION / "evaluator"))

from evaluate import (EvaluatorInfrastructureError, SubmissionEvaluationError,
                      failure_report, infrastructure_failure, score, validate_predictions)
from sandbox import run_submission


FAMILIES = ("iid_uniform", "ordered_blocks", "alternating_correlated", "shuffled_pairs")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path, report):
    if path.exists():
        raise ValueError(f"Refusing to overwrite completed report: {path.name}")
    pending = path.with_name(path.name + ".pending")
    with pending.open("x") as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.link(pending, path)
    pending.unlink()


def load_replication():
    manifest_path = ARTIFACTS / "replication_manifest.json"
    bank_path = ARTIFACTS / "replication_bank.jsonl"
    manifest = json.loads(manifest_path.read_text())
    if not manifest["complete"] or manifest["records"] != 640 or sha256(bank_path) != manifest["bank_sha256"]:
        raise ValueError("Private replication bank is incomplete or has changed")
    if sha256(ARTIFACTS / "replication_seed.json") != manifest["seed_sha256"]:
        raise ValueError("Replication seed archive differs from its completed manifest")
    targets_path = GENERATION / "evaluator/targets.json"
    targets = json.loads(targets_path.read_text())
    expected = {"overall_rmse": 0.035, "worst_family_rmse": 0.05, "wall_seconds": 3,
                "startup_seconds": 60, "memory_mb": 2048, "threads": 4, "target_length": 14}
    if not targets["frozen"] or any(targets[key] != value for key, value in expected.items()):
        raise ValueError("Expected unchanged frozen generation-two targets and resource limits")
    if sha256(targets_path) != manifest["source_sha256"]["evaluator/targets.json"]:
        raise ValueError("Frozen scoring configuration changed after replication sampling")
    cases = [json.loads(line) for line in bank_path.read_text().splitlines() if line.strip()]
    if len(cases) != 640 or len({case["id"] for case in cases}) != 640:
        raise ValueError("Expected 640 unique replication IDs")
    if Counter((case["batch"], case["family"]) for case in cases) != Counter(
            {(batch, family): 80 for batch in (0, 1) for family in FAMILIES}):
        raise ValueError("Replication batches are not independently stratified 320-case sets")
    if any(case["L"] != 14 or len(case["fields"]) != 14 or not math.isfinite(case["f"])
           or not 0 <= case["f"] <= 1 for case in cases):
        raise ValueError("Invalid L14 replication record")
    return cases, targets, manifest


def additional_errors(cases, predictions):
    result = {}
    for group in ("all",) + FAMILIES:
        selected = [case for case in cases if group == "all" or case["family"] == group]
        errors = [predictions[case["id"]] - case["f"] for case in selected]
        result[group] = {"count": len(errors), "mae": math.fsum(abs(error) for error in errors) / len(errors),
                         "bias": math.fsum(errors) / len(errors),
                         "maximum_absolute_error": max(abs(error) for error in errors)}
    return result


def score_batch(submission, cases, targets, batch):
    inputs = {"cases": [{key: case[key] for key in ("id", "L", "fields")} for case in cases]}
    resources = None
    try:
        payload, resources = run_submission(
            submission, inputs, timeout=targets["wall_seconds"],
            startup_timeout=targets["startup_seconds"], streaming=True,
            memory_mb=targets["memory_mb"], participant=GENERATION / "participant")
        try:
            predictions = validate_predictions(payload, cases)
        except Exception as error:
            raise SubmissionEvaluationError(str(error)) from error
        try:
            result = score(cases, predictions, targets)
        except Exception as error:
            raise EvaluatorInfrastructureError(str(error)) from error
        accuracy_passed = result["passed"]
        resource_valid = (resources["wall_seconds"] <= targets["wall_seconds"]
                          and resources["startup_seconds"] <= targets["startup_seconds"])
        result.update({"mode": "D HIDDEN PREDICTION", "generation": 2, "ratchet": 1,
                       "batch": batch, "planned_records": 320, "scored_records": len(cases),
                       "core_score": result["overall_rmse"], "worst_family_score": result["worst_family_rmse"],
                       "accuracy_passed": accuracy_passed, "resource_score": float(resource_valid),
                       "resources": resources, "runtime_seconds": resources["wall_seconds"],
                       "inference_margin_seconds": targets["wall_seconds"] - resources["wall_seconds"],
                       "valid": True, "evaluator_valid": True,
                       "passed": accuracy_passed and resource_valid,
                       "reason": "passed" if accuracy_passed and resource_valid else
                                 "accuracy_target_not_met" if resource_valid else "submission_resource_limit",
                       "official_isolated_evaluation": True,
                       "additional_errors": additional_errors(cases, predictions)})
        return result, predictions
    except Exception as error:
        category = EvaluatorInfrastructureError if infrastructure_failure(error) else SubmissionEvaluationError
        result = failure_report(error if isinstance(error, (EvaluatorInfrastructureError, SubmissionEvaluationError))
                                else category(str(error)))
        result.update({"batch": batch, "planned_records": 320, "scored_records": 0,
                       "accuracy_passed": None,
                       "timing_failure_alone_is_not_hardness_evidence": True})
        if resources is not None:
            result["resources"] = resources
            result["runtime_seconds"] = resources["wall_seconds"]
        return result, None


def run(submission, output):
    try:
        cases, targets, manifest = load_replication()
    except Exception as error:
        return failure_report(EvaluatorInfrastructureError(str(error)))
    batch_reports, predictions = [], {}
    for batch in (0, 1):
        batch_cases = [case for case in cases if case["batch"] == batch]
        report, batch_predictions = score_batch(submission, batch_cases, targets, batch)
        batch_reports.append(report)
        if batch_predictions is not None:
            predictions.update(batch_predictions)
        batch_output = output.with_name(output.stem + f"_batch_{batch}.json")
        write_once(batch_output, report)
        print(json.dumps({"batch": batch, "passed": report["passed"],
                          "core_score": report["core_score"], "worst_family_score": report["worst_family_score"],
                          "runtime_seconds": report["runtime_seconds"], "reason": report["reason"]}),
              file=sys.stderr, flush=True)
    complete_predictions = len(predictions) == 640
    aggregate = score(cases, predictions, targets) if complete_predictions else None
    runtime_values = [report["runtime_seconds"] for report in batch_reports if report["runtime_seconds"] is not None]
    resources_passed = all(report["resource_score"] == 1 for report in batch_reports)
    evaluator_valid = all(report["evaluator_valid"] for report in batch_reports)
    passed = all(report["passed"] for report in batch_reports)
    if not evaluator_valid:
        reason = "infrastructure_error"
    elif not complete_predictions:
        reason = "one_or_more_batches_invalid_or_resource_limited"
    elif not resources_passed:
        reason = "submission_resource_limit"
    elif not passed:
        reason = "one_or_more_batches_miss_accuracy_targets"
    else:
        reason = "both_replication_batches_passed"
    result = {"mode": "D HIDDEN PREDICTION", "concept": "concept_1", "generation": 2, "ratchet": 1,
              "purpose": "Private post-completion champion replication, not a new task or changed threshold",
              "created_utc": datetime.now(timezone.utc).isoformat(), "submission": str(submission),
              "records": 640, "scored_records": len(predictions), "batch_reports": batch_reports,
              "aggregate": aggregate, "core_score": aggregate["overall_rmse"] if aggregate else None,
              "worst_family_score": aggregate["worst_family_rmse"] if aggregate else None,
              "by_family": aggregate["by_family"] if aggregate else None,
              "valid": complete_predictions, "evaluator_valid": evaluator_valid,
              "resource_score": float(resources_passed) if evaluator_valid else None,
              "runtime_seconds": max(runtime_values) if runtime_values else None,
              "total_reported_inference_seconds": math.fsum(runtime_values) if runtime_values else None,
              "runtime_alias_definition": "Maximum reported inference runtime of the two independent calls; each retains its own 3-second gate",
              "passed": passed, "reason": reason,
              "pass_rule": "Both independent 320-case batches must satisfy unchanged numeric and resource gates",
              "assessment": "Replication evidence only; no automatic hard/easy conclusion, especially from borderline timing",
              "timing_failure_alone_is_not_hardness_evidence": True,
              "targets": {key: targets[key] for key in ("overall_rmse", "worst_family_rmse", "wall_seconds", "startup_seconds", "memory_mb", "threads")},
              "bank_sha256": manifest["bank_sha256"],
              "trusted_evaluator_sha256": sha256(GENERATION / "evaluator/evaluate.py"),
              "sandbox_sha256": sha256(GENERATION / "evaluator/sandbox.py"),
              "private_labels_passed_to_submission": False, "submission_imported_in_parent": False}
    if complete_predictions:
        result["additional_errors"] = additional_errors(cases, predictions)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Score an explicitly authorized completed submission on two private L14 replication batches.",
        epilog="Requires the same outer sandbox privileges as the frozen evaluator. Never discovers or selects live submissions.")
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.parent != ARTIFACTS.resolve() or not output.name.startswith("replication_") or output.suffix != ".json":
        parser.error("--output must be generation_2/adversary/replication_*.json")
    destinations = [output] + [output.with_name(output.stem + f"_batch_{batch}.json") for batch in (0, 1)]
    if any(path.exists() or path.with_name(path.name + ".pending").exists() for path in destinations):
        parser.error("Existing reports are immutable; choose a new replication output name")
    result = run(args.submission.resolve(), output)
    write_once(output, result)
    print(json.dumps(result, indent=2, allow_nan=False), flush=True)
    return 2 if not result["evaluator_valid"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
