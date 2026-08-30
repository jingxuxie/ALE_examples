import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


EVALUATOR_ROOT = Path(__file__).resolve().parent


class IntegrityError(ValueError):
    pass


def load_trusted(evaluator_root=EVALUATOR_ROOT):
    manifest = json.loads((evaluator_root / "frozen.json").read_text(encoding="utf-8"))
    expected_paths = {"_checker.py", "hidden/instances.json"}
    if manifest.get("schema_version") != 1 or set(manifest.get("sha256", {})) != expected_paths:
        raise IntegrityError("Invalid frozen evaluator manifest.")
    for relative_path, expected_hash in manifest["sha256"].items():
        observed_hash = hashlib.sha256((evaluator_root / relative_path).read_bytes()).hexdigest()
        if observed_hash != expected_hash:
            raise IntegrityError("Frozen evaluator asset hash mismatch: " + relative_path)
    specification = importlib.util.spec_from_file_location("native_cx_trusted_checker", evaluator_root / "_checker.py")
    trusted_checker = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(trusted_checker)
    suite = trusted_checker.validate_instances(trusted_checker.load_json_file(evaluator_root / "hidden" / "instances.json"))
    if len(suite["targets"]) != 4:
        raise IntegrityError("The frozen task requires exactly four targets.")
    return trusted_checker, suite, manifest


def evaluate(solution_path, evaluator_root=EVALUATOR_ROOT):
    trusted_checker, suite, manifest = load_trusted(evaluator_root)
    artifact = Path(solution_path)
    if artifact.is_dir() and not artifact.is_symlink():
        artifact = artifact / "solution.json"
    report = trusted_checker.evaluate_file(artifact, suite)
    report["suite_id"] = suite["suite_id"]
    report["frozen_instances_sha256"] = manifest["sha256"]["hidden/instances.json"]
    return report


def infrastructure_report():
    return {
        "valid": False, "passed": False, "reason": "evaluator_integrity_error",
        "evaluator_error": True, "core_score": 0.0,
        "worst_family_score": 0.0, "resource_score": 0.0,
        "solved_targets": 0, "total_targets": 4,
        "family_scores": {"mesh": 0.0, "bottleneck": 0.0}, "per_target": [],
    }


def main():
    parser = argparse.ArgumentParser(description="Grade a frozen native-CX JSON witness without executing submitted code.")
    parser.add_argument("artifact", nargs="?", type=Path, help="solution.json or a directory containing it")
    parser.add_argument("--solution", "--submission", dest="solution", type=Path)
    parser.add_argument("--output", type=Path, help="Optional report file; the report is also printed to stdout")
    arguments = parser.parse_args()
    if (arguments.artifact is None) == (arguments.solution is None):
        parser.error("Provide exactly one positional artifact or --solution/--submission path.")
    artifact = arguments.artifact if arguments.artifact is not None else arguments.solution
    try:
        report = evaluate(artifact)
        exit_code = 0 if report["passed"] else 1
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        report = infrastructure_report()
        exit_code = 2
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.output is not None:
        artifact_file = artifact / "solution.json" if artifact.is_dir() else artifact
        if arguments.output.resolve() == artifact_file.resolve():
            parser.error("The report output must not overwrite the submitted artifact.")
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
