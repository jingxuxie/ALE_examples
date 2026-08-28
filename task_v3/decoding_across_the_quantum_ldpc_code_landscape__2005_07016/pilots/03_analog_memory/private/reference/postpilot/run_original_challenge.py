from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
OUTPUT = Path(__file__).resolve().parent
PILOT = OUTPUT.parents[2]
PAPER = PILOT.parents[1]
WRITABLE = (OUTPUT, PILOT / "private/challenge_pool/postpilot")


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(directory):
    return {
        str(path.relative_to(directory)): checksum(path)
        for path in sorted(directory.rglob("*")) if path.is_file()
    }


def protected_inventory():
    return {
        str(path.relative_to(PILOT)): checksum(path)
        for path in sorted(PILOT.rglob("*"))
        if path.is_file() and not any(path.is_relative_to(root) for root in WRITABLE)
    }


def main():
    before = protected_inventory()
    attempt = PILOT / "attempt"
    snapshot = OUTPUT / "submission_snapshot"
    submitted = inventory(attempt)
    if not snapshot.exists():
        shutil.copytree(attempt, snapshot, copy_function=shutil.copy2)
    if inventory(snapshot) != submitted:
        raise RuntimeError("Snapshot is not byte-identical to the original attempt")
    (OUTPUT / "before.json").write_text(json.dumps({
        "submitted_files": submitted, "protected_files": before,
    }, indent=2) + "\n")
    report_path = OUTPUT / "original_challenge_report.json"
    command = [
        sys.executable, str(PILOT / "private/evaluator.py"),
        "--submission", str(snapshot), "--report", str(report_path), "--split", "challenge",
    ]
    subprocess.run(
        command, cwd=PAPER, check=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
    )
    report = json.loads(report_path.read_text())
    manifest = json.loads((PILOT / "private/challenge_pool/challenge/manifest.json").read_text())
    references = {record["case_id"]: record for record in manifest["cases"]}
    comparisons = []
    for result in report["cases"]:
        original = references[result["case_id"]]
        comparisons.append({
            "case_id": result["case_id"], "family": result["family"],
            "configuration": original["configuration"], "shots": original["shots"],
            "submission": result["metrics"], "reference": original["metrics"]["reference"],
            "weak": original["metrics"]["weak"],
            "submission_cpu_seconds": result["runtime_seconds"],
            "submission_wall_seconds": result["wall_seconds"],
            "max_rss_kb": result["execution"].get("max_rss_kb"),
            "reference_cpu_seconds": original["build_seconds"]["reference"],
            "status": result["status"],
        })
    after = protected_inventory()
    unchanged = before == after
    summary = {
        "mean_core": report["mean_core"], "worst_family": report["worst_family"],
        "runtime_seconds": report["runtime_seconds"], "wall_seconds": report["wall_seconds"],
        "cases": comparisons,
        "protected_files_unchanged": unchanged,
        "attempt_unchanged": inventory(attempt) == submitted,
        "snapshot_unchanged": inventory(snapshot) == submitted,
        "additional_regimes_tested": 0,
        "final_holdout_generated": False,
        "fresh_model_calls": 0,
    }
    (OUTPUT / "original_challenge_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (OUTPUT / "after.json").write_text(json.dumps(after, indent=2) + "\n")
    if not unchanged or not summary["attempt_unchanged"]:
        raise RuntimeError("Protected files changed during audit; inspect before/after inventories")
    print(json.dumps({
        name: summary[name] for name in (
            "mean_core", "worst_family", "runtime_seconds", "wall_seconds", "protected_files_unchanged"
        )
    }))


if __name__ == "__main__":
    main()
