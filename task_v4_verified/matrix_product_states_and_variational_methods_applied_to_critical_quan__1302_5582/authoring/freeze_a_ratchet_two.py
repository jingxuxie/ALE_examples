from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    calibration_path = CONCEPT / "evaluator/hidden/calibration.json"
    calibration = json.loads(calibration_path.read_text())
    validation = json.loads((CONCEPT / "adversary/calibration_validation.json").read_text())
    scoring = json.loads((CONCEPT / "participant/input/scoring.json").read_text())
    prepared = json.loads((CONCEPT / "adversary/ratchet_2_admission/public_preparation.json").read_text())
    infrastructure = json.loads((CONCEPT / "adversary/wall_guard_repair/freeze_manifest_v5.json").read_text())
    assert calibration["generation"] == 2 and calibration["infrastructure_revision"] == 5
    assert calibration["full_passing_algorithm_known_at_admission"] is False
    assert prepared["generation"] == 2
    assert validation["valid"] and validation["case_count"] == 8 and validation["states_checked"] == 24
    assert validation["calibration_sha256"] == digest(calibration_path)
    assert prepared["target_predeclared"] == scoring["target"] == calibration["target_frozen_before_launch"]
    assert not validation["baseline_summary"]["passed"]
    assert infrastructure["checks_passed"] == 15
    for relative, expected in calibration["frozen_hashes"].items():
        assert digest(CONCEPT / relative) == expected, relative
    public = {}
    for path in (CONCEPT / "participant").rglob("*"):
        assert not path.is_symlink(), path
        assert path.name != "__pycache__" and path.suffix != ".pyc", path
        if path.is_file():
            public[str(path.relative_to(CONCEPT))] = digest(path)
    for attempt in ("v_5", "v_6"):
        assert not (CONCEPT / "attempts" / attempt).exists(), "fresh output must not be precreated"
    manifest = {"generation": 2, "frozen_utc": datetime.now(timezone.utc).isoformat(),
                "participant_sha256": public, "frozen_private_assets": calibration["frozen_hashes"],
                "calibration_sha256": digest(calibration_path),
                "target": scoring["target"], "target_predeclared": True,
                "baseline_summary": validation["baseline_summary"],
                "model": "ultima-alpha", "reasoning_effort": "high", "fresh_limit_seconds": 3600,
                "planned_fresh_attempts": ["v_5", "v_6"], "fresh_attempts_launched": 0,
                "infrastructure_revision": 5, "passing_solution_known": False,
                "runner_sha256": digest(ROOT.parents[1] / "run_allowlisted_codex.sh"),
                "harness_sha256": digest(ROOT / "authoring/tournament.py"),
                "freeze_builder_sha256": digest(Path(__file__))}
    relative = "adversary/ratchet_2_admission/freeze_manifest.json"
    assert not (CONCEPT / relative).exists(), "launch freeze must not be overwritten"
    previous = json.loads((CONCEPT / "status.json").read_text())
    assert previous["generation"] == 1 and previous["status"] == "solved"
    archived = CONCEPT / "generations/generation_1/status.json"
    assert digest(archived) == digest(CONCEPT / "status.json")
    (CONCEPT / relative).write_text(json.dumps(manifest, indent=2) + "\n")
    status = {"concept": "concept_1", "name": "Robust variational field states in fixed parity sectors",
              "primary_verification_mode": "A_baseline_improvement", "status": "frozen_ready",
              "generation": 2, "ratchet_generations": 2, "champion_generations": 2,
              "evaluator_validated": True, "validation_report": "adversary/calibration_validation.json",
              "infrastructure_revision": 5, "freeze_manifest": relative,
              "baseline": validation["baseline_summary"], "target": scoring["target"],
              "target_frozen_before_fresh_attempt": True, "passing_solution_known": False,
              "solvability": "unknown_for_resource_feasible_solver", "reference_states_attainable": True,
              "reference_states_are_exact_ground_energies": False, "fresh_agent_scores": [],
              "hardness_claimed": False, "generation_zero_archive": "generations/generation_0/",
              "generation_one_archive": "generations/generation_1/",
              "previous_champion": previous["champion"],
              "private_passing_solver_assessment": "not yet graded on this frozen target"}
    (CONCEPT / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps({"frozen": True, "generation": 2, "public_files": len(public),
                      "calibration_sha256": manifest["calibration_sha256"],
                      "baseline": manifest["baseline_summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
