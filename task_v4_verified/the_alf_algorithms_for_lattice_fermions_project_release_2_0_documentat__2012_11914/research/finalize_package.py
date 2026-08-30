import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return json.loads((ROOT / relative).read_text())


def write(relative, payload):
    (ROOT / relative).write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def brief(report):
    return {key: report[key] for key in (
        "core_score", "worst_family_score", "max_point_ratio", "valid",
        "passed", "runtime_seconds", "reason"
    ) if key in report}


def manifest(directory):
    return {
        str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }


def finalize_design():
    fresh = read("concept_2/attempts/v_2.evaluation.json")
    private = read("concept_2/adversary/privileged_generation2_confirmation.json")
    fresh_precision = read("concept_2/adversary/fresh_v2_high_precision.json")
    private_precision = read("concept_2/adversary/privileged_schedule_high_precision.json")
    run = read("concept_2/attempts/logs/v_2.run.json")
    assert run["state"] == "finished" and run["participant_unchanged"]
    assert fresh["valid"] and not fresh["passed"]
    assert private["valid"] and private["passed"]
    assert fresh["targets"] == private["targets"]
    assert fresh_precision["passed"] and private_precision["passed"]
    assert fresh["max_point_ratio"] > 1.10
    assert fresh["core_score"] >= 1.80 and fresh["worst_family_score"] >= 1.35
    artifact = ROOT / "concept_2/adversary/topology_refine/submission.json"
    status = {
        "concept": "Positive checkerboard propagator",
        "verification_mode": "C_WITNESS_OR_DESIGN_CONSTRUCTION",
        "status": "hard_verified_achievable",
        "retained_as_hard": True,
        "selected_primary": True,
        "generation": 2,
        "ratchet_generations": 1,
        "target_frozen_before_attempt": True,
        "targets": fresh["targets"],
        "baseline": brief(read("concept_2/adversary/baseline_generation2_score.json")),
        "baseline_report": "adversary/baseline_generation2_score.json",
        "initial_champion_on_initial_target": brief(read("concept_2/attempts/v_1.evaluation.json")),
        "initial_champion_on_current_target": brief(read("concept_2/adversary/champion_generation2_score.json")),
        "initial_champion": "champions/generation_1",
        "fresh_agent": {"model": "ultima-alpha", "limit_seconds": 3600},
        "qualified_fresh_attempt": "v_2",
        "fresh_score": brief(fresh),
        "fresh_report": "attempts/v_2.evaluation.json",
        "fresh_run": "attempts/logs/v_2.run.json",
        "fresh_failure_high_precision": "adversary/fresh_v2_high_precision.json",
        "known_target_passing_solution": True,
        "solvability": "demonstrated by a privileged independent topology/coefficient search, not by the fresh challenger",
        "privileged_solution": "adversary/topology_refine/submission.json",
        "privileged_artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "privileged_score": brief(private),
        "privileged_report": "adversary/privileged_generation2_confirmation.json",
        "privileged_high_precision": "adversary/privileged_schedule_high_precision.json",
        "privileged_search": "adversary/topology_refine/summary.json",
        "evaluator_validated": True,
        "validation_reports": ["adversary/self_test_report.json", "adversary/privileged_generation2_confirmation.json", "adversary/fresh_v2_high_precision.json"],
        "adversarial_search_report": "adversary/CHAMPION_AUDIT_SUMMARY.json",
        "generation_protocol": "adversary/generation_2_protocol.json",
        "failed_capability": "Joint finite-step component-order and positive-coefficient design under simultaneous aggregate, family, and no-regression constraints. Aggregate and family targets are met, but the final schedule makes a held-out Green-function error 17.0% worse than equal-cost Strang.",
        "reason": "A one-hour clean challenger fails a substantial, independently 70-digit-confirmed pointwise constraint; a private artifact passes every frozen gate."
    }
    write("concept_2/status.json", status)
    return status


