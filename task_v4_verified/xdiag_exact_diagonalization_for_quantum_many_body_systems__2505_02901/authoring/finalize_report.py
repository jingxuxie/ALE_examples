import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text())


def write(relative, payload):
    (ROOT / relative).write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def score(relative):
    record = load(relative)
    fields = (
        "core_score", "worst_family_score", "minimum_column_fidelity",
        "resource_score", "runtime_score", "valid", "passed", "reason",
    )
    return {"report": relative, **{key: record[key] for key in fields if key in record}}


def attempt(package, name, report_name=None):
    run_path = f"{package}/attempts/{name}.run.json"
    run = load(run_path)
    assert run.get("ended_at") and run.get("elapsed_seconds") is not None, run_path
    assert run["model"] == "ultima-alpha"
    assert run["output_initially_empty"] and run["participant_read_only"]
    report_path = f"{package}/attempts/{report_name or name + '.score.json'}"
    return {
        "attempt": name,
        "package": package,
        "model": run["model"],
        "elapsed_seconds": run["elapsed_seconds"],
        "timed_out": run["timed_out"],
        "run_record": run_path,
        **score(report_path),
    }


def finalize_fleet():
    current = load("concept_1/generations/generation_1/status.json")
    original = load("concept_1/status.json")
    search = load("concept_1/adversary/champion_audit_summary.json")
    first = attempt("concept_1", "v_1", "v_1.repaired_evaluation.json")
    second = attempt("concept_1/generations/generation_1", "v_1")
    champion = load("concept_1/champions/generation_1/repaired_evaluation.json")
    assert first["passed"] and second["passed"] and champion["passed"]
    assert not search["genuine_failure_found"] and not search["ratchet_recommended"]
    assert search["incomplete_reason"] is None
    assert search["counters"]["stress_fleets_evaluated"] == 12
    assert search["counters"]["protocol_resource_or_audit_errors"] == 0
    assert (ROOT / "concept_1/champions/generation_1/solve.py").read_bytes() == (ROOT / "concept_1/attempts/v_1/solve.py").read_bytes()
    assert max(first["core_score"], second["core_score"]) <= champion["core_score"] + 1e-8
    assert max(first["worst_family_score"], second["worst_family_score"]) <= champion["worst_family_score"] + 1e-8
    archive = "concept_1/adversary/invalid_original_generation_status.json"
    if not (ROOT / archive).exists():
        assert original["status"] == "invalid"
        write(archive, original)
    write("concept_1/champions/generation_1/score.json", champion)
    decision = {
        "status": "solved",
        "solvability": "demonstrated",
        "retained_as_hard": False,
        "tournament_complete": True,
        "evaluator_validated": True,
        "ratchet_generations": 0,
        "repair_generations": 1,
        "fresh_attempts": [first, second],
        "reason": (
            "Both observed fresh solvers meet the repaired, predeclared 2.5% core / "
            "1% worst-family improvement targets with identical scores. The best "
            "champion has no substantiated failure in the bounded private audit. "
            "The original infeasible 6%/3% target is invalid and is not hardness evidence."
        ),
        "champion_core_score": champion["core_score"],
        "champion_worst_family_score": champion["worst_family_score"],
    }
    current.update(decision)
    current["champion"] = "../../champions/generation_1"
    current["champion_audit"] = "../../adversary/champion_audit_summary.json"
    write("concept_1/generations/generation_1/status.json", current)
    original.update(decision)
    original.update({
        "status_scope": "The current repaired generation, not the invalid original participant contract",
        "target": current["target"],
        "current_generation": "generations/generation_1",
        "current_generation_status": "solved",
        "current_participant_task": "generations/generation_1/participant/TASK.md",
        "original_generation_status": "invalid",
        "original_generation_record": "adversary/invalid_original_generation_status.json",
        "champion": "champions/generation_1",
        "champion_audit": "adversary/champion_audit_summary.json",
    })
    write("concept_1/status.json", original)


def pair(record, percent=False):
    suffix = "%" if percent else ""
    return f"{record['core_score']:.6f}{suffix} / {record['worst_family_score']:.6f}{suffix}"


