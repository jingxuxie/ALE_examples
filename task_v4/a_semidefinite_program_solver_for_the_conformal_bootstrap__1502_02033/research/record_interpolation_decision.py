import datetime
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "concept_1"


def main():
    state = json.loads((ROOT / "status.json").read_text())
    score = json.loads((ROOT / "attempts/v_1.score.json").read_text())
    search = json.loads((ROOT / "adversary/champion_search/handoff.json").read_text())
    isolated = json.loads((ROOT / "adversary/isolated_stress.json").read_text())
    assert score["passed"] and score["valid"] and isolated["passed"]
    assert search["schema_validated_cases"] == 160 and search["oracle_confirmed_case_pairs"] == 13
    assert not search["genuine_numerical_failures"] and not search["oracle_unresolved_cases"]
    state.update({"status": "solved", "final_status": "solved", "final_classification": "solved",
                  "selected_for_retention": False, "ratchet_generations": 0,
                  "solvability": "demonstrated_by_generation_1_fresh_champion",
                  "current_champion_score": score, "private_challenge_search": search,
                  "isolated_stress_checks": isolated,
                  "failure_capability": "None established: the fresh champion meets the target and the bounded 160-case search finds no confirmed regression.",
                  "no_ratchet_reason": "No genuine champion failure was found; no arbitrary threshold change or untrustworthy case was introduced.",
                  "decision_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    (ROOT / "status.json").write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps({"concept": "concept_1", "status": "solved", "ratchets": 0,
                      "screened_cases": 160, "oracle_confirmed_case_pairs": 13,
                      "additional_isolated_case_pairs": 2}, indent=2))


if __name__ == "__main__":
    main()
