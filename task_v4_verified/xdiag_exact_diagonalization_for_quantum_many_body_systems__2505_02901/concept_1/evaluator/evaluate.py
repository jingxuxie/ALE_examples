import argparse
import json
import os
import tempfile
import time
from pathlib import Path

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

from isolation import SubmissionFailure, run_isolated
from scoring import InvalidPolicy, exact_score, strict_json


HERE = Path(__file__).resolve().parent


def load_configurations(directory):
    manifest = strict_json((directory / "manifest.json").read_text())
    configurations = [strict_json((directory / entry["configuration"]).read_text())
                      for entry in manifest["cases"]]
    return manifest, configurations


def evaluate(submission, suite_path=None, baseline_path=None):
    suite_path = HERE / "hidden" / "suite.json" if suite_path is None else Path(suite_path)
    baseline_path = HERE / "hidden" / "baseline.json" if baseline_path is None else Path(baseline_path)
    suite = strict_json(suite_path.read_text())
    baseline = strict_json(baseline_path.read_text())
    targets = strict_json((HERE / "hidden" / "targets.json").read_text())
    records = []
    families = {}
    started = time.monotonic()
    for entry in suite["fleets"]:
        directory = suite_path.parent / entry["directory"]
        try:
            with tempfile.TemporaryDirectory(prefix="xdiag_fleet_") as temporary:
                output, elapsed = run_isolated(submission, directory, temporary, targets["seconds_per_fleet"])
                policy = strict_json(output)
                manifest, configurations = load_configurations(directory)
                physics_start = time.monotonic()
                result = exact_score(manifest, configurations, policy)
                verifier_seconds = time.monotonic() - physics_start
            reference = baseline["fleets"][entry["id"]]["objective"]
            improvement = 100 * (1 - result["objective"] / reference)
            families.setdefault(entry["family"], []).append(improvement)
            records.append(dict(result, id=entry["id"], family=entry["family"],
                                baseline_objective=reference, improvement_percent=improvement,
                                submission_seconds=elapsed, verifier_seconds=verifier_seconds, valid=True))
        except (SubmissionFailure, InvalidPolicy, OSError, KeyError, TypeError, ValueError) as error:
            records.append({"id": entry["id"], "family": entry["family"], "valid": False, "reason": str(error)})
            return {"valid": False, "passed": False, "core_score": 0.0, "worst_family_score": 0.0,
                    "resource_score": 0.0, "reason": "invalid submission: " + str(error),
                    "fleets": records, "total_seconds": time.monotonic() - started}
    family_scores = {family: sum(values) / len(values) for family, values in families.items()}
    core = sum(family_scores.values()) / len(family_scores)
    worst = min(family_scores.values())
    passed = core + 1e-6 >= targets["core_improvement_percent"] and worst + 1e-6 >= targets["worst_family_improvement_percent"]
    maximum_runtime = max(record["submission_seconds"] for record in records)
    return {"valid": True, "passed": passed, "core_score": core, "worst_family_score": worst,
            "family_scores": family_scores,
            "resource_score": 100 * max(0, 1 - maximum_runtime / targets["seconds_per_fleet"]),
            "reason": "both fixed quality targets met" if passed else "below fixed core and/or worst-family improvement target",
            "targets": targets, "fleets": records, "total_seconds": time.monotonic() - started}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        report = evaluate(arguments.submission)
    except Exception as error:
        report = {"valid": False, "passed": False, "core_score": 0.0, "worst_family_score": 0.0,
                  "resource_score": 0.0, "infrastructure_error": True, "reason": str(error)}
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in ("valid", "passed", "core_score", "worst_family_score", "reason")}))
    if report.get("infrastructure_error"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