def markdown_report(report):
    fleet, pulse, spectroscopy = report["concepts"]
    lines = [
        "# Empirical hardness report", "",
        "Scores are core / worst-family. Fleet scores are percentage loss reductions; pulse and spectroscopy scores are in [0,1].", "",
        "## Concepts and scores", "",
        "### A — Adaptive symmetry diagnostic fleet",
        "- Baseline: 0% / 0%; repaired fixed target: 2.5% / 1%.",
        f"- Both fresh attempts and the champion: {pair(fleet['current_champion'], True)}.",
        "- Final status: `solved`; solvability demonstrated. The original 6% / 3% contract was invalidated, not retained as hard.", "",
        "### C — Calibration-aware coherent many-body pulse compilation",
        f"- Weak baseline: {pair(pulse['baseline'])}.",
        f"- Private passing witness: {pair(pulse['privileged_witness'])}; fixed target: 0.999995 / 0.999990, with minimum-column fidelity at least 0.999990.",
        f"- Fresh v1: {pair(pulse['fresh_attempts'][0])}; fresh v2: {pair(pulse['fresh_attempts'][1])}. Both artifacts satisfy hardware constraints but fail accuracy.",
        "- Final status: `hard_verified_achievable`; solvability demonstrated by the private witness.", "",
        "### E — Shot-budgeted active spin spectroscopy",
        f"- Original baseline: {pair(spectroscopy['original_baseline'])}; ratchet champion-baseline: {pair(spectroscopy['current_champion_baseline'])}.",
        f"- Initial fresh v1: {pair(spectroscopy['fresh_attempts'][0])}; initial fresh v2: {pair(spectroscopy['fresh_attempts'][1])}.",
        f"- Ratchet fresh attempt / current champion: {pair(spectroscopy['current_champion'])}; fixed target: 0.970000 / 0.950000.",
        "- Final status: `solved`; solvability demonstrated.", "",
        "## Counterexample searches", "",
        "- Fleet: a guarded relaxation disproves the original 6% / 3% target. After repair, 12 private stress fleets and two equivalent-order variants produce no substantiated champion failure; relaxation gaps alone are not treated as feasible improvements.",
        "- Pulse: 49 saved numeric pulse artifacts produce no valid witness. The checker rejects 17 invalid-artifact cases, independently validated propagation agrees, and the private positive witness passes.",
        "- Spectroscopy: a 48-case private stress space exposes the initial champion at three configurations while total shots remain fixed. A fresh agent solves that ratchet; the new champion also passes the prospective two-configuration audit.", "",
        "## Ratchets and final decision", "",
        "- Champion-ratchet generations: fleet 0; pulse 0; spectroscopy 1. Fleet also has one separate contract-repair generation.",
        "- Seven isolated `ultima-alpha` attempts, each limited to one hour, are complete and scored.",
        "- Retained task: `concept_2/participant/TASK.md`. Final status: `hard_verified_achievable`. Solvability is demonstrated, not unknown.",
        "- Substantive failed capability: " + pulse["substantive_failed_capability"], "",
    ]
    (ROOT / "FINAL_REPORT.md").write_text("\n".join(lines))


