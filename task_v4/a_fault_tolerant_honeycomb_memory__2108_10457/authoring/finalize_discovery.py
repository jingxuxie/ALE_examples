from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_json(relative):
    return json.loads((ROOT / relative).read_text())


def write_json(relative, value):
    (ROOT / relative).write_text(json.dumps(value, indent=2) + "\n")


def score_summary(score):
    keys = ["core_score", "worst_family_score", "core_failure_ratio", "worst_family_ratio",
            "runtime_seconds", "runtime_score", "resource_score", "valid", "passed", "reason"]
    return {key: score[key] for key in keys if key in score}


def attempt_record(concept, attempt_index, generation):
    directory = f"{concept}/attempts"
    runner = read_json(f"{directory}/v_{attempt_index}_runner.json")
    score = read_json(f"{directory}/v_{attempt_index}_score.json")
    assert runner.get("finished_utc"), "Cannot finalize an unfinished attempt"
    assert runner["generation"] == generation
    assert runner["model"] == "ultima-alpha"
    assert runner["limit_seconds"] == 3600
    assert runner["elapsed_seconds"] <= 3615
    assert score["valid"], "Investigate an invalid scientific attempt before finalizing"
    if concept == "concept_2" and generation == 1:
        frozen_path = f"{concept}/generations/generation_1/evaluator/frozen.json"
    else:
        frozen_path = f"{concept}/evaluator/frozen.json"
    assert runner["participant_sha256"] == read_json(frozen_path)
    return {
        "attempt": f"v_{attempt_index}", "generation": generation, "model": runner["model"],
        "elapsed_seconds": runner["elapsed_seconds"], "timed_out": runner["timed_out"],
        "runner_sha256": runner["runner_sha256"], "score": score_summary(score),
        "runner_record": f"attempts/v_{attempt_index}_runner.json",
        "score_file": f"attempts/v_{attempt_index}_score.json",
    }


