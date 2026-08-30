import hashlib
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fingerprint(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(directory.rglob("*")) if path.is_file() and "__pycache__" not in path.parts}


def audit_package(package, canaries):
    required = ["participant/TASK.md", "participant/input", "participant/workspace", "participant/baseline", "evaluator/evaluate.py", "evaluator/hidden", "attempts", "champions", "adversary", "status.json"]
    participant = package / "participant"
    missing = [name for name in required if not (package / name).exists()]
    symlinks = [str(path.relative_to(participant)) for path in participant.rglob("*") if path.is_symlink()]
    leaked = []
    for path in participant.rglob("*"):
        if path.is_file():
            content = path.read_bytes()
            if any(canary in content for canary in canaries):
                leaked.append(str(path.relative_to(participant)))
    status_path = package / "status.json"
    status = json.loads(status_path.read_text()) if status_path.exists() else {}
    return {"package": str(package.relative_to(ROOT)), "missing": missing, "participant_symlinks": symlinks, "canary_leaks": leaked, "status": status.get("status", status.get("build_status")), "ready": status.get("ready")}


def audit_attempt(filename):
    launch = json.loads(filename.read_text())
    output = Path(launch["output"])
    audit_path = output / "isolation_audit.json"
    isolation = json.loads(audit_path.read_text()) if audit_path.exists() else {}
    stem = filename.name.removesuffix(".launch.json")
    report_path = filename.parent / f"{stem}.evaluation.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    result = {"launch": str(filename.relative_to(ROOT)), "participant": str(Path(launch["participant"]).relative_to(ROOT)), "model": launch["model"], "elapsed_seconds": launch.get("elapsed_seconds"), "limit_seconds": launch["limit_seconds"], "fresh_ephemeral": launch["fresh_ephemeral"], "output_initially_empty": launch["output_initially_empty"], "participant_read_only": launch["participant_read_only"], "participant_unchanged": launch.get("participant_unchanged"), "evaluator_unchanged": launch.get("evaluator_unchanged"), "private_reads_denied": isolation.get("private_reads_denied"), "evaluated": report_path.exists(), "evaluation_passed": report.get("passed")}
    if launch.get("elapsed_seconds") is not None:
        result["current_participant_matches_frozen"] = fingerprint(Path(launch["participant"])) == launch["participant_sha256_before"]
        evaluator = Path(launch.get("evaluator", str(Path(launch["participant"]).parent / "evaluator")))
        result["current_evaluator_matches_frozen"] = fingerprint(evaluator) == launch["evaluator_sha256_before"]
    if launch.get("scoring_snapshot"):
        result["snapshot_unchanged"] = fingerprint(Path(launch["scoring_snapshot"])) == launch["snapshot_sha256"]
        result["post_deadline_files_excluded"] = launch["post_deadline_files_excluded"]
    cutoff_path = filename.parent / f"{stem}.cutoff.json"
    if cutoff_path.exists():
        cutoff = json.loads(cutoff_path.read_text())
        artifact = Path(cutoff["artifact_directory"]) / "solution.json"
        result["cutoff_before_deadline"] = bool(cutoff.get("captured_utc")) and datetime.fromisoformat(cutoff["captured_utc"]) <= datetime.fromisoformat(cutoff["deadline_utc"])
        result["cutoff_snapshot_unchanged"] = artifact.exists() and hashlib.sha256(artifact.read_bytes()).hexdigest() == cutoff.get("captured_sha256")
    return result


def main():
    concepts = [ROOT / f"concept_{index}" for index in range(1, 4)]
    packages = [package for concept in concepts for package in [concept, *sorted((concept / "generations").glob("generation_*"))] if (package / "status.json").exists()]
    canaries = [(ROOT / "private/generation_canary.txt").read_bytes()]
    canaries.extend(path.read_bytes() for package in packages if (path := package / "evaluator/hidden/isolation_canary.txt").exists())
    reports = [audit_package(package, canaries) for package in packages]
    attempts = [audit_attempt(filename) for concept in concepts for filename in sorted((concept / "attempts").glob("*.launch.json"))]
    completed = [attempt for attempt in attempts if attempt["elapsed_seconds"] is not None]
    valid = all(not report["missing"] and not report["participant_symlinks"] and not report["canary_leaks"] for report in reports)
    isolation_valid = bool(completed) and all(attempt["model"] == "ultima-alpha" and attempt["limit_seconds"] == 3600 and all(attempt[key] for key in ("fresh_ephemeral", "output_initially_empty", "participant_read_only", "participant_unchanged", "evaluator_unchanged", "private_reads_denied", "current_participant_matches_frozen", "current_evaluator_matches_frozen")) for attempt in completed)
    snapshots_valid = all(all(attempt.get(key, True) for key in ("snapshot_unchanged", "cutoff_before_deadline", "cutoff_snapshot_unchanged")) for attempt in completed)
    report = {"package_layout_valid": valid, "completed_attempt_isolation_valid": isolation_valid, "scoring_snapshots_valid": snapshots_valid, "completed_attempt_count": len(completed), "pending_attempt_count": len(attempts) - len(completed), "all_completed_attempts_evaluated": all(attempt["evaluated"] for attempt in completed), "packages": reports, "attempts": attempts}
    (ROOT / "private/package_audit.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
