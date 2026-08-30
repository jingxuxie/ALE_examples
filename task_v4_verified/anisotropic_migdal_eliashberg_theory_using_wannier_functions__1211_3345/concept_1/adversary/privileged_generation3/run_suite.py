"""Private provenance wrapper; candidate imports occur only in the sandbox."""

import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import shutil
import sys
import tempfile
import time

STARTED_CPU = time.process_time()
STARTED_CHILDREN = resource.getrusage(resource.RUSAGE_CHILDREN)
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

SIDECAR = Path(__file__).resolve().parent
CONCEPT = SIDECAR.parents[1]
PROTOCOL = json.loads((SIDECAR / "protocol.json").read_text())


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            hasher.update(block)
    return hasher.hexdigest()


def identities():
    actual = {name: digest(CONCEPT / name) for name in PROTOCOL["active_sealed_files"]}
    mismatches = [name for name, value in actual.items() if value != PROTOCOL["active_sealed_files"][name]]
    seal_path = CONCEPT / "evaluator/hidden/prelaunch_seal.json"
    seal_hash = digest(seal_path)
    if seal_hash != PROTOCOL["active_prelaunch_seal_sha256"]:
        mismatches.append("evaluator/hidden/prelaunch_seal.json")
    if mismatches:
        raise RuntimeError("Active seal mismatch: " + repr(mismatches))
    manifest_path = CONCEPT / "evaluator/hidden/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    return {
        "generation": 3,
        "prelaunch_seal_path": str(seal_path),
        "prelaunch_seal_sha256": seal_hash,
        "verified_sealed_files": len(actual),
        "dataset_manifest_path": str(manifest_path),
        "dataset_manifest_sha256": digest(manifest_path),
        "dataset_case_ids": [record["case_id"] for record in manifest["cases"]],
        "case_file_sha256": {name: value for name, value in actual.items() if name.startswith("evaluator/hidden/cases/")},
        "reference_file_sha256": {name: value for name, value in actual.items() if name.startswith("evaluator/hidden/references/")},
        "policy_sha256": digest(CONCEPT / "evaluator/hidden/policy.json"),
        "evaluator_sha256": digest(CONCEPT / "evaluator/evaluate.py"),
        "baseline_anchor_sha256": digest(CONCEPT / "evaluator/hidden/baseline_anchor.json"),
        "shared_runner_sha256": digest(CONCEPT.parent / "authoring/sandbox_runner.py"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, choices=("candidate_1", "candidate_2"))
    parser.add_argument("--tag", required=True)
    parser.add_argument("--cases", nargs="*")
    arguments = parser.parse_args()
    if not arguments.tag.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Simple report tag required")
    reports = SIDECAR / "reports"
    reports.mkdir(exist_ok=True)
    destination = reports / (arguments.tag + ".json")
    provenance_path = reports / (arguments.tag + ".provenance.json")
    if destination.exists() or provenance_path.exists():
        raise ValueError("Report tags are immutable and must be unique")
    previous_cpu = sum(json.loads(path.read_text())["consumed_cpu_seconds"] for path in reports.glob("*.provenance.json"))
    reserve = 300.0 if not arguments.cases else 30.0 * len(arguments.cases) + 20
    if previous_cpu + reserve > PROTOCOL["cpu_budget_seconds"]:
        raise RuntimeError("Insufficient remaining private CPU budget for this run")
    before = identities()
    source = SIDECAR / arguments.candidate
    frozen_source = SIDECAR / "report_sources" / arguments.tag
    frozen_source.parent.mkdir(exist_ok=True)
    shutil.copytree(source, frozen_source, symlinks=True)
    source_hashes = {str(path.relative_to(frozen_source)): digest(path) for path in frozen_source.rglob("*") if path.is_file()}
    scratch = SIDECAR / "scratch"
    scratch.mkdir(exist_ok=True)
    tempfile.tempdir = str(scratch)
    sys.path.insert(0, str(CONCEPT / "evaluator"))
    import evaluate

    started_wall = time.monotonic()
    report = None
    failure = None
    try:
        with (reports / (arguments.tag + ".log")).open("w") as logfile, contextlib.redirect_stderr(logfile):
            report = evaluate.evaluate(frozen_source, set(arguments.cases) if arguments.cases else None)
        destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    except Exception as error:
        failure = repr(error)
        raise
    finally:
        after = identities()
        children = resource.getrusage(resource.RUSAGE_CHILDREN)
        parent_cpu = time.process_time() - STARTED_CPU
        child_cpu = children.ru_utime + children.ru_stime - STARTED_CHILDREN.ru_utime - STARTED_CHILDREN.ru_stime
        consumed = parent_cpu + child_cpu
        command = [sys.executable, "-B", str(Path(__file__).resolve()), *sys.argv[1:]]
        provenance = {
            **before,
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "identity_rechecked_after_run": after == before,
            "active_assets_modified": False,
            "candidate": arguments.candidate,
            "frozen_submission_path": str(frozen_source),
            "candidate_files_sha256": source_hashes,
            "command": shlex.join(command),
            "codepath": "Immutable active evaluator.evaluate(frozen_submission, case_ids); its run_candidate invokes evaluator/launch.py and shared authoring/sandbox_runner.py; no policy override",
            "selected_case_ids": arguments.cases,
            "report_path": str(destination),
            "report_sha256": digest(destination) if report else None,
            "complete_suite": bool(report and report["complete_suite"]),
            "passing_candidate": arguments.candidate if report and report["complete_suite"] and report["passed"] else None,
            "resources": PROTOCOL["candidate_resources"],
            "parent_cpu_seconds": parent_cpu,
            "children_cpu_seconds": child_cpu,
            "consumed_cpu_seconds": consumed,
            "portfolio_cpu_seconds_cumulative": previous_cpu + consumed,
            "portfolio_cpu_budget_seconds": PROTOCOL["cpu_budget_seconds"],
            "wall_seconds": time.monotonic() - started_wall,
            "error": failure,
            "candidate_imported_in_trusted_parent": False,
            "fresh_v5_accessed_or_contacted": False,
        }
        provenance_path.write_text(json.dumps(provenance, indent=2, allow_nan=False) + "\n")
        print(json.dumps({"report": str(destination), "core_score": report["core_score"] if report else None,
                          "worst_family_score": report["worst_family_score"] if report else None,
                          "passing_candidate": provenance["passing_candidate"],
                          "consumed_cpu_seconds": consumed, "portfolio_cpu_seconds_cumulative": previous_cpu + consumed}))


if __name__ == "__main__":
    main()
