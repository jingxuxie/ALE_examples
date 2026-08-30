import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    options = parser.parse_args()
    failures = []
    pending = []
    checked = []
    for record_path in sorted(ROOT.glob("concept_*/attempts/v_*.run.json")):
        record = load(record_path)
        name = record_path.name.removesuffix(".run.json")
        concept = record_path.parents[1]
        label = f"{concept.name}/{name}"
        if record["status"] == "running":
            pending.append(label)
            continue
        scoring_path = record_path.parent / f"{name}.scoring.json"
        evaluation_path = record_path.parent / f"{name}.evaluation.json"
        if not scoring_path.exists() or not evaluation_path.exists():
            pending.append(label + ": grading")
            continue
        scoring = load(scoring_path)
        evaluation = load(evaluation_path)
        attempt = record_path.parent / name
        artifact = ROOT / scoring["artifact"]
        relative = str(artifact.relative_to(attempt))
        checks = {
            "expected_model": record["model"] == "ultima-alpha",
            "one_hour_limit": record["limit_seconds"] == 3600,
            "bounded_teardown": record["elapsed_seconds"] <= 3630,
            "empty_output_at_start": record["output_empty_at_start"],
            "read_only_participant": record["participant_access"] == "read-only",
            "no_privileged_mounts": record["privileged_mounts"] == [],
            "participant_unchanged_during_trial": record["participant_unchanged"],
            "artifact_not_symlink": not artifact.is_symlink(),
            "artifact_matches_cutoff": digest(artifact) == record["submission_sha256"].get(relative),
            "scoring_matches_cutoff": scoring["artifact_sha256"] == record["submission_sha256"].get(relative),
            "artifact_unchanged_during_grading": scoring["artifact_unchanged_during_evaluation"],
            "pass_implies_valid": not evaluation["passed"] or evaluation["valid"],
        }
        current = load(concept / "status.json")
        generation = current.get("current_generation", current.get("generation", 1))
        archive = concept if generation == record["generation"] else concept / "generations" / f"generation_{record['generation']}"
        participant = archive / ("tested_participant" if (archive / "tested_participant").exists() else "participant")
        evaluator = archive / ("tested_evaluator" if (archive / "tested_evaluator").exists() else "evaluator")
        checks["participant_archive_matches_trial"] = all(digest(participant / path) == expected for path, expected in record["participant_sha256"].items())
        checks["evaluator_matches_scoring_record"] = digest(evaluator / "evaluate.py") == scoring["evaluator_sha256"]
        if concept.name == "concept_1":
            checks["documented_non_scoring_amendment_passed"] = load(ROOT / "authoring/amendment_audit.json")["passed"]
            checks["entire_executable_bundle_matches_cutoff"] = all(digest(attempt / path) == expected for path, expected in record["submission_sha256"].items())
        else:
            checks["evaluator_unchanged_during_trial"] = record["evaluator_unchanged"]
            checks["evaluator_archive_matches_trial"] = all(digest(evaluator / path) == expected for path, expected in record["evaluator_sha256"].items())
        failed = [key for key, passed in checks.items() if not passed]
        failures.extend(f"{label}: {key}" for key in failed)
        checked.append({"attempt": label, "generation": record["generation"], "checks": checks, "passed": not failed})
    passed = not failures and (not pending or not options.require_complete)
    report = {"passed": passed, "complete": not pending, "checked_at": datetime.now(timezone.utc).isoformat(), "failures": failures, "pending": pending, "checked": checked}
    (ROOT / "authoring/attempt_integrity_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": passed, "complete": not pending, "checked_attempts": len(checked), "pending": pending, "failures": failures}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
