import datetime
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCORE_KEYS = (
    "core_score", "worst_family_score", "resource_score", "runtime_score",
    "passed", "valid", "reason", "max_tolerance_ratio", "scalar_count",
    "matched_lags", "squared_error", "runtime_seconds", "elapsed_seconds",
)


def load(relative):
    return json.loads((ROOT / relative).read_text())


def save(relative, value):
    destination = ROOT / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(value, indent=2) + "\n")


def score(relative):
    report = load(relative)
    return {"report": relative, **{key: report[key] for key in SCORE_KEYS if key in report}}


def attempts(concept):
    records = []
    for path in sorted((ROOT / concept / "attempts").glob("v_*.run.json")):
        run = json.loads(path.read_text())
        suffix = ".corrected_score.json" if concept == "concept_1" and run["generation"] == 2 else ".score.json"
        relative = f"{concept}/attempts/v_{run['attempt']}{suffix}"
        records.append({
            "attempt": run["attempt"], "generation": run["generation"],
            "model": run["model"], "time_limit_seconds": run["time_limit_seconds"],
            "observed_elapsed_seconds": run["elapsed_seconds"], "timed_out": run["timed_out"],
            "strict_deadline_snapshot": run["timed_out"], "score": score(relative),
        })
    return records


def main():
    audit = load("authoring/tournament_audit.json")
    if not audit["passed"] or audit["attempt_count"] != 10:
        raise ValueError("the complete ten-attempt isolation audit must pass first")
    review = load("concept_3/adversary/independent_generation_2_review/result.json")
    if not review["evaluator_valid"]:
        raise ValueError("the independent construction evaluator audit did not pass")
    for filename in ("generation_2_fresh_native_confirmation.json", "generation_2_fresh_v4_native_confirmation.json"):
        native = load("concept_2/adversary/" + filename)
        if not native["resolved"]:
            raise ValueError("direct-source quadrature confirmation did not resolve")
    all_attempts = {concept: attempts(concept) for concept in ("concept_1", "concept_2", "concept_3")}
    if not all_attempts["concept_1"][-1]["score"]["passed"]:
        raise ValueError("unexpected compression outcome requires review")
    for concept in ("concept_2", "concept_3"):
        current = [entry for entry in all_attempts[concept] if entry["generation"] == 2]
        if len(current) != 2 or any(entry["score"]["passed"] for entry in current):
            raise ValueError("a solved or incomplete current generation needs ratchet review")
        if not all(entry["score"]["valid"] for entry in current):
            raise ValueError("invalid artifacts require substantive-failure review")
    planted = score("concept_3/adversary/generation_2_installed_planted.json")
    if not planted["passed"] or planted["matched_lags"] != 4096:
        raise ValueError("achievability has not been demonstrated for the current target")
    updated = datetime.datetime.now(datetime.timezone.utc).isoformat()
    shared = {
        "generation": 2, "total_generations": 2, "ratchet_generations": 1,
        "target_frozen_before_attempts": True, "evaluator_validated": True,
        "updated_at_utc": updated,
    }
    compression = {
        **shared, "concept": "compact_color_resolved_response", "mode": "A",
        "status": "solved", "final_status": "solved", "retained_as_hard": False,
        "solvability": "demonstrated", "champion": "champions/generation_2",
        "target": "All value, derivative, combination and bin tolerances at 268 stored scalars, including endpoint power-suppressed residuals.",
        "baseline_generation_1": score("concept_1/adversary/baseline_score.json"),
        "baseline_generation_2": score("concept_1/adversary/generation_2_baseline.json"),
        "champion_generation_1": score("concept_1/champions/generation_1/score.json"),
        "champion_generation_2": score("concept_1/champions/generation_2/score.json"),
        "fresh_attempts": all_attempts["concept_1"],
        "counterexample_search": {
            "result": "Original contract passes a broad audit; downstream endpoint residual extraction amplifies its approximation error. A new endpoint-chart generation is solved, including the broad private audit.",
            "evidence": ["adversary/RATCHET.md", "adversary/nlp_search", "adversary/generation_2_broad.json"],
        },
        "evaluator_repair": "An interval-local bin quadrature repair and strict numeric parsing were independently audited after the attempt. Regrading the exact frozen artifact leaves its score and maximum tolerance ratio unchanged; the original launch snapshot is retained.",
        "substantive_failure": None,
    }
    falsification = {
        **shared, "concept": "guarded_weighted_eec_falsification", "mode": "B",
        "status": "hard_open_candidate", "final_status": "hard_open_candidate", "retained_as_hard": True,
        "solvability": "unknown", "champion": "champions/generation_1",
        "target": "Every color must report convergence and have certified error at least max(20*tau, 50*reported_error, 1e-5*reference_L1).",
        "baseline_generation_1": score("concept_2/attempts/baseline/report.json"),
        "champion_generation_1": score("concept_2/champions/generation_1/score.json"),
        "baseline_generation_2": score("concept_2/adversary/generation_2_baseline.json"),
        "privileged_generation_2_best": score("concept_2/adversary/guarded_best/report.json"),
        "fresh_attempts": all_attempts["concept_2"],
        "counterexample_search": {
            "result": "The first-generation champion defeats correlated embedded and parent-child error estimates. An independent Gauss-12 guard removes that witness. No passing generation-two witness is known after 1200 private configurations and two full-hour fresh attempts.",
            "evidence": ["adversary/RATCHET.md", "adversary/guarded_search_outcomes.json", "adversary/generation_2_fresh_native_confirmation.json", "adversary/generation_2_fresh_v4_native_confirmation.json", "adversary/final_generation_2_numerical_tests.log"],
        },
        "substantive_failure": "Construct a sufficiently material, simultaneously false-confidence integration failure in all three color channels while satisfying the bandwidth, norm, response and independent-reference constraints. Feasible final weights understate errors but reach only about 11.4% of the fixed materiality target.",
    }
    construction = {
        **shared, "concept": "exact_inverse_energy_flow", "mode": "C",
        "status": "hard_verified_achievable", "final_status": "hard_verified_achievable", "retained_as_hard": True,
        "solvability": "demonstrated", "champion": "champions/generation_1",
        "target": "A ternary event on 4096 antipodal pairs must satisfy energy counts, cyclic spacing, and all 4096 exact integer autocorrelation constraints.",
        "baseline_generation_1": score("concept_3/champions/generation_1/task_snapshot/participant/baseline/grade_report.json"),
        "champion_generation_1": score("concept_3/champions/generation_1/score.json"),
        "baseline_generation_2": score("concept_3/participant/baseline/grade_report.json"),
        "phase_baseline_generation_2": score("concept_3/adversary/generation_2_phase_baseline/score.json"),
        "privileged_passing_witness": planted,
        "fresh_attempts": all_attempts["concept_3"],
        "counterexample_search": {
            "result": "The successful original constructor is replayed exactly and then tested on 17 private cases. It solves 2/4 new 512-pair cases but 0/12 larger cases in 90 seconds each. The higher-resolution target is planted once, without solver-based target selection; the actual hardness decision uses two full-hour fresh attempts.",
            "evidence": ["adversary/RATCHET.md", "adversary/champion_replay/scale_results.json", "adversary/generation_2_installed_planted.json", "adversary/independent_generation_2_review/result.json"],
        },
        "substantive_failure": "Recover a globally consistent high-dimensional discrete energy-flow event from complete two-point correlations, rather than only a coarse spectrum or a locally improved feasible event.",
    }
    concepts = {"concept_1": compression, "concept_2": falsification, "concept_3": construction}
    for concept, status in concepts.items():
        backup = ROOT / "authoring/pre_final_status" / (concept + ".json")
        if not backup.exists():
            save(str(backup.relative_to(ROOT)), load(concept + "/status.json"))
        save(concept + "/status.json", status)
    save("status.json", {
        "status": "hard_verified_achievable", "primary_concept": "concept_3",
        "retained_concepts": ["concept_3", "concept_2"], "solved_not_retained": ["concept_1"],
        "built_concepts": 3, "verification_modes": ["A", "B", "C"],
        "fresh_agent_model": "ultima-alpha", "fresh_attempt_count": 10,
        "attempt_time_limit_seconds": 3600, "ratchet_generations_per_concept": 1,
        "primary_solvability": "demonstrated", "secondary_solvability": "unknown",
        "isolation_audit": "authoring/tournament_audit.json", "report": "FINAL_REPORT.md",
        "updated_at_utc": updated,
    })
    lines = [
        "# Empirical hardness report", "", "## Concepts and verification modes", "",
        "| Concept | Mode | Final status | Solvability |",
        "|---|---|---|---|",
        "| 1: compact color-resolved response | A: baseline improvement | solved; not retained as hard | demonstrated |",
        "| 2: guarded weighted-EEC integration | B: counterexample | hard_open_candidate | unknown |",
        "| 3: exact inverse energy flow | C: witness construction | hard_verified_achievable; primary task | demonstrated by private passing witness |",
        "", "Each concept has **one ratchet, two task generations**. Ten isolated `ultima-alpha` attempts were run; each had a 3600-second budget. Timeout scores use artifacts observed before the strict deadline, not termination-grace output.",
        "", "## Baseline and champion scores", "",
        "Scores below are core / worst-family; passing requires the complete task condition, not merely a nonzero score.", "",
        "| Concept | Original baseline | Original champion | Current baseline / privileged result |",
        "|---|---|---|---|",
        "| 1 | 0.996696 / 0.977350; max tolerance ratio 210.413 | 1 / 1; ratio 0.00124203 | 0.908622 / 0.636015; ratio 9,273,303.98. Current fresh champion: 1 / 1, ratio 0.00220509, 268 scalars. |",
        "| 2 | 0 / 0 | 1 / 1; minimum uncapped margin 1.291893 | Old champion against guard: 0 / 0. Private guarded search best: 0.0679279 / 0.0649429; no passing witness. |",
        "| 3 | 0 / 0; 79/512 lags | 1 / 1; 512/512 lags | Local baseline: 0 / 0, 149/4096 lags; supplied projection baseline: 0 / 0, 99/4096. Private planted witness: 1 / 1, 4096/4096. |",
        "", "## Fresh-agent scores", "",
        "| Concept | Generation / attempt | Core | Worst family | Passed | Construction seconds | Diagnostic |",
        "|---|---|---:|---:|---|---:|---|",
    ]
    for concept, records in all_attempts.items():
        for entry in records:
            result = entry["score"]
            seconds = min(entry["observed_elapsed_seconds"], entry["time_limit_seconds"])
            if "max_tolerance_ratio" in result:
                diagnostic = f"max tolerance ratio {result['max_tolerance_ratio']:.8g}; {result['scalar_count']} scalars"
            elif "matched_lags" in result:
                total = 512 if entry["generation"] == 1 else 4096
                diagnostic = f"{result['matched_lags']}/{total} exact lags; SSE {result['squared_error']}"
            else:
                diagnostic = "feasible weight; all numerical reference gates resolve"
            lines.append(f"| {concept} | {entry['generation']} / v_{entry['attempt']} | {result['core_score']:.9g} | {result['worst_family_score']:.9g} | {result['passed']} | {seconds:.1f} | {diagnostic} |")
    lines += [
        "", "All final artifacts are schema/constraint-valid; resource scores are 1. Evaluation runtimes are separate from construction budgets and remain in the individual score reports.",
        "", "## Counterexample search results", "",
        "- **Compression:** a 60,001-point original-contract sweep passes, but endpoint power-suppressed residual extraction amplifies the original approximation error. The strengthened chart-based generation is solved and passes its broad private sweep. A subsequent local-coordinate bin-integration repair does not change the frozen champion's measured score.",
        "- **Quadrature:** both original agents produce material three-color counterexamples. The nonnested Gauss-12 guard eliminates the old champion. A 1200-configuration private search and both full-hour challengers find no qualifying guarded witness. Independent high-precision refinement and direct source-native confirmation agree.",
        "- **Construction:** exact replay reproduces the original successful projection method. The 17-case scale sweep exposes persistent projection stagnation, including 0/12 successes at larger resolutions in its short screening budget. The current target was fixed before attempts and its private planted event passes every installed constraint. A separate independent evaluator audit passes.",
        "", "## Substantive capability failures", "",
        "- **Concept 2:** the fresh agents obtain real error underestimation, but cannot make it sufficiently material in all three color channels while satisfying the fixed smooth-weight and independent-reference contract. Both achieve only about 11.4% of the required margin. Current-target solvability remains unknown; the old-generation witness is not claimed as a current solution.",
        "- **Concept 3:** the agents cannot reconstruct one exact globally consistent high-dimensional discrete energy-flow event from the full two-point correlation within one hour. Feasible approximations and coarse reconstructions do not satisfy the full exact witness condition. Achievability is demonstrated by a private event validated against the same target and constraints.",
        "- **Concept 1:** no surviving substantive failure; the strengthened task is solved and is not retained as hard.", "",
    ]
    (ROOT / "FINAL_REPORT.md").write_text("\n".join(lines))
    print(json.dumps({concept: status["status"] for concept, status in concepts.items()}))


if __name__ == "__main__":
    main()
