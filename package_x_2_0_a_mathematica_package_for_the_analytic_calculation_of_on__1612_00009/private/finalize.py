import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_01"


def load(path):
    return json.loads(path.read_text())


def write(path, payload):
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def main():
    attempt = CONCEPT / "attempts/v_01/fresh_02"
    runtime = load(attempt / "runtime.json")
    grade = load(attempt / "evaluation.json")
    reference = load(CONCEPT / "evaluator/reference_score_final.json")
    verification = load(CONCEPT / "evaluator/reference_verification.json")
    baseline = load(CONCEPT / "evaluator/baseline_score.json")
    excluded_runtime = load(CONCEPT / "attempts/v_01/fresh_01/runtime.json")
    assert runtime["returncode"] == 0 and not runtime["timed_out"] and runtime["participant_unchanged"]
    assert runtime["model"] == "ultima-alpha"
    assert reference["core_score"] == 1 and reference["evidence_score"] == 1 and verification["passed"]
    assert grade["core_score"] >= 0.90
    valid_attempt = {
        "attempt": "fresh_02", "model": runtime["model"], "reasoning_effort": runtime["reasoning_effort"],
        "runtime_seconds": runtime["runtime_seconds"], "time_limit_seconds": 3600,
        "valid_hardness_attempt": True, "timed_out": False,
        "core_score": grade["core_score"], "overall_score": grade["overall_score"],
        "per_family": grade["per_family"], "resource_metrics": grade["resource_metrics"],
        "evidence_score": grade["evidence_score"], "classification": "too_easy",
        "scientific_failure": False, "participant_unchanged": True,
        "transcript": "attempts/v_01/fresh_02/transcript.txt", "evaluation": "attempts/v_01/fresh_02/evaluation.json"
    }
    failure_classification = {
        "classification": "too_easy", "valid_hardness_attempt": True,
        "failure_type": "none_scientific_work_succeeded", "core_score": grade["core_score"],
        "minimum_family_score": grade["minimum_family_score"], "timeout": False,
        "main_capability": "Constructed and validated the standard hybrid analytic-Laurent and causal-parameter-integration solution",
        "decision": "reject_without_tightening_or_redesign", "audit": "../../../../private/decision.md"
    }
    write(attempt / "failure_classification.json", failure_classification)
    concept_status = {
        "status": "rejected", "reason": "fresh_agent_core_score_at_least_0_90",
        "concept": "Weighted-integral matching and subtraction release audit",
        "archetype": "A: workspace diagnosis, repair, and performance validation",
        "participant_version": "v_01", "participant_task_directory": str(CONCEPT / "participant/v_01"),
        "reference_core_score": reference["core_score"], "reference_score": reference["overall_score"],
        "reference_evidence_score": reference["evidence_score"], "reference_resource_metrics": reference["resource_metrics"],
        "reference_verification": "evaluator/reference_verification.json",
        "weak_baseline_core_score": baseline["core_score"],
        "fundamental_redesigns": 0, "built_concepts": 1, "valid_fresh_attempts": [valid_attempt],
        "excluded_launches": [{"attempt": "fresh_01", "model_requested": "ultima-alpha",
                               "runtime_seconds": excluded_runtime["runtime_seconds"], "core_score": None,
                               "reason": "stdin_blocked_before_scientific_model_work"}],
        "scientific_tests_changed_after_screening": False,
        "grader_compatibility_repairs": "Declared baseline runners, additional claim tables, and direct-comparison figure source data are behaviorally rerun and checked",
        "empirical_hardness_claim": False
    }
    write(CONCEPT / "status.json", concept_status)
    status = {
        "paper": "Package-X 2.0: A Mathematica package for the analytic calculation of one-loop integrals",
        "arxiv_id": "1612.00009", "status": "rejected", "reason": "paper_did_not_yield_frontier_hard_task",
        "selected_concept": None, "screened_concept": "concept_01",
        "screened_task_name": concept_status["concept"], "archetype": concept_status["archetype"],
        "central_contributions": ["weighted four-point tensor coefficients", "even-dimensional and UV/IR Laurent processing",
                                  "nonsingular multivariate Taylor coefficients", "causal numerical evaluation at real kinematics"],
        "participant_task_directory": concept_status["participant_task_directory"],
        "reference_core_score": reference["core_score"], "reference_score": reference["overall_score"],
        "fresh_attempts": [valid_attempt], "excluded_launches": concept_status["excluded_launches"],
        "redesign_occurred": False, "built_concepts": 1, "concepts_considered": 5,
        "remaining_candidates": "Four alternatives rejected at prerequisite source/shortcut gates; no second eligible pilot",
        "decision_record": "private/decision.md", "candidate_record": "private/concepts.md",
        "shortcut": "A standard hybrid of parameter-moment quadrature with causal deformation, analytic Laurent/Taylor processing, and known infrared formulas solved every hidden family"
    }
    write(ROOT / "status.json", status)
    print(json.dumps({key: value for key, value in status.items() if key not in ("fresh_attempts", "excluded_launches")}, indent=2))
    print(json.dumps(valid_attempt, indent=2))


if __name__ == "__main__":
    main()
