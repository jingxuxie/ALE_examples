#!/usr/bin/env python3
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time


EVALUATOR = Path(__file__).resolve().parent


def load_context():
    hidden = EVALUATOR / "hidden"
    manifest = json.loads((hidden / "frozen_manifest.json").read_text())
    target_bytes = (hidden / "target.json").read_bytes()
    checker_path = EVALUATOR / "validator.py"
    if hashlib.sha256(target_bytes).hexdigest() != manifest["target_sha256"]:
        raise ValueError("target digest mismatch")
    if hashlib.sha256(checker_path.read_bytes()).hexdigest() != manifest["validator_sha256"]:
        raise ValueError("trusted validator digest mismatch")
    target = json.loads(target_bytes)
    if target["generation"] != 2 or target["pair_count"] != 4096 or target["direction_count"] != 8192:
        raise ValueError("wrong generation or scale")
    if target["counts"] != {"0": 3328, "1": 512, "2": 256} or target["max_submission_bytes"] != 131072:
        raise ValueError("wrong counts or resource cap")
    specification = importlib.util.spec_from_file_location("trusted_static_eec_validator", checker_path)
    checker = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(checker)
    checker.validate_target(target)
    return checker, target, manifest


def evaluate(submission):
    started = time.perf_counter()
    try:
        checker, target, manifest = load_context()
        report = checker.evaluate(submission, target)
        report.update(target_sha256=manifest["target_sha256"], generation=2)
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        report = {"core_score": 0.0, "worst_family_score": 0.0, "runtime_score": 0.0,
                  "resource_score": 0.0, "valid": False, "passed": False,
                  "configuration_error": True, "reason": "evaluator configuration error"}
    report["runtime_seconds"] = time.perf_counter() - started
    return report


def main():
    parser = argparse.ArgumentParser(description="Grade a static inverse-EEC artifact against the frozen target.")
    parser.add_argument("submission")
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    submitted = Path(arguments.submission)
    candidate = submitted / "design.json" if submitted.is_dir() else submitted
    if arguments.report and arguments.report.resolve() == candidate.resolve():
        parser.error("report must not overwrite design.json")
    report = evaluate(arguments.submission)
    serialized = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 2 if report["configuration_error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
