from datetime import datetime, timezone
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NAMES = {1: "Sample-specific dynamical-fraction prediction", 2: "Spectrally matched disorder layouts",
         3: "Robust spectral-window counterexample"}
MODES = {1: "D_HIDDEN_PREDICTION", 2: "C_WITNESS_OR_DESIGN_CONSTRUCTION",
         3: "B_COUNTEREXAMPLE_OR_FALSIFICATION"}
CAPABILITIES = {
    1: "Finite-size transfer of sample-specific many-body relaxation predictions under a strict inference budget.",
    2: "Robust histogram-preserving permutation design: both attempts achieve every relaxation-separation condition but fail spectral matching on unseen calibration perturbations.",
    3: "Finding a spectral-window discrepancy that persists under independent perturbations rather than overfitting a public calibration bank."}


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def score_summary(report):
    keys = ("core_score", "worst_family_score", "passed", "valid", "evaluator_valid", "reason", "runtime_seconds", "resource_score")
    return {key: report.get(key) for key in keys}


def metric(value):
    return "n/a" if value is None else f"{value:.6f}"


def score_pair(report):
    return metric(report["core_score"]) + " / " + metric(report["worst_family_score"])


def main():
    decisions = load(ROOT / "authoring/ratchet_stop_decisions.json")
    summaries = {}
    table = []
    champions = []
    total_attempts = 0
    for number in (1, 2, 3):
        concept = ROOT / f"concept_{number}"
        promotion = concept / "promotion.json"
        active = load(promotion)["current_generation"] if promotion.exists() else 1
        generations = {}
        for generation in range(1, active + 1):
            source = concept if active == 1 else concept / "generations" / f"generation_{generation}"
            baseline = score_summary(load(source / "adversary/baseline_score.json"))
            assert baseline["valid"] and baseline["evaluator_valid"]
            attempts = []
            for path in sorted((concept / "attempts").glob("v_*.run.json")):
                metadata = load(path)
                if metadata["generation"] != generation:
                    continue
                assert "returncode" in metadata and metadata["participant_unchanged"]
                report = load(path.with_name(path.name.replace(".run.json", ".score.json")))
                assert report["evaluator_valid"]
                attempt = {"attempt": metadata["attempt"], "model": metadata["model"],
                           "limit_seconds": metadata["limit_seconds"], "elapsed_seconds": metadata["seconds"],
                           "timed_out": metadata["timed_out"], **score_summary(report)}
                attempts.append(attempt)
            assert len(attempts) >= 2
            total_attempts += len(attempts)
            proof_path = source / "adversary" / ("portfolio_score.json" if number == 2 else "privileged_score.json")
            proof = score_summary(load(proof_path)) if proof_path.exists() else None
            passed = [attempt for attempt in attempts if attempt["passed"]]
            demonstrated = bool(passed) or bool(proof and proof["passed"] and proof["evaluator_valid"])
            status = "solved" if passed else "hard_verified_achievable" if demonstrated else "hard_open_candidate"
            champion = min(passed, key=lambda result: result["core_score"]) if number == 1 and passed else max(passed, key=lambda result: result["core_score"]) if passed else None
            state = {"concept": NAMES[number], "mode": MODES[number], "generation": generation,
                     "ratchet_generations": generation - 1, "status": status, "evaluator_valid": True,
                     "baseline_score": baseline, "fresh_attempts": attempts, "fresh_champion": champion,
                     "privileged_score": proof, "solvability_demonstrated": demonstrated,
                     "solvability": "demonstrated" if demonstrated else "unknown",
                     "targets_fixed_before_fresh_launch": True, "participant_unchanged": True,
                     "selected_for_retention": number == 2,
                     "capability_tested": CAPABILITIES[number]}
            generations[str(generation)] = state
            if active > 1:
                save(source / "status.json", state)
            fresh_text = "; ".join(f"v{attempt['attempt']}: {score_pair(attempt)} ({'pass' if attempt['passed'] else 'fail'})"
                                   for attempt in attempts)
            table.append(f"| C{number} g{generation} | {MODES[number].split('_')[0]} | {score_pair(baseline)} | {fresh_text} |")
            if champion:
                champions.append(f"- C{number} g{generation}: fresh v{champion['attempt']}, {score_pair(champion)}, {champion['runtime_seconds']:.3f}s evaluation.")
            if proof and proof["passed"]:
                champions.append(f"- C{number} g{generation}: privileged {'portfolio' if number == 2 else 'witness'}, {score_pair(proof)}, {proof['runtime_seconds']:.3f}s evaluation.")
        state = dict(generations[str(active)])
        state["generation_history"] = generations
        state["ratchet_stop"] = decisions[f"concept_{number}"]
        if state["status"] == "solved":
            assert not state["ratchet_stop"]["new_generation_required"]
            assert state["ratchet_stop"]["stress_evidence"]
        if number == 2:
            state.update({"verification_evidence": "adversary/portfolio_score.json",
                          "privileged_witness": "adversary/portfolio_candidate/design.json",
                          "independent_verification": "adversary/portfolio_independent_driver.json",
                          "search": {"initial_layouts": 1800, "initial_robust_pairs": 240,
                                     "cached_bank2_layouts": 71, "recombined_ordered_pairs": 5041,
                                     "passing_bank2_pairs": 2}})
        save(concept / "status.json", state)
        summaries[f"concept_{number}"] = state
    selected = summaries["concept_2"]
    assert selected["status"] == "hard_verified_achievable"
    root_status = {"paper": "The many-body localization phase transition", "arxiv_id": "1010.1992",
                   "completed_utc": datetime.now(timezone.utc).isoformat(), "discovery_complete": True,
                   "status": selected["status"], "selected_concept": "concept_2",
                   "concepts_considered": 10, "concepts_built": 3, "fresh_agent_model": "ultima-alpha",
                   "fresh_limit_seconds": 3600, "fresh_attempt_count": total_attempts,
                   "verification_modes": {name: state["mode"] for name, state in summaries.items()},
                   "concept_statuses": {name: state["status"] for name, state in summaries.items()},
                   "ratchet_generations": {name: state["ratchet_generations"] for name, state in summaries.items()},
                   "active_generation": {name: state["generation"] for name, state in summaries.items()},
                   "solvability": {name: state["solvability"] for name, state in summaries.items()},
                   "evaluator_valid": True, "solvability_demonstrated": True,
                   "substantive_failure": CAPABILITIES[2]}
    save(ROOT / "status.json", root_status)
    save(ROOT / "selection.json", {"concept": "concept_2", "mode": MODES[2],
                                    "task": "concept_2/participant/TASK.md", "status": selected["status"],
                                    "solvability": "demonstrated", "passing_certificate": "concept_2/adversary/portfolio_candidate/design.json",
                                    "scoring_evidence": "concept_2/adversary/portfolio_score.json",
                                    "independent_check": "concept_2/adversary/portfolio_independent_driver.json",
                                    "reason": CAPABILITIES[2]})
    lines = ["# Hardness discovery report", "", "## Concepts and verification modes",
             "", "- C1: sample-specific dynamical-fraction prediction — D, hidden prediction.",
             "- C2: spectrally matched disorder layouts — C, witness/design construction.",
             "- C3: robust spectral-window counterexample — B, counterexample/falsification.", "",
             "## Baseline and fresh-agent scores", "",
             "Scores are core / worst family. C1 uses RMSE (lower is better; targets 0.035 / 0.050). C2 uses normalized constraint scores (100 / 100 and every condition must pass). C3 uses signed discrepancy (targets 0.060 / 0.050 plus base and coverage constraints). Each generation has two isolated ultima-alpha attempts with a one-hour limit.", "",
             "| Concept / generation | Mode | Baseline | Fresh attempts |", "|---|---|---|---|", *table, "",
             "C1 g1 v1 exceeded the 3-second inference budget at 3.005s and has no accuracy score; it is not used as evidence of scientific hardness. C2 v1 and C3 g2 v3 were stopped at the one-hour deadline and their stable, valid checkpoints were scored.", "",
             "## Champion and privileged scores", "", *champions, "",
             "## Counterexample search results", "",
             "- C1 g1: a 1,760-realization private bank exposed L14 size-transfer failure. Merely fixing unsupported-size dispatch still gives RMSE 0.058231 / 0.072183; the raw unsupported-size failure is not treated as scientific evidence. Generation 2 supplies new L14 public data and keeps the numerical targets fixed.",
             "- C2: 1,800 privately searched layouts and 240 robust pairs did not initially yield a complete design. Recombining 71 cached bank-two layouts over 5,041 ordered pairs finds two passing pairs. A three-bank portfolio passes every requirement; independent full-spectrum LAPACK verification agrees within 4.86e-13. Both fresh designs meet all relaxation-separation conditions, but respectively miss spectral matching in seven and five of nine families.",
             "- C3 g1: both fresh witnesses pass their initial grader, but the best-core champion passes 0/16 independent replication banks (mean core 0.049581); the earlier v2 champion also passes 0/16. Both fail the frozen generation-two bank. Generation 2 uses separate, independent 128-probe calibration and grading banks, with unchanged numerical thresholds.",
             "- C3 g2: privileged scale search tests 30 candidates and finds one passing witness; an independent LAPACK driver agrees within 4.62e-13."]
    for number in (1, 3):
        lines.append(f"- C{number} final champion stress: " + decisions[f"concept_{number}"]["summary"])
    lines.extend(["", "## Ratchets and final status", ""])
    for number in (1, 2, 3):
        state = summaries[f"concept_{number}"]
        lines.append(f"- C{number}: {state['ratchet_generations']} ratchet generation(s); `{state['status']}`; solvability {state['solvability']}.")
    lines.extend(["", "## Substantive capability failure", "",
                  "Retained C2 is `hard_verified_achievable`: neither fresh agent constructs a fully valid robust design, while the privileged portfolio does. The failure is selecting spatial arrangements that preserve a field histogram and keep adjacent-gap statistics matched across unseen perturbations while maintaining a large dynamical separation. It is not a format failure, missing implementation formula, or numerical-precision artifact.", ""])
    (ROOT / "FINAL_REPORT.md").write_text("\n".join(lines))
    print(json.dumps(root_status), flush=True)


if __name__ == "__main__":
    main()