def audit_runs():
    mapping = [
        ("concept_1", 1, "adversary/generations/generation_1/participant"),
        ("concept_1", 2, "adversary/generations/generation_2_assisted/participant"),
        ("concept_1", 3, "adversary/generations/generation_2_clean/participant"),
        ("concept_2", 1, "adversary/generations/generation_1/participant"),
        ("concept_2", 2, "participant"),
        ("concept_3", 1, "participant"),
    ]
    reports = []
    for concept, index, snapshot in mapping:
        folder = ROOT / concept
        run = read(f"{concept}/attempts/logs/v_{index}.run.json")
        public = manifest(folder / snapshot)
        output = manifest(folder / f"attempts/v_{index}")
        changed = sorted(name for name in output.keys() | run["submission_sha256"].keys()
                         if output.get(name) != run["submission_sha256"].get(name))
        qualified = (concept, index) != ("concept_1", 2)
        record = {
            "concept": concept, "attempt": f"v_{index}", "qualifying": qualified,
            "state": run["state"], "model": run["model"],
            "output_initially_empty": run["output_initially_empty"],
            "participant_snapshot_matches_launch": public == run["participant_sha256"],
            "submission_matches_deadline_or_exit": not changed,
            "later_changed_paths": changed,
            "elapsed_seconds": run["elapsed_seconds"], "timed_out": run["timed_out"],
        }
        assert record["state"] == "finished" and record["model"] == "ultima-alpha"
        assert record["output_initially_empty"] and record["participant_snapshot_matches_launch"]
        assert record["elapsed_seconds"] <= 3611
        if qualified:
            assert not changed, record
        else:
            record["exclusion"] = "Previous fresh code/witness were supplied; additionally later scratch-file changes exist. Never counted as qualifying hardness evidence."
        reports.append(record)
    audit = {"passed_for_all_qualifying_runs": True, "qualifying_runs": 5,
             "excluded_assisted_controls": 1, "records": reports}
    write("research/run_integrity_audit.json", audit)
    return audit


def audit_package():
    names = ["concept_1", "concept_2", "concept_3"]
    assert sorted(path.name for path in ROOT.glob("concept_*")) == names
    for name in names:
        folder = ROOT / name
        for required in ("participant/TASK.md", "participant/input", "participant/workspace",
                         "participant/baseline", "evaluator/evaluate.py", "evaluator/hidden",
                         "attempts", "champions", "adversary", "status.json"):
            assert (folder / required).exists(), (name, required)
        assert not any(path.is_symlink() for path in (folder / "participant").rglob("*"))
    for relative, expected in read("concept_2/evaluator/hidden/manifest.json")["sha256"].items():
        assert hashlib.sha256((ROOT / "concept_2" / relative).read_bytes()).hexdigest() == expected
    assert read("concept_1/adversary/evaluator_validation.json")["passed"]
    assert read("concept_2/adversary/self_test_report.json")["successful"]
    for name in ("static_validation_report", "process_validation_report"):
        assert read(f"concept_3/evaluator/hidden/{name}.json")["all_passed"]
    for artifact in read("research/provenance.json")["source_artifacts"]:
        assert hashlib.sha256((ROOT / "research" / artifact["file"]).read_bytes()).hexdigest() == artifact["sha256"]
    audit = {"passed": True, "built_concepts": 3, "distinct_primary_modes": 3,
             "required_package_structure": True, "public_symlinks": False,
             "design_frozen_manifest_unchanged": True, "paper_source_hashes_match": True,
             "evaluator_validation_controls_pass": True,
             "run_integrity": "research/run_integrity_audit.json"}
    write("research/package_audit.json", audit)
    return audit


