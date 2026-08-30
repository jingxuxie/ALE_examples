from datetime import datetime, timezone
import json
from pathlib import Path

from build_resilience_generation import replace_text


ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return json.loads((ROOT / relative).read_text())


def compact(score):
    fields = ("core_score", "worst_family_score", "passed", "valid", "macro_rmse", "mean_risk",
              "mean_loss_risk", "intact_mean_ratio", "execution_ticks", "distinct_circuits")
    return {key: score[key] for key in fields if key in score}


def main():
    current = read("concept_1/attempts/v_3.score.json")
    confirmation = read("concept_1/adversary/generation_2/fresh_failure_confirmation.json")
    private = read("concept_1/adversary/generation_2/best_private_score.json")
    portfolio = read("concept_1/adversary/generation_2/completed_attempt_portfolio/summary.json")
    baseline = read("concept_1/adversary/generation_2/baseline_score.json")
    assert current["valid"] and not current["passed"]
    assert not confirmation["passed"] and confirmation["disjoint_from_official_hidden_points"]
    assert current["core_score"] < .25 * .9 and current["worst_family_score"] < .20 * .9
    proofs = [dict(artifact="adversary/generation_2/best_private_design.json", **compact(private))]
    proofs.extend(portfolio["results"])
    passing = [entry for entry in proofs if entry["passed"] and entry["valid"]]
    classification = "hard_verified_achievable" if passing else "hard_open_candidate"
    failed_capability = (
        "Joint circuit-support selection and integer-shot allocation meeting average and worst-regime "
        "information-retention targets after three complete circuit-record losses, while preserving "
        "normal-operation efficiency and the acquisition budget."
    )
    history = {}
    for name in ("concept_1", "concept_2", "concept_3"):
        history[name] = []
        for path in sorted((ROOT / name / "attempts").glob("*.run.json")):
            run = json.loads(path.read_text())
            assert run["status"] == "finished" and run["participant_unchanged"] and run["evaluator_unchanged"]
            attempt = path.name.removesuffix(".run.json")
            score = read(f"{name}/attempts/{attempt}.score.json")
            generation = int(Path(run["snapshot_root"]).name.rsplit("_", 1)[1]) if "snapshot_root" in run else read(f"{name}/status.json").get("generation", 0)
            history[name].append(dict(attempt=attempt, generation=generation, model=run["model"],
                                      elapsed_seconds=run["elapsed_seconds"], timed_out=run["timed_out"],
                                      score_file=f"attempts/{attempt}.score.json", **compact(score)))
    status = read("concept_1/status.json")
    status.update(status=classification, retained_as_hard=True, evaluator_valid=True,
                  solvability="demonstrated_on_frozen_evaluator" if passing else "unknown",
                  solvability_demonstrated=bool(passing), known_passing_current_generation_solution=bool(passing),
                  baseline_score=compact(baseline), fresh_attempts=history["concept_1"],
                  current_fresh_attempt="v_3", current_fresh_score=compact(current),
                  independent_confirmation=confirmation, private_portfolio=proofs,
                  substantive_failed_capability=failed_capability,
                  core_target_shortfall_fraction=1 - current["core_score"] / .25,
                  worst_family_target_shortfall_fraction=1 - current["worst_family_score"] / .20,
                  final_reason="Valid one-hour submission misses both quality targets; independent confirmation agrees. Normal-efficiency and acquisition constraints pass. No infeasibility claim is made.",
                  scope="The decision concerns the frozen generation-2 target. Passing solutions to earlier generations do not demonstrate this target's solvability.")
    replace_text(ROOT / "concept_1/status.json", json.dumps(status, indent=2) + "\n")
    statuses = {name: read(f"{name}/status.json")["status"] for name in history}
    assert statuses["concept_2"] == statuses["concept_3"] == "solved"
    root_status = dict(final_status=classification, accepted=True, selected_concept="concept_1",
                       selected_generation=2, selected_participant="concept_1/participant",
                       selected_evaluator="concept_1/evaluator/evaluate.py", solvability=status["solvability"],
                       built_concepts=3, internally_considered_concepts=10,
                       verification_modes={"concept_1": "A_BASELINE_IMPROVEMENT", "concept_2": "B_COUNTEREXAMPLE", "concept_3": "D_HIDDEN_PREDICTION"},
                       fresh_model="ultima-alpha", per_attempt_limit_seconds=3600,
                       isolated_attempts=sum(len(records) for records in history.values()),
                       ratchet_generations={"concept_1": 2, "concept_2": 1, "concept_3": 0},
                       concept_statuses=statuses, scores=history, substantive_failed_capability=failed_capability,
                       final_package_audit="authoring/final_package_audit.json",
                       final_process_audit="authoring/final_process_audit.json",
                       finalized_at=datetime.now(timezone.utc).isoformat())
    replace_text(ROOT / "status.json", json.dumps(root_status, indent=2) + "\n")
    first_design = read("concept_1/attempts/v_1.score.json")
    second_design = read("concept_1/attempts/v_2.score.json")
    first_witness = read("concept_2/attempts/v_1.score.json")
    second_witness = read("concept_2/attempts/v_2.score.json")
    witness_baseline = read("concept_2/adversary/baseline_evaluation.json")
    witness_ratchet_baseline = read("concept_2/adversary/generation_1/baseline_score.json")
    prediction = read("concept_3/attempts/v_1.score.json")
    prediction_baseline = read("concept_3/status.json")["baseline"]
    broad_prediction = read("concept_3/adversary/champion_search/final_report.json")
    broad_witness = read("concept_2/adversary/generation_2/champion_search/final_report.json")
    private_result = "passes" if private["passed"] else "does not pass"
    portfolio_result = ("A privately selected alternative artifact passes the frozen target."
                        if portfolio["passing_proof_found"] else
                        "Two other static design artifacts from the completed fresh attempt also fail.")
    solvability_result = ("**Solvability is demonstrated by a private static design on the frozen evaluator.**"
                          if passing else
                          "**Solvability of the retained target remains unknown; no impossibility claim is made.**")
    report = f'''# Hardness-discovery report

## Concepts and verification modes

| Concept | Primary mode | Ratchet generations | Final status | Solvability |
|---|---|---:|---|---|
| 1. Loss-resilient quantum characterization allocation | A — baseline improvement | 2 | `{classification}` | {status["solvability"]} for the retained target |
| 2. Phase-robust coherent-leakage counterexample | B — counterexample/falsification | 1 | `solved` | Demonstrated by isolated fresh agents |
| 3. Finite-shot quantum-memory prediction | D — hidden prediction | 0 | `solved` | Demonstrated by a data-only fresh learner |

Three concepts were built from ten considered concepts. Six isolated `ultima-alpha` attempts used a one-hour limit each.

## Baseline, champion, and fresh-agent scores

Pairs in the score columns are **core / worst-family**. Generations 0 and 1 of concept 1 use fractional risk reduction; generation 2 uses champion-intact risk divided by submitted worst-three-loss risk. Concept 2 scores are absolute prediction-probability gaps, but every physical/calibration/leakage constraint must also pass.

| Concept / generation | Supplied baseline | Fresh score | Fresh result |
|---|---|---|---|
| 1 / 0 | 0 / 0 reduction; mean intact risk 13.203226 | {first_design["core_score"]:.6f} / {first_design["worst_family_score"]:.6f} | Passed; became champion 1 |
| 1 / 1 | 0 / 0 reduction; mean two-loss risk 528.085560 | {second_design["core_score"]:.6f} / {second_design["worst_family_score"]:.6f} | Passed; became champion 2 |
| 1 / 2 | {baseline["core_score"]:.8f} / {baseline["worst_family_score"]:.8f} | {current["core_score"]:.6f} / {current["worst_family_score"]:.6f} | Valid; failed fixed 0.25 / 0.20 targets |
| 2 / 0 | {witness_baseline["core_score"]:.6f} / {witness_baseline["worst_family_score"]:.6f}; insufficient gap | {first_witness["core_score"]:.6f} / {first_witness["worst_family_score"]:.6f} | Passed all five scenarios |
| 2 / 1 | {witness_ratchet_baseline["core_score"]:.6f} / {witness_ratchet_baseline["worst_family_score"]:.6f}; fails calibration/leakage constraints | {second_witness["core_score"]:.6f} / {second_witness["worst_family_score"]:.6f} | Passed all 21 scenarios |
| 3 / 0 | RMSE {prediction_baseline["macro_rmse"]:.9f} | RMSE {prediction["macro_rmse"]:.9f}; worst family 0.000727309 | Passed every predictive target |

The retained attempt reached the 3,600-second cutoff with a valid design. Its intact-risk ratio was **{current["intact_mean_ratio"]:.6f}**, within the 1.20 guard; it used exactly **{current["execution_ticks"]:,} ticks and {current["distinct_circuits"]} circuits**. Its mean three-loss risk was **{current["mean_loss_risk"]:.6f}**, or **{current["loss_to_champion_intact_ratio"]:.6f}×** champion-intact risk instead of the allowed 4×. Its worst-regime inflation was **{1/current["worst_family_score"]:.6f}×** instead of 5×.

## Counterexample-search results

- **Concept 1, first ratchet:** loss of two selected records exposes severe information concentration in the original champion. A 3,000-point private sweep supports the loss-resilience successor.
- **Concept 1, second ratchet:** the two-loss champion remains effective for its original contract, but three losses raise its mean risk from **4.917090 intact to 100,059.914230** over 3,000 operating points. An independent 600-point sweep gives **112,359.172180**. The dominant triple removes nearly all Y-gate z-axis sensitivity in 2,616/3,000 points; secondary failures affect the X gate's z-axis sensitivity. Additional boundary tests and independent dense/rank-update checks corroborate the mechanism. The new generation explicitly requires three-loss usability rather than merely halving a nearly singular baseline's risk.
- **Retained-attempt confirmation:** a disjoint 600-point ensemble scores **{confirmation["core_score"]:.6f} / {confirmation["worst_family_score"]:.6f}**, with intact ratio **{confirmation["intact_mean_ratio"]:.6f}**; it also fails. No target changed after launch.
- **Concept 2:** independent phase drift defeats the first champion; a bounded uniform-rescaling search finds no repair for the selected ±0.008-radian case. The next champion survives **{broad_witness["total_grid_random_scenarios"]:,} grid/random scenarios plus {broad_witness["local_scenario_evaluations"]:,} evaluations in {broad_witness["local_optimizer_runs"]} local searches** inside the unchanged uncertainty box. Independently reproduced extrema and rounding tests reveal no genuine further failure. This is finite evidence, not a whole-box proof.
- **Concept 3:** **12 campaigns, 48 devices, and 98,304 held-out queries** reveal no substantial champion failure. Worst campaign RMSE is **{broad_prediction["worst_campaign_macro_rmse"]:.9f}**, worst family **{broad_prediction["worst_family_rmse"]:.9f}**, and worst device/family cell **{broad_prediction["worst_device_family_rmse"]:.9f}**. No scientifically justified successor was selected.

## Solvability and final decision

**Retain concept 1, generation 2, as `{classification}`.** The fresh score falls **{status["core_target_shortfall_fraction"]:.2%}** below the fixed core target and **{status["worst_family_target_shortfall_fraction"]:.2%}** below the worst-family target. This is a substantive quality failure, not malformed output, unavailable software, or an acquisition-budget violation.

The current-generation private search scores **{private["core_score"]:.6f} / {private["worst_family_score"]:.6f}**, with intact ratio **{private["intact_mean_ratio"]:.6f}**; it {private_result}. {portfolio_result} {solvability_result} Passing designs for earlier generations do not establish this target's achievability.

The substantive capability missed is **constrained, loss-resilient experimental design meeting simultaneous average and worst-regime information-retention requirements without sacrificing normal-operation efficiency**. Both counterexample construction and finite-shot prediction were solved and are not retained as hard tasks.
'''
    replace_text(ROOT / "REPORT.md", report)
    print(json.dumps({key: root_status[key] for key in ("final_status", "selected_concept", "solvability", "isolated_attempts", "ratchet_generations")}, indent=2))


if __name__ == "__main__":
    main()
