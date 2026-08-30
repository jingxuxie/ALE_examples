"""Freeze the staged public and trusted packet after successful audits."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

PACKET = Path(__file__).resolve().parents[1]


def main():
    oracle = json.loads((PACKET / "authoring" / "oracle_audit.json").read_text())
    audit = json.loads((PACKET / "authoring" / "packet_audit.json").read_text())
    zero = json.loads((PACKET / "authoring" / "zero_staged_evaluation.json").read_text())
    assert oracle["passed"] and audit["passed"]
    assert zero["diagnostics"]["admissible"] and zero["passed"] is False
    assert zero["diagnostics"]["stencil"]["path_certificates_evaluated"] == 243
    stamp = datetime.now(timezone.utc).isoformat()
    files = []
    for directory, name in (("participant", "freeze.json"), ("evaluator", "evaluator_freeze.json")):
        hashes = {str(path.relative_to(PACKET)): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in sorted((PACKET / directory).rglob("*"))
                  if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}
        manifest = {"generation": "population-witness-v4-adaptive", "ratchet_count": 3,
                    "frozen_at_utc": stamp, "scope": directory, "sha256": hashes}
        (PACKET / name).write_text(json.dumps(manifest, indent=2))
        files.extend(hashes)
    status = {"generation": "population-witness-v4-adaptive", "ratchet_count": 3, "primary_mode": "B",
              "readiness": "frozen_staging_ready_for_main_installation_and_fresh_attempts",
              "frozen_at_utc": stamp, "achievability": "hard_open_candidate",
              "privileged_passing_witness_known": False, "feasibility_proved": False,
              "infeasibility_proved": False, "hardness_demonstrated": False,
              "structural_obstruction_audit": "simple kinematic implication fails; stationary-CCSD feasibility unresolved",
              "active_generation_three_unchanged": audit["checks"]["active_and_archived_generation_three_unchanged"],
              "all_original_thresholds_unchanged": True, "radius": 0.001, "coordinate_point_count": 241,
              "adaptive_point_count": 2, "total_point_count": 243, "population_threshold": 0.02,
              "dad_maximum": 0.001, "energy_error_maximum": 0.0001,
              "evaluator_timeout_seconds": 900, "zero_example_runtime_seconds": zero["runtime_seconds"],
              "zero_example_certificates": 243, "baseline_trials": 1000, "baseline_core_score": 0.0,
              "completed_champions_rejected_by_new_rule": 2, "oracle_audit_passed": True,
              "packet_audit_passed": True, "fresh_agents_launched_by_worker": 0}
    (PACKET / "status.json").write_text(json.dumps(status, indent=2))
    text = "# Generation four staged files\n\nOnly the files under this staging directory are new or changed.\n\n"
    text += "\n".join("- `" + name + "`" for name in files)
    text += "\n\nPrivate handoff: `READY_FOR_MAIN.md`, `status.json`, `freeze.json`, `evaluator_freeze.json`, and `authoring/`.\n"
    (PACKET / "FILES.md").write_text(text)
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
