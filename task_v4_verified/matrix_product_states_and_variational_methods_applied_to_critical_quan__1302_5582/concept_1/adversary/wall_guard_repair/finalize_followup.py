import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    calibration_path = ROOT / "evaluator/hidden/calibration.json"
    original = json.loads(calibration_path.read_text())
    previous = json.loads((HERE / "freeze_manifest.json").read_text())
    if digest(calibration_path) != previous["corrected_calibration_sha256"]:
        raise ValueError("unexpected calibration revision")
    archived = ROOT / "generations/generation_0/evaluator/hidden/calibration.json"
    if digest(archived) != digest(calibration_path):
        raise ValueError("graded generation zero was not archived unchanged")
    for relative, expected in original["frozen_hashes"].items():
        if relative != "evaluator/sandbox_runner.py" and digest(ROOT / relative) != expected:
            raise ValueError("unapproved frozen change: " + relative)
    classifications = json.loads((HERE / "classification_validation.json").read_text())
    timing = json.loads((HERE / "validation.json").read_text())
    security = json.loads((ROOT / "adversary/runner_validation.json").read_text())
    if [record["passed"] for record in (classifications, timing, security)] != [4, 4, 6]:
        raise ValueError("follow-up regression checks incomplete")
    if any(record["failed"] for record in (classifications, timing, security)):
        raise ValueError("follow-up regression failure")
    updated = copy.deepcopy(original)
    old_hash = updated["frozen_hashes"]["evaluator/sandbox_runner.py"]
    updated["frozen_hashes"]["evaluator/sandbox_runner.py"] = digest(ROOT / "evaluator/sandbox_runner.py")
    updated["infrastructure_revision"] = 3
    updated["infrastructure_followup"] = "Unaccounted outer timeout is classified before stderr access; supervisor and child bootstrap use the same staged worker. Successful scoring predicate unchanged."
    calibration_path.write_text(json.dumps(updated, indent=2, allow_nan=False) + "\n")
    manifest = {
        "revision": 3,
        "previous_calibration_sha256": previous["corrected_calibration_sha256"],
        "corrected_calibration_sha256": digest(calibration_path),
        "runner_sha256_before": old_hash,
        "runner_sha256_after": updated["frozen_hashes"]["evaluator/sandbox_runner.py"],
        "successful_scoring_predicate_unchanged": True,
        "participant_cases_references_targets_unchanged": updated["cases"] == original["cases"] and updated["target_frozen_before_launch"] == original["target_frozen_before_launch"],
        "regressions_passed": 14,
        "scientific_ratchet": False,
        "graded_generation_zero_archive": "generations/generation_0/",
        "fresh_reports_remain_infrastructure_revision": 2,
        "solvability_demonstrated_by_unchanged_successful_predicate": True,
    }
    (HERE / "freeze_manifest_v3.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
