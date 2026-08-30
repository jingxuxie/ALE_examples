"""Finalize readiness only after all required empirical checks succeeded."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(relative):
    return json.loads((ROOT / relative).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    settings = load("evaluator/settings.json")
    assert settings == load("participant/input/scoring.json")
    assert (settings["train_count"], settings["validation_count"], settings["hidden_count"]) == (1536, 256, 256)
    assert (settings["charge_rmse_limit"], settings["spin_rmse_limit"],
            settings["family_charge_rmse_limit"], settings["family_spin_rmse_limit"]) == (0.03, 0.02, 0.05, 0.035)
    assert (settings["wall_seconds"], settings["cpu_seconds"], settings["memory_mb"],
            settings["inference_threads"]) == (25, 25, 2048, 1)
    task_words = len((ROOT / "participant/TASK.md").read_text().split())
    assert task_words <= 250
    checks = {name: load(name) for name in (
        "evaluator/hidden/remaining_checks.json", "evaluator/hidden/source_validation.json",
        "evaluator/hidden/reference_calibration.json", "evaluator/hidden/dataset_validation.json",
        "adversary/test_report.json", "adversary/isolation_audit_report.json",
        "adversary/public_workflow_report.json", "attempts/exact_small_quality.json")}
    assert all(report["passed"] for report in checks.values())
    assert checks["adversary/test_report.json"]["tests_run"] == 22
    assert load("participant/baseline/training_report.json")["training_wall_seconds"] < 3600
    kernel = load("attempts/kernel_test.json")
    assert kernel["valid"]
    assert load("attempts/kernel_validation.json")["valid"]
    exact = load("attempts/exact_hidden_budget.json")
    assert not exact["valid"] and not exact["passed"]
    assert exact["reason"] in {"wall_time_limit_exceeded", "sandbox_or_solver_exit_137", "sandbox_or_solver_exit_152"}
    lineage = load("evaluator/hidden/lineage.json")
    for name in ("solver.py", "physics.py", "hubbard.cpp", "hubbard.so"):
        relative = "participant/baseline_exact/" + name
        assert digest(ROOT / relative) == lineage["copies"][relative]["sha256"]
        assert digest(Path(lineage["copies"][relative]["source"])) == lineage["copies"][relative]["sha256"]
    original_changes = []
    original = ROOT.parents[1]
    for relative, record in lineage["copies"].items():
        source = Path(record["source"])
        if source.is_relative_to(original / "participant") or source.is_relative_to(original / "evaluator"):
            if digest(source) != record["sha256"]:
                original_changes.append(relative)
    assert not original_changes, original_changes
    manifest = {}
    for directory in (ROOT / "participant", ROOT / "evaluator"):
        for path in sorted(directory.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or "runs" in path.parts:
                continue
            if path.name in {"serial_affinity.json", "evaluation.lock", "worker_placement.json"}:
                continue
            manifest[str(path.relative_to(ROOT))] = digest(path)
    frozen = datetime.now(timezone.utc).isoformat()
    generation = load("evaluator/hidden/generation_report.json")
    assert generation["config_sha256"] == digest(ROOT / "participant/input/scoring.json")
    (ROOT / "freeze_manifest.json").write_text(json.dumps({"frozen_at_utc": frozen,
        "targets_unchanged_since_label_generation": True, "sha256": manifest}, indent=2) + "\n")
    status = load("status.json")
    status.update(status="ready_for_fresh_attempt", ready=True, frozen_at_utc=frozen,
        participant_frozen=True, evaluator_source_frozen=True,
        fresh_attempt_launched=False, original_participant_and_evaluator_modified=False,
        original_copy_sources_unchanged=True, task_word_count=task_words,
        build_progress={"training_labels_completed_at_least": settings["train_count"],
            "training_labels_planned": settings["train_count"],
            "total_labels_completed": settings["train_count"] + settings["validation_count"] + settings["hidden_count"],
            "note": "All generation and required validation checks completed before freeze."},
        generation_counts={name: row["count"] for name, row in generation["splits"].items()},
        label_cpu_seconds=sum(row["label_cpu_seconds"] for row in generation["splits"].values()),
        label_generation_wall_seconds=sum(row["build_wall_seconds"] for row in generation["splits"].values()),
        max_source_residual=max(row["max_residual"] for row in generation["splits"].values()),
        baseline_hidden={key: kernel[key] for key in ("valid", "passed", "core_score", "worst_family_score",
            "charge_rmse", "spin_rmse", "runtime_seconds", "resource_score")},
        provided_exact_hidden={key: exact[key] for key in ("valid", "passed", "reason", "runtime_seconds", "runtime")},
        difficulty_status="not_yet_measured_by_a_fresh_generation_attempt",
        manifest="freeze_manifest.json")
    (ROOT / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
