from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT.parents[1]


def read(relative):
    return json.loads((ROOT / relative).read_text())


def write(relative, data):
    (ROOT / relative).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    known = read("adversary/known_independent_metrics.json")
    baseline = read("adversary/baseline_independent_metrics.json")
    audit = read("adversary/audit_report.json")
    spec = read("participant/input/spec.json")
    assert known["passed"] and known["core_score"] >= 1 and baseline["valid"] and not baseline["passed"]
    assert baseline["nominal_score"] >= 1 and audit["passed"]
    assert baseline["local_actual_failure_clusters"].get("gap", 0) > 0
    assert baseline["local_actual_failure_clusters"].get("opposite_posterior", 0) > 0
    frozen_at = datetime.now(timezone.utc).isoformat()
    files = {}
    for directory in ("participant", "evaluator"):
        for path in sorted((ROOT / directory).rglob("*")):
            if path.is_file() and path.name != "frozen_manifest.json":
                assert not path.is_symlink()
                files[str(path.relative_to(ROOT))] = digest(path)
    manifest = {"generation": 2, "ratchet_index": 1, "frozen_at_utc": frozen_at,
                "fresh_agents_launched_at_freeze": 0, "files_sha256": files,
                "global_targets": spec["targets"], "local_calibration": spec["local_calibration"],
                "source_champion_sha256": digest(ORIGINAL / "champions/generation_1/witness.json"),
                "known_private_witness_sha256": digest(ROOT / "adversary/known_witness.json"),
                "domain": "one global line and 44 explicit spatial lines, each continuously certified; not a full box"}
    write("evaluator/hidden/frozen_manifest.json", manifest)
    def summary(result):
        return {key: result[key] for key in ("core_score", "nominal_score", "local_score", "local_minimum_certificates", "local_actual_failure_clusters", "evaluation_seconds", "evaluation_cpu_seconds", "peak_rss_mib")}
    status = {"concept_id": "concept_2", "generation": 2, "ratchet_index": 1, "maximum_ratchets": 3,
              "verification_mode": "B", "task_type": "COUNTEREXAMPLE_FALSIFICATION",
              "status": "frozen_ready_for_main_launch", "solvability": "known_feasible", "known_passing_solution": True,
              "evaluator_valid": True, "builder_audit_passed": True, "fresh_agents_launched": 0,
              "participant_attempts": 0, "participant_champions": 0, "planned_independent_attempts": 2,
              "planned_model": "ultima-alpha", "fresh_agent_wall_seconds": 3600,
              "fresh_difficulty_status": "unmeasured for generation 2", "source_generation": 1,
              "source_champion": "../../champions/generation_1/witness.json", "source_champion_is_actual_fresh_artifact": True,
              "source_selection": "both generation-one fresh attempts independently passed; v2 had the higher score",
              "original_frozen_participant_evaluator_unchanged": True, "full_multidimensional_box_claimed": False,
              "global_targets": spec["targets"], "local_targets": spec["local_calibration"]["targets"],
              "continuous_domains": 45, "local_directions": 22, "local_background_scales": [0.95, 1.05],
              "local_amplitude_interval": [-0.05, 0.05], "inference_points": 2265,
              "known_witness": {"artifact": "adversary/known_witness.json", "report": "adversary/known_independent_metrics.json", **summary(known)},
              "champion_baseline": {"artifact": "participant/baseline/champion.json", "report": "adversary/baseline_independent_metrics.json", **summary(baseline)},
              "audit_report": "adversary/audit_report.json", "frozen_at_utc": frozen_at,
              "manifest": "evaluator/hidden/frozen_manifest.json", "manifest_sha256": digest(ROOT / "evaluator/hidden/frozen_manifest.json"),
              "participant_exposure_allowlist": ["participant/"], "evaluation_resources": known["resources"],
              "fresh_runner_launched_by_builder": False}
    write("status.json", status)
    (ROOT / "adversary/BUILD_REPORT.md").write_text(
        "# Privileged generation-two construction report\n\n"
        "The actual promoted generation-one champion is v_2, after both independent\n"
        "ultima-alpha attempts passed. It—not the private builder witness—is the\n"
        "participant baseline. Its first broad calibration replay is preserved in\n"
        "the parent adversary/V2_STRESS_REPORT.md and v2_stress_report.json.\n\n"
        "The ratchet adds explicit exhaustive row/column sign directions, with\n"
        "continuous amplitude along each. It does not infer a multidimensional box\n"
        "from corners and does not use hidden random directions. Rate-budget\n"
        "preservation removes global-noise drift as the explanation for failures.\n\n"
        "Private calibration selected 51 local anchors and local targets 0.85 nats,\n"
        "0.845 posterior, and 0.0000175 syndrome probability. The original global\n"
        "targets and certificate remain unchanged. The preexisting private known\n"
        "witness is feasible without a new optimized design search. No private\n"
        "solver or feasibility artifact is exposed in the public packet.\n\n"
        f"Known independent score: {known['core_score']:.15g}; local bounds: "
        f"{json.dumps(known['local_minimum_certificates'], sort_keys=True)}.\n\n"
        f"Actual champion generation-two score: {baseline['core_score']:.15g}; "
        f"nominal score retained: {baseline['nominal_score']:.15g}. Exact pointwise "
        f"failure clusters: {json.dumps(baseline['local_actual_failure_clusters'], sort_keys=True)}.\n\n"
        "All 2,265 points per artifact were independently recomputed by generic\n"
        "full-state C++ probability/min-plus DP. The reversible GF(2) basis merely\n"
        "changes state coordinates and processes independent transitions first.\n"
        "The audit compares all 4,530 outputs against separate frontier inference,\n"
        "plus brute force, a slow generic full-state check, edge-order invariance,\n"
        "rank-deficient cases, off-anchor bounds, and malformed artifacts.\n\n"
        f"Known evaluation CPU/wall seconds: {known['evaluation_cpu_seconds']:.3f} / {known['evaluation_seconds']:.3f}; "
        f"peak RSS: {known['peak_rss_mib']:.3f} MiB. "
        f"Baseline CPU/wall seconds: {baseline['evaluation_cpu_seconds']:.3f} / {baseline['evaluation_seconds']:.3f}.\n\n"
        f"Frozen at {frozen_at}, before any generation-two fresh launch. This is\n"
        "ratchet one of at most three. No further task generation is created, no\n"
        "runner is launched, and no original frozen participant/evaluator is edited.\n")
    (ROOT / "adversary/BASELINE_REPORT.md").write_text(
        "# Actual-champion baseline audit\n\n"
        "The source is ../../champions/generation_1/witness.json, selected from both\n"
        "completed and independently passing generation-one attempts. Byte identity\n"
        "is checked in audit.py. The privileged known witness is not the baseline.\n\n"
        f"Generation-one nominal score: {baseline['nominal_score']:.15g}.\n"
        f"Generation-two score: {baseline['core_score']:.15g}; valid=true, passed=false.\n"
        f"Local bounds: {json.dumps(baseline['local_minimum_certificates'], sort_keys=True)}.\n"
        f"Actual anchor clusters: {json.dumps(baseline['local_actual_failure_clusters'], sort_keys=True)}.\n\n"
        "Thus actual gap and posterior violations, not only certificate slack,\n"
        "motivate the new domain. Full public and independent metrics are retained.\n")
    print(json.dumps({"READY": True, "frozen_at_utc": frozen_at, "files_hashed": len(files), "known_score": known["core_score"], "actual_champion_score": baseline["core_score"], "audit_passed": True, "generation_two_fresh_launched": 0}, indent=2))


if __name__ == "__main__":
    main()
