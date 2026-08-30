from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_1"
PORTFOLIO = CONCEPT / "adversary/ratchet_2_portfolio"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(directory, include_cache=True):
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("Unexpected source symlink: " + str(path))
        if path.is_file() and (include_cache or "__pycache__" not in path.parts):
            result[str(path.relative_to(directory))] = digest(path)
    return result


def main():
    grade_path = PORTFOLIO / "v3_evaluation.json"
    grade = json.loads(grade_path.read_text())
    freeze_path = CONCEPT / "adversary/ratchet_2_admission/freeze_manifest.json"
    freeze = json.loads(freeze_path.read_text())
    audit_path = CONCEPT / "attempts/v_3_audit/audit.json"
    audit = json.loads(audit_path.read_text())
    source = CONCEPT / "attempts/v_3"
    assert grade["calibration_sha256"] == freeze["calibration_sha256"]
    assert grade["summary"]["passed"] and grade["summary"]["all_valid"]
    assert audit["state"] == "finished" and audit["participant_unchanged"]
    assert not audit["timed_out"] and audit["return_code"] == 0
    assert datetime.fromisoformat(audit["finished_utc"]) < datetime.fromisoformat(freeze["frozen_utc"])
    assert manifest(source, include_cache=False) == audit["submission_files"]
    for name, expected in freeze["frozen_private_assets"].items():
        assert digest(CONCEPT / name) == expected, name
    snapshot = PORTFOLIO / "passing_submission"
    if not snapshot.exists():
        shutil.copytree(source, snapshot)
    assert manifest(snapshot) == manifest(source)
    proof = {
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Full resource-feasible achievability evidence for the frozen generation-2 target",
        "passing_solution_known": True,
        "source": "Unchanged historical fresh submission concept_1/attempts/v_3, completed on generation 1",
        "source_predates_frozen_target": True,
        "source_original_completion_utc": audit["finished_utc"],
        "source_original_audit_sha256": digest(audit_path),
        "source_unchanged_since_original_attempt": True,
        "snapshot": str(snapshot.relative_to(CONCEPT)),
        "snapshot_sha256": manifest(snapshot),
        "calibration_sha256": freeze["calibration_sha256"],
        "freeze_manifest_sha256": digest(freeze_path),
        "evaluation": str(grade_path.relative_to(CONCEPT)),
        "evaluation_sha256": digest(grade_path),
        "summary": grade["summary"],
        "case_count": len(grade["cases"]),
        "stage_count": sum(len(case["stages"]) for case in grade["cases"]),
        "claim_scope": "A solver, not merely stored reference states, passes all fixed quality and resource gates on the admitted suite.",
        "not_a_current_fresh_attempt": True,
        "not_released_to_current_challengers": True,
        "does_not_prove": ["Exact ground energies", "Global optimality", "Hardness of current fresh attempts before their evaluation"],
    }
    (PORTFOLIO / "ACHIEVABILITY.json").write_text(json.dumps(proof, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"snapshot_files": len(proof["snapshot_sha256"]), "summary": proof["summary"]}, indent=2))


if __name__ == "__main__":
    main()
