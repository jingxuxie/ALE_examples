import datetime
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def attempt_record(concept, number):
    metadata = read(concept / "attempts" / f"v_{number}.metadata.json")
    assert metadata["participant_unchanged"] and metadata["evaluator_unchanged"]
    assert "finished_utc" in metadata
    return {key: metadata[key] for key in ["model", "generation", "attempt", "limit_seconds",
            "elapsed_seconds", "returncode", "timed_out", "participant_unchanged", "evaluator_unchanged"]} | {
        "score": read(concept / "attempts" / f"v_{number}.score.json")}


def main():
    concept = ROOT / "concept_2"
    state = read(concept / "status.json")
    first = attempt_record(concept, 1)
    second = attempt_record(concept, 2)
    assert first["score"]["passed"] and not second["score"]["passed"]
    assert second["score"]["valid"] and second["score"]["evidence_valid"]
    state.update({"status": "hard_open_candidate", "final_status": "hard_open_candidate",
                  "final_classification": "hard_open_candidate", "fresh_agent_attempted": True,
                  "fresh_agent_results": [first, second], "solvability": "unknown_for_strengthened_screen",
                  "known_successful_witness": False, "selected_for_retention": True, "primary_selection": False,
                  "failure_capability": "Constructing a bounded exact-negative matrix polynomial that evades the strengthened all-principal-minor screen; the fresh admissible witness is rejected by all three profiles.",
                  "scoring_environment": "research/score_attempt.py concept_2 --attempt 2",
                  "decision_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    write(concept / "status.json", state)
    concept = ROOT / "concept_1"
    state = read(concept / "status.json")
    first = attempt_record(concept, 1)
    assert first["score"]["passed"]
    archive = concept / "adversary" / "generation_1_packet"
    if not archive.exists():
        archive.mkdir()
        for name in ["participant", "evaluator"]:
            shutil.copytree(concept / name, archive / name, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(concept / "status.json", archive / "status.json")
    champion = concept / "champions" / "generation_1"
    if not champion.exists():
        shutil.copytree(concept / "attempts" / "v_1", champion, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(concept / "attempts" / "v_1.score.json", champion / "score.json")
    state.update({"status": "solved_pending_private_challenge_search", "fresh_agent_attempted": True,
                  "fresh_agent_results": [first], "current_champion_score": first["score"],
                  "champion": "champions/generation_1/solution.py",
                  "solvability": "demonstrated_by_generation_1_fresh_champion",
                  "scoring_environment": "research/score_attempt.py concept_1 --attempt 1"})
    write(concept / "status.json", state)
    print("Concept 2 generation 2 retained as open; concept 1 champion archived for private search.")


if __name__ == "__main__":
    main()
