import datetime
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    targets = json.loads((ROOT / "targets.json").read_text())
    validation = json.loads((ROOT / "validation.json").read_text())
    audit = json.loads((ROOT / "adversary/champion_audit.json").read_text())
    provenance = json.loads((ROOT / "adversary/champion_provenance.json").read_text())
    for filename, expected in provenance["external_sha256"].items():
        assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == expected
    assert validation["valid"] and validation["all_certificates_exceed_50pct"]
    assert (targets["core_target"], targets["worst_family_target"], targets["case_seconds"], targets["suite_seconds"]) == (0.4, 0.3, 12, 360)
    assert audit["case_count"] == 36
    quality_failure = audit["valid"] and (audit["core_score"] < 0.4 or audit["worst_family_score"] < 0.3)
    if not quality_failure:
        raise RuntimeError("G2 is not justified by a valid original-champion quality failure")
    files = {}
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name not in ("freeze.json", "status.json") and "__pycache__" not in path.parts:
            files[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    freeze = {"generation": 2, "frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "frozen_before_fresh_launch": True, "fresh_agents_started": 0,
              "quality_targets_fixed": {"core": 0.40, "worst_family": 0.30},
              "resource_contract": {"case_seconds": 12, "suite_seconds": 360, "cpu_cores": 1, "memory_mb": 2048},
              "resource_adjustment_prelaunch_rationale": targets["resource_rationale"],
              "quality_targets_not_retuned": True, "timing_jitter_not_hardness_evidence": True,
              "certificate_feasibility": {"cases": 48, "minimum_improvement": validation["minimum_witness_improvement"],
                                          "minimum_active_wires": validation["minimum_active_wires"]},
              "original_champion_quality_failure": {"valid": audit["valid"], "core": audit["core_score"],
                                                     "worst_family": audit["worst_family_score"], "runtime_seconds": audit["runtime_seconds"]},
              "participant_boundary": "Only participant/ is delivered; all evaluator, generator, certificates, audits, status, and freeze material remain private.",
              "input_only_resource_qualified_generation_2_solver": "unknown; no fresh solver launched",
              "audit_provenance": provenance,
              "sha256": files}
    (ROOT / "freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
    status = {"generation": 2, "status": "ready_for_clean_fresh_launch", "frozen": True,
              "fresh_agents_started": 0, "participant_directory": "participant",
              "evaluator": "evaluator/evaluate.py", "public_cases": 12, "hidden_cases": 36,
              "quality_targets": [0.4, 0.3], "resource_limits": [12, 360],
              "minimum_private_certificate_improvement": validation["minimum_witness_improvement"],
              "old_champion_valid_quality_failure": True, "old_champion_core": audit["core_score"],
              "old_champion_worst_family": audit["worst_family_score"],
              "resource_rationale": targets["resource_rationale"],
              "no_target_quality_retuning": True, "full_resource_qualified_input_only_solver_known": False}
    (ROOT / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
