from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1] / "concept_1"


def main():
    destination = ROOT / "generations/generation_1"
    if destination.exists():
        raise RuntimeError("Do not overwrite a frozen repaired generation")
    destination.mkdir(parents=True)
    for directory in ("participant", "evaluator"):
        shutil.copytree(ROOT / directory, destination / directory, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for directory in ("adversary", "attempts", "champions"):
        (destination / directory).mkdir()
    targets_path = destination / "evaluator/hidden/targets.json"
    targets = json.loads(targets_path.read_text())
    targets.update(core_improvement_percent=2.5, worst_family_improvement_percent=1.0)
    targets_path.write_text(json.dumps(targets, indent=2) + "\n")
    task = destination / "participant/TASK.md"
    text = task.read_text()
    assert "6% mean relative" in text and "3% reduction in the worst family" in text
    text = text.replace("6% mean relative", "2.5% mean relative").replace("3% reduction in the worst family", "1% reduction in the worst family")
    task.write_text(text)
    lower_bound = json.loads((ROOT / "adversary/relaxed_bound.json").read_text())
    assert lower_bound["core_improvement_upper_bound_percent"] < 6
    assert lower_bound["worst_family_improvement_upper_bound_percent"] < 3
    assert lower_bound["core_improvement_upper_bound_percent"] > targets["core_improvement_percent"]
    assert lower_bound["worst_family_improvement_upper_bound_percent"] > targets["worst_family_improvement_percent"]
    hashes = {}
    for path in sorted((ROOT / "evaluator").rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.name == "targets.json":
            continue
        relative = path.relative_to(ROOT / "evaluator")
        other = destination / "evaluator" / relative
        assert path.read_bytes() == other.read_bytes()
        hashes[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
    provenance = {"created_at": datetime.now(timezone.utc).isoformat(), "reason": "Independent Bayes-tree relaxation rules out the original 6% core / 3% worst-family targets, even before fleet restrictions. The original generation is invalid, not hard.", "original_core_target": 6.0, "original_worst_family_target": 3.0, "new_core_target": 2.5, "new_worst_family_target": 1.0, "relaxed_core_upper_bound": lower_bound["core_improvement_upper_bound_percent"], "relaxed_worst_family_upper_bound": lower_bound["worst_family_improvement_upper_bound_percent"], "not_a_champion_ratchet": True, "changed": ["participant/TASK.md target percentages", "evaluator/hidden/targets.json target percentages"], "physics_cases_baseline_and_resource_limits_unchanged": True, "unchanged_evaluator_asset_sha256": hashes, "passing_solution_known": False, "fresh_attempt_required": True}
    (destination / "adversary/contract_repair.json").write_text(json.dumps(provenance, indent=2) + "\n")
    shutil.copy2(ROOT / "adversary/validation_report.json", destination / "adversary/inherited_validation_report.json")
    shutil.copy2(ROOT / "adversary/relaxed_bound.json", destination / "adversary/relaxed_bound.json")
    status = {"name": "Adaptive symmetry diagnostic fleet", "verification_mode": "A", "status": "ready_for_tournament", "generation": 1, "repair_generations": 1, "ratchet_generations": 0, "target": {"core_improvement_percent": 2.5, "worst_family_improvement_percent": 1.0}, "baseline_score": 0.0, "baseline_worst_family_score": 0.0, "private_portfolio_score": 1.6268, "private_portfolio_worst_family_score": 0.4838, "solvability": "unknown", "evaluator_validated": True}
    (destination / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    root_status = json.loads((ROOT / "status.json").read_text())
    root_status.update(status="invalid", reason=provenance["reason"], current_generation="generations/generation_1", current_generation_status="ready_for_tournament", repair_generations=1)
    (ROOT / "status.json").write_text(json.dumps(root_status, indent=2) + "\n")
    print(json.dumps({"generation": str(destination), "targets": targets, "original_generation": "invalid", "evaluator_assets_unchanged": len(hashes)}))


if __name__ == "__main__":
    main()
