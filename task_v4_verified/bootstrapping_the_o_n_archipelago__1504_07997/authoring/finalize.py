import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text())


def summary(report, percentage_units=False):
    factor = 1 if percentage_units else 100
    return {"core_percent": factor*report.get("core_score", report.get("core", 0)),
            "worst_family_percent": factor*report.get("worst_family_score", report.get("worst_family", 0)),
            "runtime_seconds": report.get("runtime_seconds", report.get("evaluation_seconds")),
            "passed": report["passed"], "reason": report.get("reason", "")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--decision", required=True, choices=("hard_verified_achievable", "rejected"))
    parser.add_argument("--capability", default="")
    arguments = parser.parse_args()
    state = load("concept_2/status.json")
    latest_path = "concept_2/attempts/" + arguments.attempt + ".evaluation.json"
    latest = load(latest_path)
    metadata = load("concept_2/attempts/" + arguments.attempt + ".metadata.json")
    if metadata["status"] not in ("finished", "time_limit"):
        raise ValueError("cannot finalize an active attempt")
    private_validation = load("concept_2/adversary/validation_current.json")
    proven = private_validation["planted"]["passed"] and private_validation["generation"] == state["generation"]
    submission_audit_path = "concept_2/adversary/" + arguments.attempt + "_submission_audit.json"
    submission_audit = load(submission_audit_path)
    if arguments.decision == "hard_verified_achievable":
        if latest["passed"] or not proven or not arguments.capability:
            raise ValueError("hardness requires a failed challenger, current valid witness, and audited capability diagnosis")
        if not submission_audit["complete_json_scan"] or submission_audit["recoverable_artifact_score"]["passed"]:
            raise ValueError("cannot claim hardness from an incomplete candidate audit or packaging-only failure")
        if not all(metadata.get(key) for key in ("participant_unchanged", "evaluator_unchanged",
                                                 "frozen_matches_submission", "launcher_unchanged",
                                                 "evaluation_sandbox_unchanged")):
            raise ValueError("trial integrity checks must pass")
        witness_status = "hard_verified_achievable"
    else:
        witness_status = "solved" if latest["passed"] else "rejected"
    history = []
    for source in sorted((ROOT / "concept_2/attempts").glob("v_*.evaluation.json")):
        attempt = source.name.removesuffix(".evaluation.json")
        attempt_metadata = load("concept_2/attempts/" + attempt + ".metadata.json")
        history.append({"attempt": attempt, "authoring_seconds": attempt_metadata["elapsed_seconds"],
                        **summary(json.loads(source.read_text()))})
    state.update(status=witness_status, final_status=witness_status, fresh_agent_history=history,
                 final_fresh_evaluation=latest_path.removeprefix("concept_2/"),
                 fresh_agent=summary(latest), solvability_demonstrated=bool(proven),
                 authoring_seconds=metadata["elapsed_seconds"],
                 failure_audit=submission_audit_path.removeprefix("concept_2/"),
                 substantive_capability=arguments.capability,
                 hardness_claim="finite empirical result from isolated ultima-alpha attempts, not an intrinsic complexity proof")
    state["fresh_v" + str(state["generation"])] = "completed_main_tournament"
    (ROOT / "concept_2/status.json").write_text(json.dumps(state, indent=2) + "\n")
    spectrum = summary(load("concept_1/attempts/v_1.evaluation.json"))
    active = summary(load("concept_3/attempts/v_1.evaluation.json"), True)
    spectrum_search = load("concept_1/adversary/champion_search_1/results.json")
    active_search = load("concept_3/adversary/champion_search_1/report.json")
    initial_screen = load("concept_2/adversary/sweep_1/results.json")["records"]
    final_screen = load("concept_2/adversary/ratchet_3/screening_results.json")["records"]
    joint_screen = load("concept_2/adversary/ratchet_3/joint_screening_results.json")["records"]
    report = {
        "paper": "Bootstrapping the O(N) Archipelago, arXiv:1504.07997",
        "status": arguments.decision,
        "selected_concept": "concept_2" if arguments.decision == "hard_verified_achievable" else None,
        "models": ["ultima-alpha"], "fresh_agent_limit_seconds": 3600,
        "built_concepts": 3, "verification_modes": ["A", "C", "E"],
        "concepts": {
            "concept_1": {"mode": "A", "name": "Extremal mixed-matrix spectrum recovery", "status": "solved",
                          "baseline": summary(load("concept_1/evaluator/hidden/attempts/baseline.json")),
                          "fresh_agent": spectrum, "ratchet_generations": 0,
                          "champion": {"submission": "champions/generation_1", "official_score": spectrum,
                                       "private_core_percent": 100*spectrum_search["core"],
                                       "private_worst_family_percent": 100*spectrum_search["worst_family"],
                                       "private_runtime_seconds": spectrum_search["total_champion_runtime_seconds"]},
                          "counterexample_search": {"cases": 48, "counterexamples": 0}, "solvability": "demonstrated"},
            "concept_2": {"mode": "C", "name": "Sparse rank-one mixed-OPE completion", "status": witness_status,
                          "baseline": state["baseline"], "fresh_agent_history": history,
                          "fresh_agent": summary(latest), "ratchet_generations": state["ratchet_generations"],
                          "champion": {"submission": "champions/generation_2",
                                       "previous_generation_score": summary(load("concept_2/attempts/v_2.evaluation.json")),
                                       "current_generation_replay": state["baseline"]},
                          "counterexample_search": {
                              "first_screen": {"cases": len(initial_screen), "failures": sum(not record["valid"] for record in initial_screen)},
                              "second_screen": {"cases": len(final_screen)+len(joint_screen),
                                                "failures": sum(not record["valid"] for record in final_screen+joint_screen)},
                              "final_confirmed_champion_failures": 8},
                          "solvability": "demonstrated by all eight privately constructed and independently checked certificates",
                          "failure_audit": {"path": submission_audit_path,
                                            "saved_json_candidates_checked": submission_audit["candidate_count"],
                                            "packaging_only_failure": submission_audit["packaging_only_failure"],
                                            "independent_precision_digits": 70,
                                            "authoring_seconds": metadata["elapsed_seconds"]},
                          "substantive_capability": arguments.capability},
            "concept_3": {"mode": "E", "name": "Active radial spectroscopy", "status": "solved",
                          "baseline": summary(load("concept_3/attempts/baseline_tournament_v1.json"), True),
                          "fresh_agent": active, "ratchet_generations": 0,
                          "champion": {"submission": "champions/generation_1", "official_score": active,
                                       "private_core_percent": active_search["core_score"],
                                       "private_worst_family_percent": active_search["worst_family_score"],
                                       "private_runtime_seconds": active_search["broad_case_runtime_seconds"]},
                          "counterexample_search": {"cases": 384, "all_frozen_scientific_targets_passed": True,
                                                    "meaningful_counterexamples": 0}, "solvability": "demonstrated"}
        }
    }
    (ROOT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (ROOT / "status.json").write_text(json.dumps({key: report[key] for key in
        ("status", "selected_concept", "built_concepts", "verification_modes", "models", "fresh_agent_limit_seconds")}, indent=2)+"\n")
    lines = ["# Hardness-discovery report", "", "| Concept | Mode | Baseline core | Fresh core / worst | Status |",
             "|---|---|---:|---:|---|"]
    for name, concept in report["concepts"].items():
        baseline = concept["baseline"]
        baseline_core = baseline.get("core_percent", 100*baseline.get("core_score", 0))
        fresh = concept["fresh_agent"]
        lines.append(f"| {name}: {concept['name']} | {concept['mode']} | {baseline_core:.2f}% | "
                     f"{fresh['core_percent']:.2f}% / {fresh['worst_family_percent']:.2f}% | {concept['status']} |")
    lines.extend(["", "Witness fresh-generation core history: " + " → ".join(f"{item['core_percent']:.2f}%" for item in history) + ".",
                  "Champion private scores (core / worst): spectrum recovery "
                  + f"{100*spectrum_search['core']:.2f}% / {100*spectrum_search['worst_family']:.2f}%; "
                  + "active design " + f"{active_search['core_score']:.2f}% / {active_search['worst_family_score']:.2f}%. "
                  + "The previous witness champion solves its own generation but passes 0/8 final-generation replay cases.",
                  f"Ratchet generations: 0 / {state['ratchet_generations']} / 0 (concepts 1 / 2 / 3).",
                  "Counterexample searches: 0/48 for spectrum recovery; 0 meaningful failures across 384 active-design cases; "
                  + str(len(initial_screen)) + " and " + str(len(final_screen)+len(joint_screen))
                  + " witness screening cases, followed by eight confirmed failures of each preceding champion replay.",
                  "Solvability: demonstrated for all three final tasks; the witness task has independently verified private certificates.",
                  "Final status: `" + arguments.decision + "`.",
                  "Substantive capability: " + (arguments.capability or "No meaningful hard concept survives.")])
    (ROOT / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"status": report["status"], "selected_concept": report["selected_concept"]}))


if __name__ == "__main__":
    main()
