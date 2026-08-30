import sys

sys.dont_write_bytecode = True

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONCEPT = ROOT.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(relative, data):
    (ROOT / relative).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def main():
    audit = json.loads((ROOT / "adversary/audit_report.json").read_text())
    baseline = json.loads((ROOT / "adversary/baseline_independent_metrics.json").read_text())
    specification = json.loads((ROOT / "participant/input/spec.json").read_text())
    assert audit["passed"] and baseline["valid"] and not baseline["passed"]
    assert baseline["inherited_generation_two_score"] >= 1
    assert baseline["extension_point_minima"]["gap"] < 0.85 and baseline["extension_point_minima"]["opposite_posterior"] < 0.845
    assert not (ROOT / "evaluator/hidden/frozen_manifest.json").exists()
    assert (ROOT / "participant/baseline/champion.json").read_bytes() == (CONCEPT / "champions/generation_2/witness.json").read_bytes()
    write("participant/baseline/metrics.json", baseline)
    write("participant/baseline/selection.json", {"source": "champions/generation_2/witness.json", "attempt": "generation_2/v1", "model": "ultima-alpha",
          "both_previous_fresh_attempts_independently_passed": True, "v1_score": 1.0104109012101703, "v2_score": 1.0104079400244192,
          "selection_rule": "higher independently verified score", "provisional": False, "privileged_witness_used": False})
    frozen_at = datetime.now(timezone.utc).isoformat()
    files = {}
    for directory in (ROOT / "participant", ROOT / "evaluator"):
        for path in sorted(directory.rglob("*")):
            assert not path.is_symlink()
            if path.is_file() and path.name != "frozen_manifest.json":
                files[str(path.relative_to(ROOT))] = digest(path)
    manifest = {"generation": 3, "ratchet_index": 2, "final_planned_generation": True, "frozen_at_utc": frozen_at,
                "fresh_agents_launched_at_freeze": 0, "files_sha256": files,
                "global_targets": specification["targets"], "inherited_local_calibration": specification["local_calibration"],
                "orientation_calibration": specification["orientation_calibration"], "inference_points": 5791,
                "source_champion_sha256": digest(CONCEPT / "champions/generation_2/witness.json"),
                "known_passing_solution": False, "solvability": "open_unknown_achievability",
                "domain": "131 explicit continuously certified one-dimensional paths; no multidimensional box claim"}
    write("evaluator/hidden/frozen_manifest.json", manifest)
    keys = ("core_score", "inherited_generation_two_score", "extension_minimum_certificates", "extension_point_minima",
            "extension_actual_failure_clusters", "extension_certificate_only_failures", "evaluation_seconds", "evaluation_cpu_seconds", "peak_rss_mib")
    summary = {key: baseline[key] for key in keys}
    status = {"concept_id": "concept_2", "generation": 3, "ratchet_index": 2, "final_planned_generation": True,
              "planned_total_generations": 3, "verification_mode": "B", "task_type": "COUNTEREXAMPLE_FALSIFICATION",
              "status": "frozen_ready_for_main_launch", "solvability": "open_unknown_achievability", "known_passing_solution": False,
              "achievability_verified": False, "impossibility_proved": False, "evaluator_valid": True, "builder_audit_passed": True,
              "fresh_agents_launched": 0, "participant_attempts": 0, "participant_champions": 0, "planned_independent_attempts": 2,
              "planned_model": "ultima-alpha", "fresh_agent_wall_seconds": 3600, "fresh_difficulty_status": "unmeasured for generation 3",
              "source_generation": 2, "source_champion": "../../champions/generation_2/witness.json", "source_champion_is_actual_fresh_artifact": True,
              "source_selection": "both generation-two attempts independently passed; v1 had the higher score",
              "earlier_frozen_generations_unchanged": True, "full_multidimensional_box_claimed": False,
              "global_targets": specification["targets"], "local_targets": specification["local_calibration"]["targets"],
              "continuous_domains": 131, "inherited_spatial_directions": 22, "new_orientation_directions": 43,
              "local_background_scales": [0.95, 1.05], "local_amplitude_interval": [-0.05, 0.05], "inference_points": 5791,
              "champion_baseline": {"artifact": "participant/baseline/champion.json", "report": "adversary/baseline_independent_metrics.json", **summary},
              "private_feasibility_search": {"bounded": True, "seconds": 242.0441173510626, "restarts": 18, "best_stricter_surrogate": 0.9652626095256147,
                                             "passing_witness_found": False, "not_a_global_infeasibility_result": True},
              "audit_report": "adversary/audit_report.json", "frozen_at_utc": frozen_at, "manifest": "evaluator/hidden/frozen_manifest.json",
              "manifest_sha256": digest(ROOT / "evaluator/hidden/frozen_manifest.json"), "participant_exposure_allowlist": ["participant/"],
              "evaluation_resources": baseline["resources"], "main_owns_launch_champion_selection_and_postfreeze_status": True,
              "fresh_runner_launched_by_builder": False}
    write("status.json", status)
    write("adversary/freeze_report.json", {"ready": True, "frozen_at_utc": frozen_at, "files_frozen": len(files),
          "manifest_sha256": status["manifest_sha256"], "solvability": status["solvability"], "baseline": summary,
          "audit_passed": True, "fresh_runner_launched": False})
    print(json.dumps(json.loads((ROOT / "adversary/freeze_report.json").read_text()), indent=2))


if __name__ == "__main__":
    main()
