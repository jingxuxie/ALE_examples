import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_1"


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"Symlink cannot be archived: {path}")
        if path.is_file():
            result[str(path.relative_to(directory))] = digest(path)
    return result


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def complete_frozen_inputs(archive):
    calibration = load(archive / "evaluator/hidden/calibration.json")
    for relative, expected in calibration["frozen_hashes"].items():
        destination = archive / relative
        if not destination.exists():
            source = CONCEPT / relative
            assert digest(source) == expected
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        assert digest(destination) == expected
    files = manifest(archive)
    files.pop("manifest.json", None)
    write_json(archive / "manifest.json", files)
    return len(calibration["frozen_hashes"])


def main():
    status_path = CONCEPT / "status.json"
    status = load(status_path)
    assert status["generation"] == 1
    assert status["status"] == "frozen_ready"
    freeze = load(CONCEPT / status["freeze_manifest"])
    entries = []
    for attempt in ("v_3", "v_4"):
        audit_path = CONCEPT / "attempts" / f"{attempt}_audit" / "audit.json"
        evaluation_path = audit_path.with_name("evaluation.json")
        audit = load(audit_path)
        evaluation = load(evaluation_path)
        assert audit["state"] == "finished"
        assert audit["return_code"] == 0 and not audit["timed_out"]
        assert audit["participant_unchanged"]
        assert evaluation["calibration_sha256"] == digest(CONCEPT / "evaluator/hidden/calibration.json")
        entries.append({
            "attempt": attempt,
            "model": audit["model"],
            "elapsed_seconds": audit["elapsed_seconds"],
            "return_code": audit["return_code"],
            "timed_out": audit["timed_out"],
            "participant_unchanged": audit["participant_unchanged"],
            "summary": evaluation["summary"],
            "report": str(evaluation_path.relative_to(CONCEPT)),
            "report_sha256": digest(evaluation_path),
            "audit": str(audit_path.relative_to(CONCEPT)),
            "audit_sha256": digest(audit_path),
        })
    best = max((entry for entry in entries if entry["summary"]["passed"]),
               key=lambda entry: entry["summary"]["score"])
    assert best["attempt"] == "v_4"
    archive = CONCEPT / "generations/generation_1"
    champion = CONCEPT / "champions/generation_2"
    assert not archive.exists() and not champion.exists()
    submission = CONCEPT / "attempts" / best["attempt"]
    source_manifest = manifest(submission)
    champion.mkdir(parents=True)
    shutil.copytree(submission, champion / "submission")
    assert manifest(champion / "submission") == source_manifest
    write_json(champion / "manifest.json", {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_attempt": "attempts/v_4",
        "solved_target_generation": 1,
        "source_files": source_manifest,
        "evaluation": best,
        "copy_is_byte_identical": True,
    })
    status.update({
        "status": "solved",
        "fresh_agent_scores": entries,
        "passing_solution_known": True,
        "solvability": "demonstrated_for_generation_1_by_v_4",
        "hardness_claimed": False,
        "hardness_retained": False,
        "champion_generations": 2,
        "champion": {
            "artifact_generation": 2,
            "solved_target_generation": 1,
            "attempt": "v_4",
            "score": best["summary"]["score"],
            "directory": "champions/generation_2",
            "submission": "champions/generation_2/submission",
            "manifest_sha256": digest(champion / "manifest.json"),
        },
        "generation_one_assessment": {
            "v_3_quality_thresholds_met": True,
            "v_3_invalid_short_outputs": 2,
            "v_3_long_outputs_valid_at_quality_one": 8,
            "v_3_resource_failures_are_not_scientific_hardness_evidence": True,
            "v_4_passes_full_frozen_target": True,
            "next_action": "private scientific residual-failure search before any new ratchet",
        },
    })
    write_json(status_path, status)
    archive.mkdir(parents=True)
    for directory in ("participant", "evaluator"):
        shutil.copytree(CONCEPT / directory, archive / directory)
    shutil.copy2(status_path, archive / "status.json")
    shutil.copy2(CONCEPT / status["freeze_manifest"], archive / "launch_freeze.json")
    shutil.copy2(CONCEPT / "adversary/calibration_validation.json", archive / "calibration_validation.json")
    write_json(archive / "audit_references.json", {
        "generation": 1,
        "attempts": entries,
        "calibration_sha256": digest(CONCEPT / "evaluator/hidden/calibration.json"),
        "freeze_sha256": digest(CONCEPT / status["freeze_manifest"]),
        "freeze_utc": freeze.get("frozen_utc", freeze.get("created_utc")),
        "infrastructure_revision": 5,
        "no_quality_or_resource_target_changed_after_launch": True,
    })
    complete_frozen_inputs(archive)
    print(json.dumps({"status": "solved", "generation": 1,
                      "champion": "v_4", "score": best["summary"]["score"],
                      "archive": str(archive), "champion_files": len(source_manifest)}))


if __name__ == "__main__":
    main()
