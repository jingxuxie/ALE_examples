import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODES = {1: "A: baseline improvement", 2: "B: counterexample/falsification", 3: "D: hidden prediction"}
NAMES = {1: "Reliable compact equilibrium proposals", 2: "Full-support false convergence", 3: "Hidden-spin material response"}
FINAL_STATUSES = {"solved", "hard_open_candidate", "hard_verified_achievable", "invalid", "rejected"}


def load(path):
    return json.loads(Path(path).read_text())


def summary(report):
    keep = ("valid", "evaluator_valid", "passed", "reason", "core_score", "worst_family_score",
            "runtime_resource_score", "resource_score", "mean_kl", "worst_family_kl", "minimum_ess",
            "baseline_mean_kl", "baseline_ratio", "family_kl", "metrics", "family_mean_kl", "targets",
            "failing_gates", "runtime_seconds", "resource", "suite_sha256")
    return {key: report[key] for key in keep if key in report}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--concept", type=int, choices=(1, 2, 3))
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--generation-root")
    parser.add_argument("--score-report", default="score.json")
    parser.add_argument("--decision", choices=sorted(FINAL_STATUSES))
    parser.add_argument("--ratchets", type=int, default=0)
    parser.add_argument("--known-solution")
    parser.add_argument("--capability", default="")
    parser.add_argument("--counterexample-search", default="")
    parser.add_argument("--selected-concept", type=int, choices=(1, 2, 3))
    parser.add_argument("--selection-reason", default="")
    parser.add_argument("--finish", action="store_true")
    arguments = parser.parse_args()
    if arguments.concept is not None:
        if arguments.decision is None or not 0 <= arguments.ratchets <= 3:
            raise ValueError("explicit decision and valid ratchet count required")
        concept = ROOT / ("concept_" + str(arguments.concept))
        generation = Path(arguments.generation_root).resolve() if arguments.generation_root else concept
        run = generation / "attempts" / ("v_" + str(arguments.version) + "_run")
        metadata = load(run / "metadata.json")
        score_path = (run / arguments.score_report).resolve()
        if score_path.parent != run.resolve():
            raise ValueError("score report must belong to this exact isolated run")
        report = load(score_path)
        if metadata["status"] not in ("finished", "time_limit") or metadata.get("participant_unchanged") is not True:
            raise ValueError("attempt not finished or participant assets changed")
        if arguments.decision == "solved" and report.get("passed") is not True:
            raise ValueError("cannot call failed attempt solved")
        if arguments.decision.startswith("hard_") and report.get("passed") is True:
            raise ValueError("a passing fresh submission is not empirical hardness")
        known = load(arguments.known_solution) if arguments.known_solution else None
        if arguments.decision == "hard_verified_achievable" and (not known or known.get("passed") is not True or report.get("passed") is True):
            raise ValueError("verified hardness requires private pass and fresh fail")
        baseline_paths = [generation / "adversary" / "baseline_report.json", generation / "adversary" / "baseline_score.json"]
        baseline = next((load(path) for path in baseline_paths if path.exists()), None)
        previous = load(concept / "status.json") if (concept / "status.json").exists() else {}
        history = previous.get("history", [])
        if arguments.decision.startswith("hard_") and any(item["generation_root"] == str(generation.relative_to(ROOT)) and item["fresh_score"].get("passed") for item in history):
            raise ValueError("this generation already has a passing fresh submission")
        entry = {"generation_root": str(generation.relative_to(ROOT)), "attempt": "v_" + str(arguments.version),
                 "decision": arguments.decision, "fresh_score": summary(report),
                 "run_metadata": str((run / "metadata.json").relative_to(ROOT)),
                 "score_report": str(score_path.relative_to(ROOT))}
        if score_path.name != "score.json" and (run / "score.json").exists():
            entry["initial_evaluation"] = {"report": str((run / "score.json").relative_to(ROOT)), "score": summary(load(run / "score.json"))}
        history = [item for item in history if (item["generation_root"], item["attempt"]) != (entry["generation_root"], entry["attempt"])] + [entry]
        value = {"concept": NAMES[arguments.concept], "verification_mode": MODES[arguments.concept],
                 "status": arguments.decision, "final_status": arguments.decision,
                 "current_generation": str(generation.relative_to(ROOT)), "ratchet_generations": arguments.ratchets,
                 "fresh_model": "ultima-alpha", "fresh_limit_seconds": 3600,
                 "baseline_or_champion_score": summary(baseline) if baseline else None,
                 "fresh_score": summary(report), "known_solution": str(Path(arguments.known_solution).resolve().relative_to(ROOT)) if known else None,
                 "known_solution_score": summary(known) if known else None,
                 "solvability": "demonstrated" if report.get("passed") or known and known.get("passed") else "unknown",
                 "substantive_capability": arguments.capability, "counterexample_search": arguments.counterexample_search,
                 "history": history, "updated_at": datetime.now(timezone.utc).isoformat()}
        (concept / "status.json").write_text(json.dumps(value, indent=2, allow_nan=False))
        if generation != concept:
            generation_path = generation / "status.json"
            generation_status = load(generation_path) if generation_path.exists() else {}
            generation_attempts = sum(item["generation_root"] == entry["generation_root"] for item in history)
            generation_status.update(status=arguments.decision, final_status=arguments.decision,
                                     empirical_hardness=arguments.decision, solvability=value["solvability"],
                                     known_passing_solution=bool(report.get("passed") or known and known.get("passed")),
                                     known_solution=value["known_solution"],
                                     known_solution_score=value["known_solution_score"],
                                     achievability=value["solvability"], fresh_agent_attempts=generation_attempts,
                                     tournament_launched=True, attempts_directory_empty=False,
                                     fresh_score=value["fresh_score"], score_report=entry["score_report"],
                                     run_metadata=entry["run_metadata"], ratchet_generations=arguments.ratchets,
                                     history=[item for item in history if item["generation_root"] == entry["generation_root"]],
                                     substantive_capability=value["substantive_capability"],
                                     counterexample_search=value["counterexample_search"],
                                     updated_at=value["updated_at"])
            generation_path.write_text(json.dumps(generation_status, indent=2, allow_nan=False))
    states = []
    for number in (1, 2, 3):
        path = ROOT / ("concept_" + str(number)) / "status.json"
        states.append(load(path) if path.exists() else {"status": "pending", "verification_mode": MODES[number]})
    selected = next((index + 1 for index, value in enumerate(states) if value.get("status") == "hard_verified_achievable"), None)
    if selected is None:
        selected = next((index + 1 for index, value in enumerate(states) if value.get("status") == "hard_open_candidate"), None)
    if arguments.selected_concept is not None:
        if states[arguments.selected_concept - 1].get("status") not in {"hard_open_candidate", "hard_verified_achievable"}:
            raise ValueError("the selected concept must have accepted empirical hardness")
        selected = arguments.selected_concept
    complete = all(value.get("status") in FINAL_STATUSES and value.get("history") for value in states)
    if arguments.finish and not complete:
        raise ValueError("all three concepts require completed scientific attempts and decisions")
    if arguments.finish:
        for metadata_path in ROOT.glob("concept_*/**/attempts/v_*_run/metadata.json"):
            metadata = load(metadata_path)
            if metadata["status"] == "running":
                raise ValueError("an isolated scientific attempt is still running")
            excluded = metadata_path.parent == ROOT / "concept_1/attempts/v_1_run"
            if not excluded and not (metadata_path.parent / "score.json").exists():
                raise ValueError("a scientific attempt has not been evaluated")
            if not excluded:
                generation_root = str(metadata_path.parents[2].relative_to(ROOT))
                attempt = metadata_path.parent.name.removesuffix("_run")
                if not any(item["generation_root"] == generation_root and item["attempt"] == attempt
                           for state in states for item in state.get("history", [])):
                    raise ValueError("a scientific attempt has no recorded hardness decision")
    overall = {"paper": "1809.10606", "phase": "complete" if arguments.finish else "tournament_and_ratchet",
               "status": states[selected - 1]["status"] if arguments.finish and selected else "rejected" if arguments.finish else "in_progress",
               "selected_concept": "concept_" + str(selected) if selected else None,
               "selected_task_root": states[selected - 1].get("current_generation") if selected else None,
               "selection_reason": arguments.selection_reason or "First verified hard concept, then first open hard concept, in concept order.",
               "concepts_built": 3, "verification_modes": ["A", "B", "D"], "fresh_model": "ultima-alpha",
               "fresh_limit_seconds": 3600, "maximum_ratchet_generations": 3,
               "solvability": states[selected - 1].get("solvability", "unknown") if selected else "unknown",
               "concept_statuses": {"concept_" + str(index + 1): value.get("status") for index, value in enumerate(states)},
               "infrastructure_exclusions": [{"run": "concept_1/attempts/v_1_run", "reason": "session initialization failed before scientific execution; not a hardness result"}],
               "updated_at": datetime.now(timezone.utc).isoformat()}
    (ROOT / "status.json").write_text(json.dumps(overall, indent=2, allow_nan=False))
    print(json.dumps(overall, indent=2))


if __name__ == "__main__":
    main()