def main():
    audit = load("authoring/package_audit.json")
    assert audit["passed"]
    finalize_fleet()
    fleet_status = load("concept_1/status.json")
    pulse_status = load("concept_2/status.json")
    spectroscopy_status = load("concept_3/status.json")
    assert fleet_status["tournament_complete"]
    assert pulse_status["status"] == "hard_verified_achievable"
    assert spectroscopy_status["status"] == "solved"
    fleet_package = "concept_1/generations/generation_1"
    spectroscopy_package = "concept_3/generations/generation_1"
    fleet_attempts = [
        attempt("concept_1", "v_1", "v_1.repaired_evaluation.json"),
        attempt(fleet_package, "v_1"),
    ]
    fleet_attempts[0]["contract_note"] = (
        "This solver was constructed under the subsequently invalidated, stricter "
        "6%/3% target. The physics, hidden cases, baseline, executable interface, and "
        "resource limits are identical in the repaired 2.5%/1% task. Its passing "
        "behavior on that same objective counts conservatively as a solved concept."
    )
    pulse_attempts = [attempt("concept_2", name) for name in ("v_1", "v_2")]
    spectroscopy_attempts = [attempt("concept_3", name) for name in ("v_1", "v_2")]
    spectroscopy_attempts.append(attempt(spectroscopy_package, "v_1"))
    fleet_search = load("concept_1/adversary/champion_audit_summary.json")
    pulse_decision = load("concept_2/adversary/hardness_decision.json")
    concepts = [
        {
            "concept": "concept_1",
            "name": "Adaptive symmetry diagnostic fleet",
            "verification_mode": "A_BASELINE_IMPROVEMENT",
            "current_package": fleet_package,
            "score_units": "Percent reduction of minimax Bayes loss relative to the supplied baseline",
            "fixed_target": {"core_score_min": 2.5, "worst_family_score_min": 1.0},
            "baseline": {"core_score": 0.0, "worst_family_score": 0.0, "report": "concept_1/evaluator/hidden/baseline.json"},
            "private_portfolio": score("concept_1/adversary/portfolio_score.json"),
            "current_champion": score("concept_1/champions/generation_1/score.json"),
            "fresh_attempts": fleet_attempts,
            "counterexample_search": fleet_search,
            "original_contract": {
                "status": "invalid",
                "target_core_percent": 6.0,
                "target_worst_family_percent": 3.0,
                "reason": "A guarded Bayes-tree relaxation proves those targets infeasible",
                "certificate": "concept_1/adversary/relaxed_bound.json",
                "core_improvement_upper_bound_percent": load("concept_1/adversary/relaxed_bound.json")["core_improvement_upper_bound_percent"],
                "worst_family_improvement_upper_bound_percent": load("concept_1/adversary/relaxed_bound.json")["worst_family_improvement_upper_bound_percent"],
                "repair_provenance": f"{fleet_package}/adversary/contract_repair.json",
                "counted_as_agent_hardness": False,
            },
            "ratchet_generations": fleet_status["ratchet_generations"],
            "repair_generations": 1,
            "status": fleet_status["status"],
            "solvability": fleet_status["solvability"],
            "retained_as_hard": fleet_status["retained_as_hard"],
        },
        {
            "concept": "concept_2",
            "name": "Calibration-aware coherent many-body pulse compilation",
            "verification_mode": "C_WITNESS_DESIGN_CONSTRUCTION",
            "current_package": "concept_2",
            "score_units": "Coherent isometry fidelity / certified worst-superposition fidelity, in [0,1]",
            "fixed_target": pulse_status["fixed_targets"],
            "baseline": score("concept_2/adversary/baseline_parent_check.json"),
            "privileged_witness": score("concept_2/adversary/witness_report.json"),
            "fresh_attempts": pulse_attempts,
            "counterexample_search": pulse_decision["counterexample_search"],
            "ratchet_generations": 0,
            "repair_generations": 0,
            "status": pulse_status["status"],
            "solvability": pulse_status["solvability"],
            "retained_as_hard": True,
            "substantive_failed_capability": pulse_decision["substantive_failed_capability"],
            "decision_record": "concept_2/adversary/hardness_decision.json",
        },
        {
            "concept": "concept_3",
            "name": "Shot-budgeted active spin spectroscopy",
            "verification_mode": "E_ACTIVE_EXPERIMENT_DESIGN",
            "current_package": spectroscopy_package,
            "score_units": "One minus normalized parameter RMSE; worst-family aggregates use the same scale",
            "fixed_target": {"core_score_min": 0.970, "worst_family_score_min": 0.950},
            "original_baseline": score("concept_3/adversary/baseline_score.json"),
            "current_champion_baseline": score(f"{spectroscopy_package}/adversary/baseline_score.json"),
            "private_portfolio": score(f"{spectroscopy_package}/adversary/portfolio_score.json"),
            "current_champion": score("concept_3/champions/generation_2/score.json"),
            "fresh_attempts": spectroscopy_attempts,
            "counterexample_search": {
                "broad_space": "48 device/noise cases across four physically valid parameter families",
                "failure": "The original champion drops below the fixed core target at three configurations with total shots unchanged",
                "stress_report": "concept_3/adversary/champion_stress_resource_audit.json",
                "ratchet_provenance": f"{spectroscopy_package}/adversary/ratchet_provenance.json",
                "ratchet_outcome": "A completely fresh agent solves the three-configuration task",
                "further_search": "The new champion also passes a two-configuration audit with the same total shots; no additional ratchet is justified by this audit",
                "further_search_report": "concept_3/adversary/generation_2_resource_audit.json",
            },
            "ratchet_generations": 1,
            "repair_generations": 0,
            "status": "solved",
            "solvability": "demonstrated",
            "retained_as_hard": False,
        },
    ]
    report = {
        "session_type": "HARDNESS_DISCOVERY",
        "paper": {"title": "XDiag: Exact Diagonalization for Quantum Many-Body Systems", "arxiv_id": "2505.02901"},
        "concepts_considered": 10,
        "concepts_built": 3,
        "distinct_verification_modes": 3,
        "fresh_attempts": sum(len(concept["fresh_attempts"]) for concept in concepts),
        "fresh_agent_model": "ultima-alpha",
        "fresh_agent_time_limit_seconds": 3600,
        "ratchet_generations": sum(concept["ratchet_generations"] for concept in concepts),
        "repair_generations": 1,
        "concepts": concepts,
        "final_status": "hard_verified_achievable",
        "selected_concept": "concept_2",
        "selected_participant_task": "concept_2/participant/TASK.md",
        "solvability": "demonstrated_by_privileged_witness",
        "package_audit": "authoring/package_audit.json",
        "finalized_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write("final_report.json", report)
    markdown_report(report)
    write("status.json", {
        key: report[key] for key in (
            "session_type", "paper", "concepts_built", "distinct_verification_modes",
            "fresh_attempts", "ratchet_generations", "repair_generations", "final_status",
            "selected_concept", "selected_participant_task", "solvability",
            "package_audit", "finalized_at_utc",
        )
    } | {
        "status": report["final_status"],
        "report": "final_report.json",
        "concepts": [
            {key: concept[key] for key in ("concept", "verification_mode", "current_package", "status", "solvability", "retained_as_hard")}
            for concept in concepts
        ],
    })
    print(json.dumps({"final_status": report["final_status"], "selected_concept": report["selected_concept"], "fresh_attempts": report["fresh_attempts"]}))


if __name__ == "__main__":
    main()
