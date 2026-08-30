import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_3"


def read(relative):
    return json.loads((CONCEPT / relative).read_text())


def summarize(report):
    return {key: report[key] for key in (
        "core_score", "worst_family_score", "runtime_seconds"
    )}


def main():
    fresh = read("attempts/v_1.evaluation.json")
    run = read("attempts/logs/v_1.run.json")
    assert run["state"] == "finished" and run["participant_unchanged"]
    assert fresh["valid"] and fresh["passed"]
    static = read("evaluator/hidden/static_validation_report.json")
    process = read("evaluator/hidden/process_validation_report.json")
    assert static["all_passed"] and process["all_passed"]
    baseline = read("evaluator/hidden/baseline_heldout_report.json")
    source = CONCEPT / "champions/generation_1/solve.py"
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    names = ("broad_0", "broad_1", "primary", "calibration", "low_information")
    reports = {
        name: read(f"adversary/champion_v1/final_{name}_report.json")
        for name in names
    }
    assert all(report["submission_sha256"]["solve.py"] == source_hash
               for report in reports.values())
    broad_passes = all(
        reports[name]["core_score"] >= 90
        and reports[name]["worst_family_score"] >= 85
        and reports[name]["runtime_seconds"] <= 120
        for name in ("broad_0", "broad_1")
    )
    conditional_passes = all(
        reports[name]["worst_family_score"] >= 85
        for name in ("primary", "calibration", "low_information")
    )
    assert broad_passes and conditional_passes
    audit = {
        "date": "2026-08-28",
        "champion": "champions/generation_1",
        "solve_sha256": source_hash,
        "earlier_snapshot": {
            "generated_cases": 2304,
            "evaluated_cases": 352,
            "not_final_champion_evidence": True,
            "report": "champion_v1/search_report.json",
            "finding": "Marginal multiband and calibration weaknesses required final-code confirmation."
        },
        "final_champion": {
            "evaluated_cases": 448,
            "balanced_iid_cases": 384,
            "independent_conditional_confirmation_cases": 64,
            "reports": {name: summarize(report) for name, report in reports.items()},
            "balanced_batch_target_violations": 0,
            "conditional_family_threshold_violations": 0,
            "calibration_caveat": "The 17/24 conditional coverage observation has an interval containing nominal 80%; no coverage threshold was added."
        },
        "decision": "solved",
        "ratchet_generations": 0,
        "reason": "The actual final champion meets the frozen target and the larger independent audit. No substantial reproducible failure justifies a new generation."
    }
    status = {
        "concept": "Fermionic spectral reconstruction",
        "verification_mode": "D_HIDDEN_PREDICTION",
        "status": "solved",
        "retained_as_hard": False,
        "generation": 1,
        "ratchet_generations": 0,
        "target_frozen_before_attempt": True,
        "target": {"core_score_min": 90, "worst_family_score_min": 85, "wall_seconds": 120},
        "baseline": summarize(baseline),
        "baseline_report": "evaluator/hidden/baseline_heldout_report.json",
        "fresh_agent": {"model": "ultima-alpha", "limit_seconds": 3600},
        "fresh_attempts": 1,
        "fresh_score": {**summarize(fresh), "valid": True, "passed": True},
        "fresh_report": "attempts/v_1.evaluation.json",
        "fresh_run": "attempts/logs/v_1.run.json",
        "evaluator_validated": True,
        "validation_reports": ["evaluator/hidden/static_validation_report.json", "evaluator/hidden/process_validation_report.json"],
        "known_target_passing_solution": True,
        "solvability": "demonstrated by the fresh submission",
        "champion_search_report": "adversary/final_champion_audit.json",
        "champion_search_status": "completed without a substantial final-champion failure",
        "reason": audit["reason"]
    }
    (CONCEPT / "adversary/final_champion_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    (CONCEPT / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps({"concept_3": "solved", "final_champion_audit_cases": 448}))


if __name__ == "__main__":
    main()
