import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_2"


def load(relative):
    return json.loads((CONCEPT / relative).read_text())


def score_record(relative):
    score = load(relative)
    keys = ("core_score", "worst_family_score", "runtime_score", "runtime_seconds",
            "valid", "passed", "reason")
    return {**{key: score[key] for key in keys if key in score}, "report": relative}


def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    attempts = []
    for generation, replicate in ((1, 1), (2, 1), (2, 2), (3, 1), (3, 2)):
        label = "v_" + str(generation) + ("_r2" if replicate == 2 else "")
        prefix = "attempts/" + label
        launch = load(prefix + ".launch.json")
        finished = load(prefix + ".exit.json")
        score = score_record(prefix + ".evaluation.json")
        participant = CONCEPT / "participant" if generation == 3 else CONCEPT / "champions" / ("generation_" + str(generation)) / "participant"
        mismatches = []
        for relative, expected in launch["participant_sha256"].items():
            artifact = participant / relative
            if not artifact.is_file() or hashlib.sha256(artifact.read_bytes()).hexdigest() != expected:
                mismatches.append(relative)
        if mismatches:
            raise RuntimeError("participant provenance mismatch: " + label + " " + str(mismatches))
        design = CONCEPT / prefix / "design.json"
        if not design.is_file() or design.is_symlink():
            raise RuntimeError("invalid final artifact: " + label)
        deadline = datetime.datetime.fromisoformat(launch["started_utc"]).timestamp() + 3600
        if design.stat().st_mtime > deadline:
            raise RuntimeError("artifact was written after deadline: " + label)
        if finished["returncode"] != 0 or finished["timed_out"]:
            raise RuntimeError("unexpected infrastructure or timeout ambiguity: " + label)
        attempts.append({"generation": generation, "replicate": replicate,
                         "model": launch["model"], "effort": launch["effort"],
                         "limit_seconds": launch["limit_seconds"],
                         "wall_seconds": finished["wall_seconds"],
                         "submission": prefix, "score": score,
                         "status": "solved" if score["passed"] else "failed",
                         "participant_hashes_verified": True,
                         "artifact_written_before_deadline": True,
                         "artifact_sha256": hashlib.sha256(design.read_bytes()).hexdigest()})
    current = [attempt for attempt in attempts if attempt["generation"] == 3]
    witness = score_record("evaluator/hidden/feasible_score.json")
    if any(attempt["score"]["passed"] for attempt in current) or not witness["passed"]:
        raise RuntimeError("spectral hardness conditions no longer hold")
    proposal = load("adversary/ratchet_2/proposal/freeze.json")
    state = {
        "concept": "spectral_fingerprint_construction",
        "verification_mode": "C_WITNESS_OR_DESIGN_CONSTRUCTION",
        "status": "hard_verified_achievable",
        "final_status": "hard_verified_achievable",
        "valid": True, "retained": True, "phase": "complete",
        "updated_utc": now, "generation": 3, "task_generations": 3,
        "ratchet_generations": 2, "fresh_model_sessions_run": len(attempts),
        "frozen_target": {"core_score_min": 0.96, "worst_family_min": 0.94},
        "baseline": score_record("evaluator/hidden/baseline_score.json"),
        "baseline_entrypoint": "participant/baseline/solve.py",
        "privileged_witness": {**witness, "artifact": "evaluator/hidden/feasible_design/design.json"},
        "solvability": "demonstrated by a fabrication-feasible private design, independently rescored in less than one second",
        "fresh_attempts": attempts,
        "generation_history": [
            {"generation": 1, "status": "solved", "baseline": score_record("champions/generation_1/evaluator/hidden/baseline_score.json"),
             "champion": "champions/generation_1", "ratchet_report": "adversary/ratchet_1/REPORT.md"},
            {"generation": 2, "status": "solved", "baseline": score_record("champions/generation_2/evaluator/hidden/baseline_score.json"),
             "champion": "champions/generation_2", "ratchet_report": "adversary/ratchet_2/REPORT.md"},
            {"generation": 3, "status": "hard_verified_achievable", "fresh_replicates": 2}
        ],
        "counterexample_search": {
            "ratchet_1": {"physical_cases": 15, "optimizer_runs": 62,
                          "selected_best_valid_core": 0.0699874138,
                          "selected_best_valid_worst": 0.0585719239,
                          "report": "adversary/ratchet_1/REPORT.md"},
            "ratchet_2": {"physical_cases_including_controls": 19,
                          "full_strength_continuation_seeds": 48,
                          "stages_per_seed": 6, "auxiliary_fits": 24,
                          "full_strength_function_evaluations": 71948,
                          "full_strength_cpu_seconds": 60341.10,
                          "passing_full_strength_runs": 0,
                          "best_valid_champion_score": proposal["measured_evidence"]["best_valid"],
                          "report": "adversary/ratchet_2/REPORT.md",
                          "incomplete_screen_not_counted_as_failure": True}
        },
        "evaluator_validation": "evaluator/hidden/validation.json",
        "integrity_audit": "attempts/final_audit.json",
        "failure_capability": "Global binary inverse spectral design under an exact normal-material budget and connected-superconductor constraint; local relaxed fits and their binary projections fail to reproduce interacting many-inclusion resonances across all three public conditions.",
        "decision_basis": "Both independent one-hour ultima-alpha sessions completed normally with fabrication-valid outputs but core scores below 0.58 and worst-condition scores below 0.54, versus fixed 0.96/0.94 goals; private witness scores essentially 1/1.",
        "limits": ["This is empirical finite-budget hardness, not a complexity or impossibility proof.",
                   "Feasibility of a design does not establish a fast general inverse-design algorithm.",
                   "The prescribed-gap lattice BdG surrogate is not a self-consistent native SuperConga result."]
    }
    audit = {"completed_utc": now, "all_five_launch_hash_sets_verified": True,
             "all_five_artifacts_written_before_deadline": True,
             "all_five_fresh_sessions_exited_normally": True,
             "final_two_attempts_valid_but_below_target": True,
             "private_witness_passed": True,
             "attempts": attempts}
    (CONCEPT / "attempts" / "final_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    (CONCEPT / "status.json").write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps({"status": state["status"], "fresh_scores": [entry["score"] for entry in current]}, indent=2))


if __name__ == "__main__":
    main()
