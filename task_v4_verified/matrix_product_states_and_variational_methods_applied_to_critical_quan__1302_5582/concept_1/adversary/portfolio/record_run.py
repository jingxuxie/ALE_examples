"""Summarize an actual frozen evaluation without changing its report or sources."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", required=True, choices=("v1", "v2", "v3"))
    parser.add_argument("--run-label")
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    run_label = args.run_label or args.variant
    if Path(run_label).name != run_label:
        raise ValueError("Run label must be a single filename component")
    report_path = folder / (run_label + "_hidden_report.json")
    report = json.loads(report_path.read_text())
    invocation = json.loads((folder / (run_label + "_invocation.json")).read_text())
    actual_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in sorted((folder / args.variant).glob("*.py"))}
    if actual_hashes != invocation["source_hashes"]:
        raise RuntimeError("Evaluated source snapshot changed")
    summary = report.get("summary", report)
    stage_rows = []
    for case in report.get("cases", []):
        for stage, measured in case["stages"].items():
            stage_rows.append({"case_id": case["case_id"], "family": case["family"], "stage": stage,
                               **{key: measured[key] for key in ("energy", "parity", "max_bond", "quality",
                                   "cpu_seconds", "cpu_accounted", "wall_seconds", "valid", "error",
                                   "process_valid", "returncode", "timed_out") if key in measured}})
    passed = summary.get("target_met") is True and summary.get("all_valid") is True
    reported_cpu = sum(row.get("cpu_seconds", 0) for row in stage_rows)
    all_cpu_accounted = bool(stage_rows) and all(row.get("cpu_accounted") is True for row in stage_rows)
    certificate = {"variant": args.variant, "run_label": run_label, "summary": summary, "full_passing_algorithm_known": passed,
                   "passing_submission": str((folder / args.variant).resolve()) if passed else None,
                   "actual_frozen_bwrap_evaluation": True, "source_hashes": actual_hashes,
                   "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
                   "freeze_sha256": invocation["freeze_sha256"],
                   "validation_sha256": invocation["validation_sha256"],
                   "calibration_sha256": report.get("calibration_sha256"),
                   "resources": {"total_cpu_seconds": reported_cpu if all_cpu_accounted else None,
                                 "reported_cpu_seconds_sum": reported_cpu,
                                 "all_cpu_accounted": all_cpu_accounted,
                                 "total_wall_seconds": sum(row.get("wall_seconds", 0) for row in stage_rows),
                                 "wall_scope": "Sum of timed invocations; staging and evaluator overhead excluded",
                                 "valid_outputs": sum(row.get("valid") is True for row in stage_rows),
                                 "output_count": len(stage_rows)},
                   "stages": stage_rows, "participant_attempts_accessed": False}
    (folder / (run_label + "_certificate.json")).write_text(json.dumps(certificate, indent=2) + "\n")
    print(json.dumps({"variant": args.variant, "summary": summary, "resources": certificate["resources"]}, indent=2))


if __name__ == "__main__":
    main()
