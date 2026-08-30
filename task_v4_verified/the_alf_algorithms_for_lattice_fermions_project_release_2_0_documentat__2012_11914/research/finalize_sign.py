import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "concept_1"


def read(relative):
    return json.loads((ROOT / relative).read_text())


def main():
    fresh = read("attempts/v_3.evaluation.json")
    run = read("attempts/logs/v_3.run.json")
    audit = read("adversary/fresh_v3_saved_candidates/report.json")
    private = read("adversary/negative_continuation_deep_search_report.json")
    assert run["state"] == "finished" and run["participant_unchanged"]
    assert fresh["valid"] and not fresh["passed"]
    assert audit["passing_saved_witnesses"] == 0 and audit["all_precision_checks_agreed"]
    assert private["requested_beta"] == 0.75 and not private["requested_target_found"]
    snapshot = ROOT / "adversary/generations/generation_2_clean/participant"
    public = ROOT / "participant"
    for relative, expected in run["participant_sha256"].items():
        assert hashlib.sha256((snapshot / relative).read_bytes()).hexdigest() == expected
        assert hashlib.sha256((public / relative).read_bytes()).hexdigest() == expected
    status = {
        "concept": "Robust rare-sign Hubbard counterexample",
        "verification_mode": "B_COUNTEREXAMPLE_OR_FALSIFICATION",
        "status": "hard_open_candidate",
        "retained_as_hard": True,
        "generation": 2,
        "ratchet_generations": 1,
        "target_frozen_before_attempt": True,
        "target": {"beta": 0.75, "core_score": 1.0, "worst_family_score": 1.0},
        "baseline": {"core_score": 0.0, "worst_family_score": 0.0, "passed": False},
        "baseline_report": "adversary/baseline_code_score_generation2.json",
        "previous_champion": {"task_generation": 1, "beta": 1.6, "core_score": 1.0, "worst_family_score": 1.0, "passed": True},
        "previous_champion_report": "attempts/v_1.evaluation.json",
        "fresh_agent": {"model": "ultima-alpha", "limit_seconds": 3600},
        "qualified_fresh_attempt": "v_3",
        "fresh_score": {key: fresh[key] for key in ("core_score", "worst_family_score", "valid", "passed", "reason", "runtime_seconds")},
        "fresh_report": "attempts/v_3.evaluation.json",
        "fresh_run": "attempts/logs/v_3.run.json",
        "assisted_control_excluded_from_clean_evidence": "v_2",
        "qualification_report": "attempts/logs/v_3.qualification.json",
        "saved_candidate_audit": "adversary/fresh_v3_saved_candidates/report.json",
        "saved_candidate_audit_summary": {key: audit[key] for key in ("unique_valid_discrete_candidates", "nominally_negative_candidates", "passing_saved_witnesses")},
        "evaluator_validated": True,
        "validation_report": "adversary/evaluator_validation.json",
        "known_target_passing_solution": False,
        "solvability": "unknown at beta=0.75; no nonexistence proof",
        "closest_privileged_verified_beta": 0.786,
        "closest_privileged_report": "adversary/privileged_beta0_786_independent_score.json",
        "closest_control_is_target_solution": False,
        "adversarial_search": {
            "static_parameter_cases": 1632,
            "old_witness_failures": 1533,
            "deep_search_report": "adversary/negative_continuation_deep_search_report.json",
            "fixed_target_unchanged_after_fresh_launch": True
        },
        "failed_capability": "Search for correlated discrete auxiliary fields producing a robust two-flavor negative determinant in the higher-temperature regime; the submitted fields give precision-stable positive weights at all three points.",
        "reason": "A clean one-hour fresh attempt fails the physical witness condition, not the artifact interface. Independent private searches also have no certified target witness."
    }
    (ROOT / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps({"concept_1": status["status"], "saved_candidates_checked": audit["unique_valid_discrete_candidates"]}))


if __name__ == "__main__":
    main()
