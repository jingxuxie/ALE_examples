import datetime
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"solved", "hard_open_candidate", "hard_verified_achievable", "invalid", "rejected"}
NAMES = {"concept_1": "Robust weighted interpolation", "concept_2": "Polynomial-matrix positivity counterexample",
         "concept_3": "Compact exact rational SOS certificates"}
MODES = {"concept_1": "A — baseline improvement", "concept_2": "B — counterexample/falsification",
         "concept_3": "C — witness construction"}


def compact(score):
    return {key: score[key] for key in ["core_score", "worst_family_score", "runtime_score", "resource_score",
                                      "passed", "valid", "reason"] if key in score}


def main():
    concepts = []
    for identifier in NAMES:
        concept = ROOT / identifier
        state = json.loads((concept / "status.json").read_text())
        classification = state.get("final_status", state.get("final_classification", state.get("status")))
        if classification not in ALLOWED:
            raise RuntimeError(identifier + " has no completed empirical decision")
        attempts = []
        for metadata_path in sorted((concept / "attempts").glob("v_*.metadata.json")):
            record = json.loads(metadata_path.read_text())
            if "finished_utc" not in record or not record["participant_unchanged"] or not record["evaluator_unchanged"]:
                raise RuntimeError("Unfinished or integrity-failed attempt: " + str(metadata_path))
            score_path = metadata_path.with_name(metadata_path.name.replace(".metadata.json", ".score.json"))
            score = json.loads(score_path.read_text())
            attempts.append({"generation": record["generation"], "attempt": record["attempt"],
                             "model": record["model"], "limit_seconds": record["limit_seconds"],
                             "elapsed_seconds": record["elapsed_seconds"], "timed_out": record["timed_out"],
                             "score": compact(score)})
        baseline = state.get("baseline_score", state.get("baseline", {}))
        concepts.append({"id": identifier, "name": NAMES[identifier], "verification_mode": MODES[identifier],
                         "baseline": compact(baseline), "fresh_attempts": attempts,
                         "ratchet_generations": state.get("ratchet_generations", 0),
                         "status": classification, "solvability": state.get("solvability", "unknown"),
                         "failure_capability": state.get("failure_capability", "none; target achieved"),
                         "privileged_witness": compact(state.get("privileged_witness_score", {})),
                         "champion": compact(state.get("current_champion_score", {}))})
    selected = next(item for item in concepts if item["id"] == "concept_3")
    if selected["status"] != "hard_verified_achievable":
        raise RuntimeError("Retained exact-certificate decision changed; review selection manually")
    search = json.loads((ROOT / "concept_2" / "adversary" / "generation_1_challenge_search.json").read_text())
    counterexamples = {key: search[key] for key in ["cases", "all_admissible", "original_successes",
                       "enhanced_successes", "common_nullspace_verified_exactly", "root_cause", "repair"]}
    interpolation_search = json.loads((ROOT / "concept_1/adversary/champion_search/handoff.json").read_text())
    interpolation_stress = json.loads((ROOT / "concept_1/adversary/isolated_stress.json").read_text())
    assert interpolation_stress["passed"]
    interpolation = {key: interpolation_search[key] for key in ["screened_cases", "scientific_families",
                     "schema_validated_cases", "oracle_confirmed_case_pairs", "oracle_confirmed_enclosures",
                     "triage_only_cases", "genuine_numerical_failures", "caveat"]}
    interpolation["isolated_stress_checks"] = interpolation_stress
    report = {"paper": "A Semidefinite Program Solver for the Conformal Bootstrap (1502.02033)",
              "completed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "status": "hard_verified_achievable", "selected_concept": "concept_3", "tournament_complete": True,
              "built_concept_count": 3, "concepts": concepts, "counterexample_search": counterexamples,
              "interpolation_champion_search": interpolation,
              "isolated_fresh_attempt_count": sum(len(item["fresh_attempts"]) for item in concepts),
              "retained_hard_concepts": [item["id"] for item in concepts if item["status"].startswith("hard_")],
              "total_ratchet_generations": sum(item["ratchet_generations"] for item in concepts),
              "solvability": "selected task demonstrated by exact private certificates for all three blocks"}
    (ROOT / "status.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = ["# Empirical hardness report", "", "## Concepts and verification modes", ""]
    lines += [f"- {item['id']}: {item['name']} — {item['verification_mode']}." for item in concepts]
    lines += ["", "## Scores", "", "| Concept | Baseline core | Fresh attempts (generation: core / worst / resource) | Final status |",
              "|---|---:|---|---|"]
    for item in concepts:
        runs = "; ".join(f"{run['generation']}: {run['score']['core_score']:.8g} / {run['score']['worst_family_score']:.8g} / {run['score'].get('resource_score', run['score'].get('runtime_score', 0)):.8g}"
                         for run in item["fresh_attempts"])
        lines.append(f"| {item['id']} | {item['baseline'].get('core_score', 0):.8g} | {runs} | {item['status']} |")
    lines += ["", "Concept 3's private certificates score 1/1, while the fresh attempt certifies 2/3 blocks.",
              "The remaining approximate identity has a scaled residual of 4.21e-104 but is not exact.",
              "Concept 2's first champion scores 1 on generation 1 and 0 on the strengthened generation 2.",
              "Concept 1's champion is its passing fresh submission: core 1.5336553, worst family 1.2076233, resource 0.90332959. Its fixed targets were 1.15, 1.05, and 0.10, plus a 0.95 minimum-case floor.",
              "", "## Counterexample search", "",
              "Interpolation: 160 schema-valid cases across 12 regimes; 13 case pairs received full numerical enclosures and 147 remain triage-only. No confirmed regression emerged. Two timer-limited stress pairs were additionally run through the isolated executable grader and passed quality/resource checks. No failure-based ratchet was justified; this is not a universal optimality claim.",
              "The initial private pilot found 0 successful witnesses in 24 admissible cases. The first fresh agent then found a valid degree-four witness.",
              f"A {counterexamples['cases']}-case signed-basis/near-singularity sweep yielded {counterexamples['original_successes']} false acceptances under generation 1 and {counterexamples['enhanced_successes']} under generation 2.",
              "The clustered failure combines a common nullspace, flat smallest eigenbranch, and an identically zero full determinant. All-principal-minor candidates resolve that cluster.",
              "", "## Ratchets, solvability, and failed capability", ""]
    for item in concepts:
        lines += [f"- {item['id']}: {item['ratchet_generations']} ratchet(s); solvability {item['solvability']}. {item['failure_capability']}"]
    lines += ["", "## Final status", "", "Selected: **concept_3 — hard_verified_achievable**.",
              "Solvability is demonstrated by exact private witnesses; a one-hour isolated ultima-alpha attempt did not produce all required certificates.", ""]
    (ROOT / "REPORT.md").write_text("\n".join(lines))
    print(json.dumps({"status": report["status"], "selected_concept": "concept_3",
                      "ratchets": report["total_ratchet_generations"], "concepts":
                      [{key: item[key] for key in ["id", "status", "solvability"]} for item in concepts]}, indent=2))


if __name__ == "__main__":
    main()
