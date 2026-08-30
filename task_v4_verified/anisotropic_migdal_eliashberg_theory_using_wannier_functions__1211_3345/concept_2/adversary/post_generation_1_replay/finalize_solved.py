import copy
import json
import subprocess
from pathlib import Path

from replay import CHAMPION, EXPECTED_INPUT, GENERATION, HERE, ROOT, RUNS, copy_file, digest, manifest, read_json, write_json


def root_evaluate(artifact, name):
    destination = HERE / "final_validation" / (name + ".json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = ["/usr/bin/python3", "-B", str(ROOT / "evaluator" / "evaluate.py"), "--artifact", str(artifact), "--output", str(destination)]
    with destination.with_suffix(".log").open("w") as stream:
        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=120, check=True)
    result = read_json(destination)
    if result["input_sha256"] != EXPECTED_INPUT or not result["reason"]:
        raise ValueError("unexpected active input or missing reporting")
    if result["core_score"] != result["score"] or result["worst_family_score"] != result["score"] or not result["resources"]:
        raise ValueError("reporting contract failed")
    return result


def main():
    replay = read_json(HERE / "summary.json")
    if replay["actual_search_replays"] != 8 or replay["passing_replays"] != 8 or not replay["control_passed"]:
        raise ValueError("not all actual-search replays passed; parent review is required")
    if replay["genuine_admissible_failures"] or replay["inconclusive_replays"]:
        raise ValueError("unresolved replay evidence requires parent review")
    protected = read_json(HERE / "protected_manifest.json")
    if any(manifest(ROOT / kind) != expected for kind, expected in protected.items()):
        raise ValueError("active package differs from the protected replay snapshot")
    active = read_json(ROOT / "status.json")
    original = read_json(GENERATION / "activation_previous" / "status.json")
    if active["generation"] != 1 or active["target_ratio"] != 1.09 or active["input_sha256"] != EXPECTED_INPUT:
        raise ValueError("unexpected active numerical generation")
    copy_file(ROOT / "status.json", HERE / "archive" / "status_before_finalization.json")
    current = []
    for name in ("v_3", "v_4"):
        evaluated = read_json(RUNS / name / "evaluation.json")
        if not evaluated["valid"] or evaluated["input_sha256"] != EXPECTED_INPUT:
            raise ValueError("fresh generation-1 evaluation no longer valid")
        current.append({"attempt": name, "generation": 1, "score": evaluated["score"], "valid": evaluated["valid"], "admissible": evaluated["admissible"], "input_sha256": evaluated["input_sha256"], "evaluation": "authoring/runs/concept_2/" + name + "/evaluation.json"})
    best = root_evaluate(CHAMPION / "frozen_submission" / "witness.npz", "best_frozen_v4")
    expected = read_json(CHAMPION / "evaluation.json")
    if best["score"] != expected["score"] or not best["valid"]:
        raise ValueError("root v4 numerical verdict changed")
    baseline_path = HERE / "final_validation" / "baseline.npz"
    subprocess.run(["/usr/bin/python3", "-B", str(ROOT / "participant" / "baseline" / "solve.py"), "--output", str(baseline_path)], check=True, timeout=60)
    baseline = root_evaluate(baseline_path, "baseline")
    if baseline["score"] != 1.0 or not baseline["admissible"] or baseline["valid"]:
        raise ValueError("baseline numerical verdict changed")
    if any(manifest(ROOT / kind) != expected for kind, expected in protected.items()):
        raise ValueError("active package changed during final checks")
    status = copy.deepcopy(active)
    minimax = copy.deepcopy(original["minimax_review"])
    minimax.update(promoted=True, fresh_protocol_completed=True, hardness_survived_fresh=False,
                   resolution="Both new independent fresh challengers solve the fixed 1.09 task; actual v4 search also passes all eight existing pool cases.")
    status.update({
        "schema_version": 2, "status": "solved", "hard": False,
        "hardness_assessment": "not_hard; no surviving champion-challenger gap in the bounded validated pool",
        "active_numerical_generation": 1, "promoted_ratchet_generations": 1,
        "reason": "Solved: v3 and v4 independently pass generation 1 at its fixed target 1.09. The actual v4 minimax search reproduces its control exactly and passes all eight frozen private-pool cases. One numerical ratchet was promoted; no second ratchet or fresh launch is requested. Original generation-0 history remains archived; the n24 600-second replay remains inconclusive.",
        "solvability_demonstrated_by_fresh": True, "review_complete": True,
        "original_fresh_results": original["original_fresh_results"], "original_passing_fresh_count": 2,
        "current_fresh_results": current, "current_generation_passing_fresh_count": 2,
        "total_passing_fresh_count": 4, "best_fresh_attempt": "v_4",
        "champion_archive": "champions/generation_2", "champion_score": best["score"],
        "best_frozen_v4": best, "baseline": baseline,
        "generation_0_history": {"status_archive": "adversary/generation_1/activation_previous/status.json", "input_sha256": original["input_sha256"], "target_ratio": original["target_ratio"], "fresh_scores": [record["score"] for record in original["original_fresh_results"]], "champion_archive": "champions/generation_1", "actual_search_replay_count": 23},
        "actual_search_replay_count": 23 + replay["actual_search_replays"],
        "prior_v2_actual_search_replay_count": 23, "current_v4_actual_search_replay_count": replay["actual_search_replays"],
        "completed_passing_replay_count": original["completed_passing_replay_count"] + replay["passing_replays"],
        "historical_completed_admissible_failing_replay_count": original["completed_admissible_failing_replay_count"],
        "current_v4_genuine_admissible_failures": replay["genuine_admissible_failures"],
        "current_v4_replay_evidence": "adversary/post_generation_1_replay/summary.json",
        "current_v4_replay_search_cpu_seconds": replay["search_cpu_seconds"],
        "minimax_review": minimax, "n24_review": original["n24_review"],
        "reporting_finalization": original["reporting_finalization"],
        "final_validation": "adversary/post_generation_1_replay/final_validation",
        "target_frozen": True, "ready_for_initial_attempts": False,
        "remaining_scheduled_search_seconds": 0, "new_fresh_launches_during_finalization": 0,
    })
    encoded = json.dumps(status, indent=2, sort_keys=True, allow_nan=False) + "\n"
    original_text = (ROOT / "status.json").read_text()
    patch = "*** Begin Patch\n*** Update File: " + str(ROOT / "status.json") + "\n@@\n" + "".join("-" + line + "\n" for line in original_text.splitlines()) + "".join("+" + line + "\n" for line in encoded.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True)
    write_json(HERE / "finalization.json", {
        "status": "solved", "root_changed_paths": ["status.json"],
        "active_participant_and_evaluator_unchanged": True, "promoted_ratchet_generations": 1,
        "v3_score": current[0]["score"], "v4_score": best["score"], "baseline_score": baseline["score"],
        "root_status_sha256": digest(ROOT / "status.json"), "replay_summary_sha256": digest(HERE / "summary.json"),
        "fresh_launches": 0, "reason": "All eight actual v4 searches passed; no surviving gap supports another ratchet.",
    })
    print(json.dumps(read_json(HERE / "finalization.json")), flush=True)


if __name__ == "__main__":
    main()