def main():
    design = finalize_design()
    runs = audit_runs()
    audit_package()
    statuses = {name: read(f"{name}/status.json") for name in ("concept_1", "concept_2", "concept_3")}
    assert statuses["concept_1"]["status"] == "hard_open_candidate"
    assert statuses["concept_3"]["status"] == "solved"
    result = {
        "status": "hard_verified_achievable",
        "selected_concept": "concept_2",
        "selected_participant": "concept_2/participant",
        "selected_evaluator": "concept_2/evaluator/evaluate.py",
        "selected_solvability": "demonstrated",
        "retained_concepts": ["concept_1", "concept_2"],
        "concepts_built": 3, "concepts_considered": 10,
        "verification_modes": ["B_COUNTEREXAMPLE_OR_FALSIFICATION", "C_WITNESS_OR_DESIGN_CONSTRUCTION", "D_HIDDEN_PREDICTION"],
        "fresh_model": "ultima-alpha", "fresh_limit_seconds": 3600,
        "qualifying_fresh_attempts": runs["qualifying_runs"],
        "excluded_assisted_controls": 1,
        "ratchet_generations": {name: status["ratchet_generations"] for name, status in statuses.items()},
        "decisions": {name: {key: status[key] for key in ("status", "known_target_passing_solution", "solvability")} for name, status in statuses.items()},
        "selected_baseline_score": design["baseline"],
        "selected_fresh_score": design["fresh_score"],
        "selected_privileged_score": design["privileged_score"],
        "failed_capability": design["failed_capability"],
        "package_audit": "research/package_audit.json",
        "report": "FINAL_REPORT.md"
    }
    write("status.json", result)
    report = """# Hardness decision

**Selected: concept_2 — hard_verified_achievable.** Solvability is demonstrated
by a private artifact. All fresh runs use `ultima-alpha` with a one-hour limit.
Scores below are core / worst-family; scales differ between concepts.

| Concept and primary mode | Baseline | Initial fresh champion | Final qualifying fresh | Final status | Ratchets |
|---|---:|---:|---:|---|---:|
| Robust rare-sign Hubbard witness — B, counterexample | 0 / 0 | 1 / 1 at beta=1.6 | 0 / 0 at beta=0.75 | hard_open_candidate | 1 |
| Positive checkerboard schedule — C, design construction | 1 / 1 | 2.9776 / 2.6003 | 2.1044 / 1.6825 | hard_verified_achievable | 1 |
| Fermionic spectral reconstruction — D, hidden prediction | 75.2339 / 48.7355 | 95.7608 / 87.2427 | 95.7608 / 87.2427 | solved | 0 |

## Champion and counterexample searches

- **Sign:** 1,632 parameter cells invalidate the original fixed witness in 1,533
  cells. A 597,504-case structured search finds no beta=0.75 witness; broader
  private continuation certifies beta=0.786, not the target. The clean fresh
  artifact is valid but positive at all three certification points. All 20
  distinct saved discrete candidates are nominally positive at 65/95 digits.
  Target solvability remains **unknown**; no nonexistence claim is made.
- **Schedule:** 7,680 independent cases and 1,108 controlled configurations expose
  genuine finite-step regressions, including a 1.5328x error ratio confirmed at
  70 digits. The old champion on the ratcheted target scores 2.0250 / 1.5158,
  but its maximum error ratio is 1.3627. The new fresh submission scores well
  in aggregate but has a **1.1701565** maximum ratio, failing the frozen <=1.00
  no-regression gate. Its worst-point failure is independently reproduced at
  70 digits. A private 65-word search produces **1.801879 / 1.372175**, maximum
  ratio **0.9812035**, passing every frozen gate. Solvability is **demonstrated**.
- **Prediction:** The final champion uses 76.35 of the allowed 120 seconds on the
  official batch. A further 448-case final-code audit includes two independent
  balanced batches scoring 95.8779 / 88.2034 and 95.9744 / 89.7548, plus 64
  conditional confirmations. No substantial final-champion failure survives;
  no new generation is justified. Solvability is **demonstrated**.

## Substantive failures

The retained design task defeats simultaneous control of aggregate accuracy,
family accuracy, and worst-case finite-step Green-function error under a fixed
positive 33-stage work budget. The open sign task defeats rare correlated-field
search, not JSON formatting. One champion-assisted sign control is excluded;
the reported final sign score comes from the clean retest. All five qualifying
attempts match their exit/deadline submission hashes.
"""
    (ROOT / "FINAL_REPORT.md").write_text(report)
    print(json.dumps({"selected": result["selected_concept"], "status": result["status"],
                      "decisions": result["decisions"], "integrity": "passed for all qualifying runs"}, indent=2))


if __name__ == "__main__":
    main()
