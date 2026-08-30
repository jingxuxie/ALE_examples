from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONCEPT = ROOT / "concept_1"


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def fresh_record(attempt, generation, evaluation_name="evaluation.json"):
    audit_path = CONCEPT / "attempts" / (attempt + "_audit") / "audit.json"
    grade_path = audit_path.with_name(evaluation_name)
    audit = load(audit_path)
    grade = load(grade_path)
    assert audit["state"] == "finished" and audit["participant_unchanged"]
    assert audit["model"] == "ultima-alpha" and audit["effort"] == "high"
    assert audit["return_code"] == 0 and not audit["timed_out"]
    assert audit["elapsed_seconds"] < 3600
    return {
        "attempt": attempt,
        "generation": generation,
        "model": audit["model"],
        "elapsed_seconds": audit["elapsed_seconds"],
        "summary": grade["summary"],
        "audit": str(audit_path.relative_to(CONCEPT)),
        "audit_sha256": digest(audit_path),
        "evaluation": str(grade_path.relative_to(CONCEPT)),
        "evaluation_sha256": digest(grade_path),
        "calibration_sha256": grade.get("calibration_sha256"),
    }


def main():
    freeze_path = CONCEPT / "adversary/ratchet_2_admission/freeze_manifest.json"
    freeze = load(freeze_path)
    for relative, expected in freeze["frozen_private_assets"].items():
        assert digest(CONCEPT / relative) == expected, relative
    assert digest(CONCEPT / "evaluator/hidden/calibration.json") == freeze["calibration_sha256"]
    proof_path = CONCEPT / "adversary/ratchet_2_portfolio/ACHIEVABILITY.json"
    proof = load(proof_path)
    assert proof["summary"]["passed"] and proof["summary"]["all_valid"]
    assert proof["calibration_sha256"] == freeze["calibration_sha256"]
    assert digest(CONCEPT / proof["evaluation"]) == proof["evaluation_sha256"]
    for relative, expected in proof["snapshot_sha256"].items():
        assert digest(CONCEPT / proof["snapshot"] / relative) == expected, relative
    isolation_path = ROOT / "authoring/final_isolation_audit_v3.json"
    isolation = load(isolation_path)
    assert isolation["summary"]["actual_completed_run_count"] == 15
    assert isolation["summary"]["all_completed_normally_under_3600_seconds"]
    assert not isolation["summary"]["new_concrete_blockers"]
    assert isolation["summary"]["new_manifest_and_stability_checks_pass"]
    assert isolation["summary"]["no_fresh_survivor_or_original_output_writer_observed"]
    assert set(path.name for path in ROOT.glob("concept_[0-9]*") if path.is_dir()) == {"concept_1", "concept_2", "concept_3"}
    for concept_name, attempt_count in (("concept_1", 6), ("concept_2", 8), ("concept_3", 1)):
        concept = ROOT / concept_name
        for relative in ("participant/input", "participant/workspace", "participant/baseline", "evaluator/hidden", "attempts", "champions", "adversary"):
            assert (concept / relative).is_dir(), (concept_name, relative)
        for relative in ("participant/TASK.md", "evaluator/evaluate.py", "status.json"):
            assert (concept / relative).is_file(), (concept_name, relative)
        for number in range(1, attempt_count + 1):
            audit = load(concept / "attempts" / ("v_" + str(number) + "_audit") / "audit.json")
            assert audit["state"] == "finished" and audit["participant_unchanged"]
            assert audit["empty_output_at_launch"] and audit["participant_read_only"]
            assert audit["model"] == "ultima-alpha" and audit["elapsed_seconds"] < 3600
            assert not audit["timed_out"] and audit["return_code"] == 0
    current = []
    for attempt in ("v_5", "v_6"):
        record = fresh_record(attempt, 2)
        grade = load(CONCEPT / record["evaluation"])
        assert grade["calibration_sha256"] == freeze["calibration_sha256"]
        summary = record["summary"]
        assert not summary["passed"] and summary["all_valid"]
        failures = [case for case in grade["cases"] if case["stages"]["long"]["quality"] < freeze["target"]["each_long_quality_min"]]
        assert len(failures) >= 2
        assert summary["core_score"] < 0.65 or summary["worst_family_score"] < 0.35
        record["long_quality_failures"] = len(failures)
        record["long_case_count"] = len(grade["cases"])
        record["failing_long_families"] = sorted({case["family"] for case in failures})
        record["maximum_long_cpu_seconds"] = max(case["stages"]["long"]["cpu_seconds"] for case in grade["cases"])
        record["failure_is_not_validity_or_resource_rejection"] = True
        current.append(record)
    history = [
        fresh_record("v_1", 0, "evaluation_wall_v2.json"),
        fresh_record("v_2", 0, "evaluation_wall_v2.json"),
        fresh_record("v_3", 1),
        fresh_record("v_4", 1),
    ]
    capability = (
        "Robust low-energy variational search across virtual-parity allocations in nonuniform finite-cap MPS. "
        "Both fresh implementations add local allocation searches but retain higher-energy edge-island and "
        "quartic-interface states; each fails four long-budget quality gates with every output valid. "
        "The same-cap private solver attains all long-quality targets."
    )
    status = load(CONCEPT / "status.json")
    status.update({
        "status": "hard_verified_achievable",
        "retained": True,
        "hardness_claimed": True,
        "decision_utc": datetime.now(timezone.utc).isoformat(),
        "passing_solution_known": True,
        "solvability": "demonstrated_by_unchanged_private_solver_on_all_16_frozen_runs",
        "private_passing_solver_assessment": "Passed every fixed quality and resource gate; this is a solver, not a reference-state lookup.",
        "private_passing_solver": {"proof": str(proof_path.relative_to(CONCEPT)), "proof_sha256": digest(proof_path), "summary": proof["summary"]},
        "fresh_agent_scores": current,
        "earlier_fresh_agent_scores": history,
        "earlier_failures_excluded_from_hardness": ["Generation-0 launcher-wall accounting episodes", "Generation-1 v3 short-budget resource failures despite meeting all quality thresholds"],
        "substantive_capability_failed": capability,
        "counterexample_search": {
            "admitted_cases": 8,
            "families": 4,
            "proposal": "adversary/ratchet_2_completion/PROPOSAL.json",
            "evidence": ["adversary/champion_2_exploration/tranche_3/PROPOSAL.json", "adversary/ratchet_2_completion/RESULTS.json", "adversary/calibration_validation.json"],
            "result": "Eight stable, physically valid, same-cap baseline energy gaps; all baseline stages valid. Large-chain prospective probes and timing-only failures were not admitted.",
        },
        "isolation_audit": "../authoring/final_isolation_audit_v3.json",
        "isolation_audit_sha256": digest(isolation_path),
        "static_frozen_suite_review": "../authoring/ratchet_two_review.json",
        "stop_reason": "Both isolated challengers substantially miss the frozen target, while a private full solver passes; no further ratchet is required.",
    })
    concept_two = load(ROOT / "concept_2/status.json")
    concept_three = load(ROOT / "concept_3/status.json")
    assert concept_two["status"] == "solved" and concept_two["ratchet_generations"] == 3
    assert concept_three["status"] == "solved" and concept_three["ratchet_generations"] == 0
    report = {
        "status": "hard_verified_achievable",
        "selected_concept": "concept_1",
        "solvability": "demonstrated",
        "built_concept_count": 3,
        "verification_modes": ["A_baseline_improvement", "C_witness_construction", "D_hidden_prediction"],
        "fresh_attempt_count": 15,
        "fresh_model": "ultima-alpha",
        "fresh_limit_seconds": 3600,
        "ratchet_generations": {"concept_1": 2, "concept_2": 3, "concept_3": 0},
        "concept_statuses": {"concept_1": status["status"], "concept_2": concept_two["status"], "concept_3": concept_three["status"]},
        "participant_task": "concept_1/participant/TASK.md",
        "evaluator": "concept_1/evaluator/evaluate.py",
        "runnable_baseline": "concept_1/participant/baseline",
        "evaluation_command_from_task_root": "python concept_1/evaluator/evaluate.py --submission SUBMISSION_DIRECTORY --output REPORT.json",
        "passing_solver_proof": "concept_1/" + str(proof_path.relative_to(CONCEPT)),
        "selected_baseline_summary": freeze["baseline_summary"],
        "selected_private_solver_summary": proof["summary"],
        "selected_fresh_scores": current,
        "substantive_capability_failed": capability,
        "isolation_audit": str(isolation_path.relative_to(ROOT)),
        "isolation_audit_sha256": digest(isolation_path),
        "isolation_scope": "Documented allowlist, hash, log and post-run process evidence; not a full backend or kernel attestation.",
        "final_report": "FINAL_REPORT.md",
    }
    save(CONCEPT / "status.json", status)
    save(CONCEPT / "adversary/final_tournament_summary.json", status)
    save(ROOT / "status.json", report)
    markdown = f"""# Hardness-discovery outcome

| Concept | Verification mode | Baseline / private solver | Fresh-agent scores | Ratchets | Final status |
| --- | --- | --- | --- | --- | --- |
| Robust parity-constrained phi4 MPS optimization | A: baseline improvement | Frozen baseline 0/100; private full solver {proof['summary']['score']:.6f}/100 | v5 {current[0]['summary']['score']:.6f}/100; v6 {current[1]['summary']['score']:.6f}/100 | 2 | hard_verified_achievable |
| Multiscale critical-vacuum tensor witness | C: witness construction | Final-generation baseline core {concept_two['baseline_core_score']:.6f}/1 | v7 and v8 core 1/1; all eight fresh attempts pass their generations | 3 | solved |
| Finite-chain spectral prediction | D: hidden prediction | Baseline {concept_three['baseline']['hidden_score']:.9f}/1 | v1 {concept_three['fresh_agent_scores'][0]['score']:.12f}/1 | 0 | solved |

## Baseline and champion history

- A generation 0: corrected intended-accounting fresh scores {history[0]['summary']['score']:.6f} and {history[1]['summary']['score']:.6f}, both passing. Generation 1: v3 {history[2]['summary']['score']:.6f}, all quality gates met but two short resource failures; v4 {history[3]['summary']['score']:.6f}, passing. These earlier resource episodes are not hardness evidence.
- C final challenger v8 has maximum three-interval relative error 0.041949 against the fixed 0.10 limit; the preceding champion has error 1.029998 on the ratcheted target.
- D champion remains passing on 360 independently certified private challenges, pooled score approximately 0.999999999155/1.

## Counterexample search results

- A: eight repeated same-cap energy failures across four physical families were admitted. Fresh v5 and v6 each fail four of eight long-quality gates, concentrated in competing edge-island odd states and quartic-interface even states. All 16 outputs per submission are valid; maximum long CPU is {current[0]['maximum_long_cpu_seconds']:.3f}s and {current[1]['maximum_long_cpu_seconds']:.3f}s against 40s.
- C: private searches expose long-distance correlation failures, connected four-spin errors, and a wrong-sign connected six-spin moment. Fresh challengers solve every resulting generation; the three-ratchet limit is exhausted without a retained hard witness task.
- D: no failure on 360 certified in-domain cases. Prospective larger-chain probes are outside the frozen prediction task and are not counted as failures.

## Final status and solvability

- Retain concept_1 as **hard_verified_achievable**. Both fresh attempts finish voluntarily within one hour and miss the fixed score >=80, core >=0.80 and worst-family >=0.70 targets substantially: cores {current[0]['summary']['core_score']:.6f}/{current[1]['summary']['core_score']:.6f}; worst families {current[0]['summary']['worst_family_score']:.6f}/{current[1]['summary']['worst_family_score']:.6f}.
- Solvability is **demonstrated**, not inferred from reference tensors: an unchanged historical solver, withheld from the current challengers, passes all 16 frozen runs with core {proof['summary']['core_score']:.6f}, worst family {proof['summary']['worst_family_score']:.6f}, and every long quality equal to 1. No exact ground-energy or global-optimality claim is made.
- Substantive capability failed: {capability}
"""
    (ROOT / "FINAL_REPORT.md").write_text(markdown)
    print(json.dumps({"status": report["status"], "selected_concept": report["selected_concept"], "fresh_scores": [record["summary"]["score"] for record in current], "passing_solver_score": proof["summary"]["score"], "fresh_attempt_count": 15}, indent=2))


if __name__ == "__main__":
    main()
