import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]


def read_json(path):
    return json.loads(path.read_text())


def main():
    validation = read_json(ROOT / "validation.json")
    legacy = read_json(ROOT / "legacy_validation.json")
    baseline = read_json(ROOT / "baseline_score.json")
    contract = read_json(CONCEPT / "participant" / "input" / "contract.json")
    status = read_json(CONCEPT / "status.json")
    assert validation["passed"] and legacy["passed"]
    assert contract["version"] == status["target_contract_version"] == "critical-vacuum-v3"
    assert contract["composite_order_channel"]["maximum_relative_error"] == .01
    assert baseline["valid"] and not baseline["passed"]
    files = []
    for folder in (CONCEPT / "participant", CONCEPT / "evaluator"):
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                assert not path.is_symlink()
                assert path.suffix != ".pyc"
                files.append({"path": str(path.relative_to(CONCEPT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                              "bytes": path.stat().st_size, "mtime_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()})
    source_hashes = {record["path"]: record["sha256"] for record in files}
    assert source_hashes["participant/workspace/physics.py"] == validation["public_trusted_source_sha256"]
    assert source_hashes["evaluator/hidden/trusted_physics.py"] == validation["public_trusted_source_sha256"]
    assert source_hashes["participant/baseline/state.npz"] == validation["baseline_sha256"]
    result = {"ratchet_generation": 2, "contract_version": "critical-vacuum-v3",
              "manifest_created_utc": datetime.now(timezone.utc).isoformat(),
              "frozen_content_last_modified_utc": max(record["mtime_utc"] for record in files),
              "ready_for_main_to_launch_fresh": True,
              "threshold_decision": "User fixed composite covariance max relative error 0.01 before fresh v3 attempts; not adjusted after evaluation",
              "all_v2_physics_and_resource_criteria_retained": True,
              "composite_quartet_count": 60, "composite_maximum_span": 256,
              "submitted_subtraction": "literal submitted raw XXXX minus submitted left mean times submitted right mean",
              "exact_subtraction": "exact raw XXXX minus exact left mean times exact right mean",
              "construction_wall_seconds": 3600, "checker_timeout_seconds": 120, "bond_dimension_max": 24,
              "baseline_source": "champions/generation_2/state.npz",
              "baseline_core_score": baseline["core_score"], "baseline_worst_family_score": baseline["worst_family_score"],
              "baseline_composite_order_max_relative_error": baseline["metrics"]["composite_order_max_relative_error"],
              "baseline_passed": False, "passing_v3_tensor_known_at_freeze": False,
              "solvability": "unknown; no feasibility claim", "fresh_agents_launched_by_sidecar": False,
              "previous_attempt_construction_code_read": False, "old_generation_archives_modified": False,
              "validation_report": "adversary/ratchet_2/validation.json",
              "ed_certificates": "adversary/ratchet_2/ed_certificates.json",
              "artifact_rejection_report": "adversary/ratchet_2/artifact_rejection.json",
              "frozen_files": files}
    (ROOT / "freeze_manifest.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "frozen_files"}, indent=2))


if __name__ == "__main__":
    main()
