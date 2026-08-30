from datetime import datetime, timezone
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return json.loads((ROOT / relative).read_text())


def write(relative, value):
    (ROOT / relative).write_text(json.dumps(value, indent=2) + "\n")


def main():
    compiler = read("concept_1/adversary/scored/v_2/score.json")
    compiler_audit = read("concept_1/adversary/challenger_2_audit/score.json")
    ratchet = read("concept_1/adversary/ratchet_1/commitment.json")
    witness = read("concept_2/adversary/scored/v_1/score.json")
    private_witness = read("concept_2/adversary/final_certificate_recheck.json")
    calibration = read("concept_3/adversary/scored/v_1/score.json")
    if not (compiler["valid"] and not compiler["passed"] and compiler_audit["valid"] and witness["valid"] and not witness["passed"] and private_witness["passed"] and calibration["passed"]):
        raise ValueError("Unexpected experimental outcome; review decisions instead of auto-finalizing")
    timestamp = datetime.now(timezone.utc).isoformat()
    excess_cost = (1 - compiler["core_score"]) / (1 - compiler["targets"]["core_score"]) - 1
    needed_reduction = 1 - (1 - compiler["targets"]["core_score"]) / (1 - compiler["core_score"])
    compiler_decision = {
        "status": "hard_open_candidate",
        "verification_mode": "A",
        "decided_at_utc": timestamp,
        "baseline_core_score": 0.0,
        "baseline_worst_family_score": 0.0,
        "target": compiler["targets"],
        "previous_champion_original_core": ratchet["old_champion_original_core"],
        "previous_champion_ratchet_core": ratchet["old_champion_focused_core"],
        "previous_champion_ratchet_worst_family": ratchet["old_champion_focused_worst_family"],
        "fresh_core_score": compiler["core_score"],
        "fresh_worst_family_score": compiler["worst_family_score"],
        "fresh_resource_score": compiler["resource_score"],
        "fresh_max_case_seconds": compiler["max_case_seconds"],
        "valid_cases": len(compiler["cases"]),
        "normalized_remaining_cost_excess_over_target": excess_cost,
        "additional_normalized_cost_reduction_needed": needed_reduction,
        "fresh_attempts": 2,
        "model": "ultima-alpha",
        "limit_seconds": 3600,
        "ratchet_generations": 1,
        "known_passing_general_compiler": False,
        "solvability": "unknown for a generic compiler meeting the fixed quality and runtime targets",
        "private_per_instance_certificates": {"mean_reduction": ratchet["witness_core"], "interpretation": "Exact hidden construction circuits establish objective headroom, not a passing general compiler."},
        "counterexample_search": {"prior_champion_cases": 152, "certified_cost_gaps": 32, "independent_challenger_cases": compiler_audit["case_count"], "independent_core_score": compiler_audit["core_score"], "independent_worst_family_score": compiler_audit["worst_family_score"], "independent_passed": compiler_audit["passed"], "independent_valid": compiler_audit["valid"]},
        "evaluator_valid": True,
        "capability_failure": "Generalizing cost-efficient shared-parity and common-basis synthesis to hidden calibrated sparse graphs within a 15-second compilation budget. All circuits and runtimes were valid; the fixed overall quality target was missed, while the worst-family floor was met.",
        "score_report": "adversary/scored/v_2/score.json",
        "audit_report": "adversary/challenger_2_audit/score.json",
        "target_commitment": "adversary/ratchet_1/commitment.json"
    }
    write("concept_1/adversary/hardness_decision.json", compiler_decision)
    compiler_status = dict(compiler_decision, concept="hardware_aware_phase_compilation", selected_as_primary=False)
    write("concept_1/status.json", compiler_status)
    root_status = {
        "paper": "Quantum computing with Qiskit",
        "arxiv_id": "2405.08810",
        "completed_at_utc": timestamp,
        "status": "hard_verified_achievable",
        "selected_concept": "concept_2",
        "participant_task": "concept_2/participant/TASK.md",
        "evaluator": "concept_2/evaluator/evaluate.py",
        "solvability": "demonstrated by private exact witnesses for all four native-CX targets",
        "concepts_screened": 9,
        "concepts_built": 3,
        "verification_modes": ["A", "C", "E"],
        "concept_statuses": {"concept_1": "hard_open_candidate", "concept_2": "hard_verified_achievable", "concept_3": "solved"},
        "fresh_agent_model": "ultima-alpha",
        "fresh_agent_attempts": 4,
        "fresh_agent_limit_seconds": 3600,
        "ratchet_generations": {"concept_1": 1, "concept_2": 0, "concept_3": 0},
        "calibration_ratchet_reason": "264 private challenge episodes did not establish a trustworthy aggregate failure; no unsupported harder generation was manufactured.",
        "report": "FINAL_REPORT.md",
        "isolation_validation": "authoring/isolation_validation.json",
        "scoring_sandbox_validation": "authoring/sandbox_validation.json",
        "final_audit": "authoring/package_audit.json"
    }
    write("status.json", root_status)
    audit_outcome = "missed" if not compiler_audit["passed"] else "met"
    report = f"""# Hardness-discovery report

## Concepts, scores, and decisions

Compiler scores are mean / worst-family cost reduction (higher is better). Calibration scores are mean / worst-family NRMSE (lower is better).

| Concept and verification mode | Baseline / prior champion | Fresh ultima-alpha result | Ratchets | Final status | Solvability |
| --- | --- | --- | --- | --- | --- |
| 1. Hardware-aware phase compilation — A, baseline improvement | Baseline 0% / 0%; prior champion on ratchet suite 75.11% / 73.44% | {100 * compiler['core_score']:.2f}% / {100 * compiler['worst_family_score']:.2f}%; target 82% / 80%; 32/32 valid | 1 | hard_open_candidate | Generic passing compiler unknown |
| 2. Native-CX linear synthesis — C, witness construction | Weak baseline 0/4; private feasible witness 4/4 | 2/4 accepted; all four exact and within CX-count caps | 0 | hard_verified_achievable | Demonstrated |
| 3. Adaptive cross-resonance calibration — E, active experiment design | Baseline 0.07761 / 0.11499 | {calibration['core_score']:.5f} / {calibration['worst_family_score']:.5f}; target ≤0.060 / ≤0.090; 32/32 valid | 0 | solved | Demonstrated by fresh champion |

There were four isolated fresh-agent attempts, each limited to one hour. The first compiler attempt passed its original 40% / 25% target with 63.57% / 58.69%, before the private ratchet. The witness attempt exhausted its hour; the other three completed normally.

## Counterexample searches

- Compiler: 96 broad cases, 24 initial basis-barrier cases, then 32 focused cases exposed 32 certified cost gaps in the first champion. Exact private construction circuits reach 82.88% mean reduction on the focused suite, but are not a general compiler. This justified the single ratchet; thresholds were frozen before the new fresh attempt.
- Compiler challenger: an additional 64 independently seeded, headroom-filtered workloads {audit_outcome} the unchanged target, scoring {100 * compiler_audit['core_score']:.2f}% mean / {100 * compiler_audit['worst_family_score']:.2f}% worst-family reduction. These were generated before the challenger score was observed and never provided to it.
- Native-CX witness: no full-task passing fresh champion existed, so no ratchet was required. Independent dense-matrix and dependency-DAG checks validate all four private witnesses and reproduce both fresh depth-cap failures.
- Calibration: 128 broad episodes, 72 independent-noise repeats, and a 64-episode continuous-neighborhood/frame audit produced no trustworthy aggregate or resource failure. One noisy point did not generalize into a failing regime. No artificial harder generation was created.

## Substantive failures and final selection

- Compiler: exact semantics and runtime compliance succeeded, but hidden workload quality remained {100 * needed_reduction:.2f}% short in the further reduction needed from its remaining normalized cost. Maximum case runtime was {compiler['max_case_seconds']:.2f}/15 seconds. The failed capability is budgeted shared-parity/common-basis synthesis that generalizes beyond public workloads; passing generic solvability remains unknown.
- Native-CX witness: the fresh artifact reached count/depth 218/81 on the 30-qubit target and 255/85 on the 34-qubit target, versus caps 227/78 and 261/79. Private feasible artifacts achieve 214/72 and 246/73. The failed capability is jointly discovering a low-count native factorization and enough duration-aware parallelism, not correctness or output formatting.
- Calibration: no capability failure was established at the fixed target; the fresh adaptive controller solved it and survived the broader audits.

**Selected task: concept_2. Final status: hard_verified_achievable.** Concept 1 is additionally retained as hard_open_candidate; concept 3 is recorded as solved, not claimed hard.
"""
    (ROOT / "FINAL_REPORT.md").write_text(report)
    print(json.dumps(root_status, indent=2))


if __name__ == "__main__":
    main()
