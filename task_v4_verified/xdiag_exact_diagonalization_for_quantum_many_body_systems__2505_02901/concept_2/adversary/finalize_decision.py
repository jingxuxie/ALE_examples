import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text())


def write(relative, payload):
    (ROOT / relative).write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def main():
    status = load("status.json")
    witness = load("adversary/witness_report.json")
    validation = load("adversary/validation_report.json")
    baseline = load("adversary/baseline_parent_check.json")
    replay = load("adversary/baseline_replay_evaluation.json")
    positive_test = load("adversary/artifact_scanner_positive_test.json")
    negative_test = load("adversary/artifact_scanner_negative_test.json")
    assert witness["passed"] and witness["physical_valid"]
    assert validation["validation_passed"]
    assert len(validation["invalid_artifact_cases_rejected"]) == validation["invalid_artifact_case_count"]
    assert replay["valid"] and not replay["passed"]
    assert abs(replay["core_score"] - baseline["core_score"]) < 1e-12
    assert positive_test["any_valid_witness"]
    assert not negative_test["any_valid_witness"]
    attempts = []
    artifact_count = 0
    metric_keys = (
        "core_score", "worst_family_score", "minimum_column_fidelity",
        "resource_score", "runtime_score", "valid", "passed", "physical_valid",
        "elapsed_seconds", "peak_memory_mib",
    )
    for name in ("v_1", "v_2"):
        audit = load(f"attempts/{name}.score_audit.json")
        run = load(f"attempts/{name}.run.json")
        final = audit["final_submission"]
        assert run["model"] == "ultima-alpha"
        assert run["elapsed_seconds"] <= 3620
        assert not audit["any_valid_witness"] and not final["passed"]
        assert final["physical_valid"] and final["valid"]
        write(f"attempts/{name}.score.json", final)
        artifact_count += audit["unique_artifacts_checked"]
        attempts.append({
            "attempt": name,
            "model": run["model"],
            "construction_elapsed_seconds": run["elapsed_seconds"],
            "timed_out": run["timed_out"],
            "run_record": f"attempts/{name}.run.json",
            "score_record": f"attempts/{name}.score.json",
            "artifact_audit": f"attempts/{name}.score_audit.json",
            "unique_pulse_artifacts_checked": audit["unique_artifacts_checked"],
            "any_valid_witness": audit["any_valid_witness"],
            "scores": {key: final[key] for key in metric_keys},
            "best_saved_artifact_scores": {
                key: audit["best_produced_artifact"][key]
                for key in metric_keys
            },
        })
    decision = {
        "status": "hard_verified_achievable",
        "solvability": "demonstrated_by_privileged_witness",
        "reason": (
            "Both independently isolated fresh agents produced physically admissible "
            "controls but remained far below the fixed coherent-fidelity requirements. "
            "The private generating pulse satisfies every requirement. Checking auxiliary "
            "numeric checkpoints found no overlooked passing witness."
        ),
        "substantive_failed_capability": (
            "Joint inverse synthesis of a hardware-constrained, 72-parameter "
            "noncommuting many-body pulse reproducing coherent six-state register "
            "isometries across four fully disclosed calibrated Hamiltonians."
        ),
        "fixed_targets": status["fixed_targets"],
        "fresh_attempts": attempts,
        "ratchet_generations": 0,
        "repair_generations": 0,
        "counterexample_search": {
            "purpose": "Check that formatting errors or unsubmitted checkpoints do not create false hardness",
            "unique_saved_pulse_artifacts_checked": artifact_count,
            "passing_artifacts": 0,
            "serialization_only": True,
            "known_positive_detected": True,
            "known_negative_rejected": True,
        },
        "validation": {
            "report": "adversary/validation_report.json",
            "private_witness": "evaluator/hidden/witness.json",
            "private_witness_score": "adversary/witness_report.json",
            "baseline_score": "adversary/baseline_parent_check.json",
            "runnable_baseline_replay": "adversary/baseline_replay_evaluation.json",
            "private_witness_core_score": witness["core_score"],
            "private_witness_worst_family_score": witness["worst_family_score"],
            "hidden_calibration_extrapolation": False,
            "fresh_construction_wall_limit_seconds": 3600,
            "construction_memory_note": (
                "The supplied fresh-agent runner hard-limits wall time and isolates files; "
                "construction peak RSS was not separately measured. The verifier separately "
                "enforces its validation budget and checks all pulse hardware constraints. "
                "No hardness claim depends on an unmeasured construction-memory violation."
            ),
        },
        "decided_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write("adversary/hardness_decision.json", decision)
    status.update({
        "status": decision["status"],
        "hardness_status": decision["status"],
        "empirical_hardness_decision": decision["reason"],
        "solvability": decision["solvability"],
        "retained_as_hard": True,
        "evaluator_validated": True,
        "tournament_complete": True,
        "fresh_attempts": attempts,
        "ratchet_generations": 0,
        "repair_generations": 0,
        "decision_record": "adversary/hardness_decision.json",
        "substantive_failed_capability": decision["substantive_failed_capability"],
        "decided_at_utc": decision["decided_at_utc"],
    })
    write("status.json", status)
    print(json.dumps({"status": decision["status"], "fresh_attempts": len(attempts), "pulse_artifacts_checked": artifact_count}))


if __name__ == "__main__":
    main()