def main():
    package_audit = read_json("authoring/package_audit.json")
    runner_audit = read_json("authoring/runner_version_audit.json")
    assert package_audit["passed"] and runner_audit["passed"]
    assert read_json("authoring/final_attempt_audit.json")["passed"]
    assert read_json("concept_2/adversary/reflection_equivalence.json")["passed"]
    for concept in ["concept_1", "concept_2", "concept_3"]:
        frozen = read_json(f"{concept}/evaluator/frozen.json")
        for relative, digest in frozen["sha256"].items():
            assert hashlib.sha256((ROOT / concept / relative).read_bytes()).hexdigest() == digest
    assert (ROOT / "concept_2/evaluator/design_common.py").read_bytes() == (
        ROOT / "concept_2/participant/workspace/design_common.py"
    ).read_bytes()
    histories = {
        "concept_1": [attempt_record("concept_1", 1, 1)],
        "concept_2": [attempt_record("concept_2", 1, 1), attempt_record("concept_2", 2, 2),
                      attempt_record("concept_2", 3, 2)],
        "concept_3": [attempt_record("concept_3", 1, 1)],
    }
    assert histories["concept_1"][0]["score"]["passed"]
    assert histories["concept_3"][0]["score"]["passed"]
    assert histories["concept_2"][0]["score"]["passed"]
    dense_attempts = histories["concept_2"][1:]
    assert not any(attempt["score"]["passed"] for attempt in dense_attempts), "A solved ratchet needs a new decision"
    dense_portfolio = read_json("concept_2/adversary/private_dense_portfolio/report.json")
    structural = read_json("concept_2/adversary/private_dense_portfolio/structural_report.json")
    assert not dense_portfolio["known_passing_solution"]
    assert not structural["known_passing_solution"]
    private_candidates = dense_portfolio["candidates"] + structural["full_frozen_evaluations"]
    assert not any(candidate["score"]["passed"] for candidate in private_candidates)
    private_best = max(private_candidates, key=lambda candidate: min(
        candidate["score"]["core_score"] / 0.85, candidate["score"]["worst_family_score"] / 0.60))
    best_fresh = max(dense_attempts, key=lambda attempt: min(
        attempt["score"]["core_score"] / 0.85, attempt["score"]["worst_family_score"] / 0.60))
    baseline = read_json("concept_2/attempts/baseline_generation_2_score.json")
    frozen_baseline = read_json("concept_2/evaluator/baseline_score.json")
    assert baseline["valid"] and not baseline["passed"]
    assert all(baseline[key] == frozen_baseline[key] for key in ["core_score", "worst_family_score"])
    certificates = read_json("concept_2/adversary/ratchet_1_counterexamples.json")
    confirmation = read_json("concept_2/adversary/dense_failure_confirmation.json")
    assert all(candidate["upper_endpoint_below_required_group_floor"]
               for candidate in confirmation["candidates"].values())
    capability = ("Construct a static local-Clifford supercell that improves dense heralded phase-erasure "
                  "correctability while preserving all four logical Pauli coordinates across all three sizes; "
                  "the 24-qubit, 0.32-density group remains the substantive bottleneck.")
    status = {
        "mode": "C", "status": "hard_open_candidate", "current_generation": 2,
        "ratchet_generations": 1, "previous_generation_status": "solved",
        "fixed_targets": {"core_score_min": 0.85, "every_group_score_min": 0.60,
                          "hidden_supports_per_group": 4096, "groups": 9,
                          "development_seconds_per_fresh_attempt": 3600},
        "baseline_score": score_summary(baseline),
        "baseline_replay": "attempts/baseline_generation_2_score.json",
        "fresh_agent_attempts": histories["concept_2"],
        "best_current_fresh_attempt": best_fresh["attempt"],
        "best_private_candidate": {"artifact": private_best["artifact"],
                                   "score": score_summary(private_best["score"])},
        "known_passing_solution": False, "solvability_demonstrated": False,
        "solvability": "Unknown for the retained dense generation; nominal-generation success is not a dense-generation witness.",
        "evaluator_valid": True,
        "validation": ["adversary/validation.json", "adversary/fault_replay.json",
                       "adversary/dense_failure_confirmation.json", "adversary/reflection_equivalence.json",
                       "../authoring/package_audit.json"],
        "adversarial_search": {
            "broad_profiles": "adversary/broad_private/champion_1.json",
            "exact_zero_syndrome_logical_fault_certificates": len(certificates["certificates"]),
            "certificates": "adversary/ratchet_1_counterexamples.json",
            "private_annealing_seeds": dense_portfolio["seeds"],
            "seconds_per_seed": dense_portfolio["seconds_per_seed"],
            "unique_structural_candidates_screened": structural["unique_candidates"],
            "structural_finalists_evaluated_on_frozen_tests": len(structural["full_frozen_evaluations"]),
            "private_passing_candidates": 0,
            "interpretation": "No global infeasibility claim: private searches and fresh finite-sample scans do not prove impossibility.",
        },
        "capability_on_which_agents_failed": capability,
        "decision_reason": "Both independent one-hour fresh attempts produce valid artifacts but miss the fixed core and/or worst-group targets; no passing dense design is known.",
        "completed_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json("concept_2/status.json", status)
    for concept, history in histories.items():
        write_json(f"{concept}/attempts/status.json", {"status": "complete", "attempts": history})
    root_status = {
        "paper": "A Fault-Tolerant Honeycomb Memory", "arxiv": "2108.10457",
        "status": "hard_open_candidate", "retained_concept": "concept_2",
        "retained_generation": 2, "solvability_demonstrated": False, "solvability": "unknown",
        "built_concepts": 3, "verification_modes": ["A", "C", "D"],
        "scientific_fresh_attempts": 5, "excluded_infrastructure_startup_retries": 1,
        "ratchet_generations": {"concept_1": 0, "concept_2": 1, "concept_3": 0},
        "concept_statuses": {"concept_1": "solved", "concept_2": "hard_open_candidate", "concept_3": "solved"},
        "fresh_attempt_manifest": histories,
        "report": "REPORT.md", "evaluator_audit": "authoring/package_audit.json",
        "runner_version_audit": "authoring/runner_version_audit.json",
        "final_attempt_audit": "authoring/final_attempt_audit.json",
        "capability_on_which_agents_failed": capability, "completed_utc": status["completed_utc"],
    }
    write_json("status.json", root_status)
    decoder = histories["concept_1"][0]["score"]
    prediction_baseline = read_json("concept_3/evaluator/baseline_score.json")
    prediction = histories["concept_3"][0]["score"]
    nominal = histories["concept_2"][0]["score"]
    decoder_audit = read_json("concept_1/adversary/broad_native/summary.json")
    prediction_audit = read_json("concept_3/adversary/champion_1_fine_grained.json")
    lines = [
        "# Hardness-discovery report", "", "## Concepts and verification modes", "",
        "| Concept | Primary verification mode | Final status |",
        "|---|---|---|",
        "| 1: Circuit-level correlated decoding | A: baseline improvement | solved |",
        "| 2: Dense heralded-erasure honeycomb design | C: witness/design construction | hard_open_candidate |",
        "| 3: Held-out paper experiment prediction | D: hidden prediction | solved |", "",
        "## Baseline, champion, and fresh-agent scores", "",
        f"- Concept 1: baseline family-balanced/worst failure ratios 1.000000 / 1.000000; fresh champion {decoder['core_failure_ratio']:.6f} / {decoder['worst_family_ratio']:.6f}. Lower is better; targets 0.80 / 0.95 were met.",
        f"- Concept 2 nominal generation: identity baseline core/worst 0.277778 / 0.050781; fresh champion {nominal['core_score']:.6f} / {nominal['worst_family_score']:.6f}, passing.",
        f"- Concept 2 retained dense generation: supplied champion baseline core/worst {baseline['core_score']:.6f} / {baseline['worst_family_score']:.6f}. Fixed targets remain at least 0.85 / 0.60, across 36,864 hidden supports.",
    ]
    for attempt in dense_attempts:
        score = attempt["score"]
        lines.append(f"- Concept 2 independent fresh attempt `{attempt['attempt']}`: core/worst {score['core_score']:.6f} / {score['worst_family_score']:.6f}; valid, not passing; {attempt['elapsed_seconds']:.1f} seconds of the one-hour allowance.")
    lines.extend([
        f"- Concept 2 private portfolio best: core/worst {private_best['score']['core_score']:.6f} / {private_best['score']['worst_family_score']:.6f}; not passing.",
        "- The first dense fresh artifact is exactly reflection-equivalent to the supplied champion. Independent bidirectional response-space checks establish equal IID population performance; its small finite-sample score gain is not a genuine robustness improvement.",
        f"- Concept 3: baseline core/worst {prediction_baseline['core_score']:.6f} / {prediction_baseline['worst_family_score']:.6f}; fresh champion {prediction['core_score']:.6f} / {prediction['worst_family_score']:.6f}. Worst-score target at least 0.50 was met.", "",
        "## Counterexample search results", "",
        f"- Concept 1: 98,304 additional source-native shots across 12 broader cases. Champion balanced/worst failure ratios {decoder_audit['core_failure_ratio']:.6f} / {decoder_audit['worst_family_ratio']:.6f}; maximum request time {decoder_audit['max_request_seconds']:.3f} seconds. No violation of the fixed target.",
        f"- Concept 2: broad physical erasure sweeps isolated the dense-IID failure regime; {len(certificates['certificates'])} exact flagged-support fault combinations have zero syndrome and nonzero logical action. Three 300-second private search seeds plus {structural['unique_candidates']:,} structural candidates screened ({len(structural['full_frozen_evaluations'])} finalists fully scored) produced no passing dense design.",
        "- Concept 2: independent 32,768-support worst-group confirmation gives the first dense attempt 0.484039 correctability, with a 99% Wilson interval [0.476932, 0.491153], well below 0.60. This is post-submission validation, not a new scoring condition.",
        f"- Concept 3: finer distance stratification of all 692 held-out observations gives worst score {prediction_audit['fine_grained_worst_score']:.6f}, with {prediction_audit['factor_two_residual_failures']} factor-two residual failures after accounting for count uncertainty. No justified further ratchet was found.", "",
        "## Ratchets, final status, and solvability", "",
        "- Ratchet generations: concept 1 = 0; concept 2 = 1 (two total task generations); concept 3 = 0. The two dense attempts are replications of the same frozen generation, not successive ratchets.",
        "- Retain concept 2 generation 2 as `hard_open_candidate`. Solvability is unknown; no dense-generation passing construction is known, and no impossibility proof is claimed.",
        "- Concepts 1 and 3 are `solved`; their fresh executable champions demonstrate achievability. Nominal concept 2 was also solved but does not demonstrate dense-generation solvability.", "",
        "## Substantive failed capability", "", capability, "",
    ])
    (ROOT / "REPORT.md").write_text("\n".join(lines))
    print(json.dumps({"status": root_status["status"], "retained_concept": "concept_2",
                      "fresh_dense_scores": [attempt["score"] for attempt in dense_attempts]}, indent=2))


if __name__ == "__main__":
    main()
