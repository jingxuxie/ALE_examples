import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import secrets
import sys


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))

from evaluate import read_hidden, score, validate_predictions


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_records(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def main():
    public = ROOT / "participant/input"
    workspace = ROOT / "participant/workspace"
    baseline = ROOT / "participant/baseline"
    model = workspace / "baseline.pkl.gz"
    if not model.is_file():
        raise RuntimeError("Refitted public model is not yet available")
    for name in ("predict.py", "descriptors.py"):
        if (baseline / name).read_bytes() != (workspace / name).read_bytes():
            raise ValueError("Standalone baseline code differs from its public workspace source")
        if (workspace / name).read_bytes() != (SOURCE / "participant/baseline" / name).read_bytes():
            raise ValueError("Expected only original public predictor/descriptor code")
    (baseline / "baseline.pkl.gz").write_bytes(model.read_bytes())
    (public / "environment.json").write_bytes((SOURCE / "participant/input/environment.json").read_bytes())
    manifest = json.loads((ROOT / "evaluator/hidden/manifest.json").read_text())
    hidden_path = ROOT / "evaluator/hidden/test.jsonl"
    if not manifest.get("hidden_order_randomized", False):
        if digest(hidden_path) != manifest["splits"]["test"]["sha256"]:
            raise ValueError("Hidden bank changed before neutral-ID randomization")
        hidden_records = read_records(hidden_path)
        secrets.SystemRandom().shuffle(hidden_records)
        previous_ids = [case["id"] for case in hidden_records]
        for index, case in enumerate(hidden_records):
            case["id"] = f"case_{index:05d}"
        hidden_path.write_text("".join(json.dumps(case, allow_nan=False, separators=(",", ":")) + "\n"
                                        for case in hidden_records))
        manifest["splits"]["test"]["sha256"] = digest(hidden_path)
        manifest["hidden_order_randomized"] = True
        manifest["hidden_id_scheme"] = "Neutral sequential case IDs assigned only after independent OS-entropy shuffling"
        write_json(ROOT / "evaluator/hidden/manifest.json", manifest)
        write_json(ROOT / "authoring/hidden_order.json", {"previous_ids_in_final_order": previous_ids,
                                                        "participant_visible": False})
        public_checks = json.loads((public / "data_checks.json").read_text())
        public_checks["hidden_contract"]["ordering"] = "Independently shuffled; neutral IDs do not encode family or original stress-bank order"
        write_json(public / "data_checks.json", public_checks)
    targets = json.loads((ROOT / "evaluator/targets.json").read_text())
    metrics = json.loads((public / "baseline_metrics.json").read_text())
    expected_sizes = {"train": 320, "validation": 160, "test": 320}
    for name, size in expected_sizes.items():
        path = ROOT / "evaluator/hidden/test.jsonl" if name == "test" else public / f"{name}.jsonl"
        records = read_records(path)
        assert len(records) == size and all(case["L"] == 14 and len(case["fields"]) == 14 for case in records)
        assert len({case["id"] for case in records}) == size
        assert Counter(case["family"] for case in records) == Counter({family: size // 4 for family in (
            "iid_uniform", "ordered_blocks", "alternating_correlated", "shuffled_pairs")})
        assert digest(path) == manifest["splits"][name]["sha256"]
        assert all(math.isfinite(case["f"]) and 0 <= case["f"] <= 1 for case in records)
    assert len(read_hidden()) == 320
    assert metrics["training_records"] == 2240 and metrics["target_size_training_records"] == 320
    assert metrics["auxiliary_training_records"] == 1920 and metrics["validation_records"] == 160
    assert not metrics["new_L14_validation_used_for_fit"]
    assert targets["overall_rmse"] == 0.035 and targets["worst_family_rmse"] == 0.05
    assert targets["wall_seconds"] == 3 and targets["startup_seconds"] == 60
    assert not targets["frozen"]
    assert (ROOT / "evaluator/sandbox.py").read_bytes() == (SOURCE / "evaluator/sandbox.py").read_bytes()
    assert (ROOT / "evaluator/physics.py").read_bytes() == (workspace / "physics.py").read_bytes()
    assert (ROOT / "participant/TASK.md").read_bytes() == (ROOT / "TASK.md").read_bytes()
    word_count = len((ROOT / "TASK.md").read_text().split())
    assert 200 <= word_count <= 300
    source_files = sorted(ROOT.rglob("*.py"))
    for path in source_files:
        ast.parse(path.read_text(), filename=str(path))
    cases = [{"id": "check", "L": 14, "family": "iid_uniform", "f": 0.5}]
    predictions = validate_predictions({"predictions": [{"id": "check", "f": 0.5}]}, cases)
    assert score(cases, predictions, targets)["passed"]
    rejected = 0
    for value in (float("nan"), float("inf"), True, "0.5", -0.1, 1.1):
        try:
            validate_predictions({"predictions": [{"id": "check", "f": value}]}, cases)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError("Invalid prediction accepted")
    report = {"generation": 2, "ratchet": 1, "completed_utc": datetime.now(timezone.utc).isoformat(),
              "task_words": word_count, "python_files_parsed": len(source_files),
              "invalid_prediction_checks_rejected": rejected,
              "checks": ["frozen identical physics", "latest inherited seccomp sandbox",
                         "L14-only balanced splits with checked hashes", "zero symmetry duplicates during construction",
                         "hidden order independently shuffled before assigning neutral IDs",
                         "auxiliary data retained without previous fresh-agent code or models",
                         "standalone baseline exact source/weight copy", "unchanged targets, main owns freeze"],
              "public_baseline_metrics": metrics,
              "official_sandbox_run": False, "fresh_agent_launched": False,
              "candidate_artifact_hashes_not_final_commitments": {
                  str(path.relative_to(ROOT)): digest(path)
                  for path in sorted((ROOT / "participant").rglob("*")) if path.is_file()},
              "trusted_candidate_hashes": {
                  str(path.relative_to(ROOT)): digest(path)
                  for path in sorted((ROOT / "evaluator").rglob("*")) if path.is_file()}}
    write_json(ROOT / "authoring/package_checks.json", report)
    baseline_passes = metrics["overall_rmse"] <= 0.035 and metrics["worst_family_rmse"] <= 0.05
    status = {"concept": "concept_1", "generation": 2, "ratchet": 1,
              "mode": "D HIDDEN PREDICTION", "status": "ready_for_main_freeze",
              "target_length": 14, "records": {"new_training": 320, "new_validation": 160,
                                                "auxiliary_training": 1920, "hidden_test": 320},
              "targets": {"overall_rmse": 0.035, "worst_family_rmse": 0.05},
              "resources": {"inference_seconds": 3, "startup_seconds": 60, "enforced_cores": 4, "memory_mb": 2048},
              "target_frozen": False, "freeze_owner": "main", "official_evaluation_owner": "main",
              "baseline": {"path": "participant/baseline", "trees": metrics["trees"],
                           "validation_overall_rmse": metrics["overall_rmse"],
                           "validation_worst_family_rmse": metrics["worst_family_rmse"],
                           "meets_unchanged_validation_targets": baseline_passes,
                           "warm_160_case_batch_seconds_not_official": metrics["warm_batch_seconds"]},
              "needs_target_discussion_before_freeze": baseline_passes,
              "thresholds_adjusted": False, "fresh_solving_agent_launched": False,
              "private_bank_scored_by_builder": False, "official_streaming_benchmark": "main pending",
              "hidden_order_randomized": True,
              "allowed_writes": "concept_1/generations/generation_2 only",
              "original_concept_1_assets_modified": False,
              "checks": "authoring/package_checks.json; participant/input/data_checks.json; participant/input/physics_checks.json"}
    write_json(ROOT / "status.json", status)
    print(json.dumps(status, indent=2), flush=True)


if __name__ == "__main__":
    main()
