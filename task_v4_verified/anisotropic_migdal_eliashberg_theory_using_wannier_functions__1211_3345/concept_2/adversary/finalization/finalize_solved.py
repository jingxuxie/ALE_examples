import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np


FINALIZATION = Path(__file__).resolve().parent
ROOT = FINALIZATION.parent.parent
PENDING = ROOT / "adversary/generation_1"


def json_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def hashes(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if "__pycache__" in path.parts:
            continue
        if path.is_symlink():
            raise ValueError("Unexpected symlink: " + str(path))
        if path.is_file():
            result[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def apply_text(path, content):
    if path.exists():
        original = path.read_text()
        if original == content:
            return
        patch = "*** Begin Patch\n*** Update File: " + str(path) + "\n@@\n"
        patch += "".join("-" + line + "\n" for line in original.splitlines())
        patch += "".join("+" + line + "\n" for line in content.splitlines())
    else:
        patch = "*** Begin Patch\n*** Add File: " + str(path) + "\n"
        patch += "".join("+" + line + "\n" for line in content.splitlines())
    subprocess.run(["apply_patch", patch + "*** End Patch\n"], check=True)


def run_evaluator(evaluator, artifact, name, validation):
    output = validation / (name + ".json")
    audit = validation / (name + ".audit.json")
    completed = subprocess.run([
        sys.executable, "-B", str(evaluator), "--artifact", str(artifact),
        "--output", str(output), "--audit-output", str(audit),
    ], check=True, text=True, capture_output=True)
    (validation / (name + ".stdout.log")).write_text(completed.stdout + completed.stderr)
    return json.loads(output.read_text())


def main():
    source = PENDING / "reporting_only/evaluator"
    previous_regression = json.loads((PENDING / "reporting_only/REPORTING_REGRESSION.json").read_text())
    assert previous_regression["passed"] and previous_regression["formatting_only"]
    original_status = json.loads((ROOT / "status.json").read_text())
    assert original_status["target_ratio"] == 1.12
    before_participant = hashes(ROOT / "participant")
    before_input = hashes(ROOT / "input")
    before_evaluator = hashes(ROOT / "evaluator")
    for filename in ("_physics.py", "_audit.py"):
        assert (ROOT / "evaluator" / filename).read_bytes() == (source / filename).read_bytes()
    archive = FINALIZATION / "original_root"
    if archive.exists():
        raise ValueError("Original-root archive already exists; do not overwrite historical status or evaluator.")
    archive.mkdir(parents=True)
    shutil.copy2(ROOT / "status.json", archive / "status.json")
    shutil.copytree(ROOT / "evaluator", archive / "evaluator", ignore=shutil.ignore_patterns("__pycache__"))
    assert hashes(archive / "evaluator") == before_evaluator
    original_status_hash = hashlib.sha256((archive / "status.json").read_bytes()).hexdigest()
    json_write(FINALIZATION / "archive_manifest.json", {
        "original_status_sha256": original_status_hash,
        "original_evaluator": before_evaluator,
        "original_participant": before_participant,
        "original_compatibility_input": before_input,
        "purpose": "Pre-finalization archive of the unchanged original numerical contract, before reporting-only additions and solved status.",
    })
    validation = FINALIZATION / "validation"
    validation.mkdir()
    baseline = validation / "baseline.npz"
    subprocess.run([sys.executable, "-B", str(ROOT / "participant/baseline/solve.py"),
                    "--output", str(baseline)], check=True)
    champion = ROOT / "champions/generation_1/frozen_submission/witness.npz"
    fresh = []
    for name in ("v_1", "v_2"):
        evaluation_path = ROOT.parent / "authoring/runs/concept_2" / name / "evaluation.json"
        result = json.loads(evaluation_path.read_text())
        assert result["valid"] and result["admissible"]
        fresh.append({"attempt": name, "score": result["score"], "valid": True,
                      "admissible": True, "input_sha256": result["input_sha256"],
                      "evaluation": str(evaluation_path.relative_to(ROOT.parent))})
    assert fresh[1]["score"] == 1.1245411788778297
    with np.load(baseline, allow_pickle=False) as artifact:
        repeated = np.array(artifact["kernels"], copy=True)
    nan_path = validation / "nan.npz"
    invalid = repeated.copy()
    invalid[0, 0, 0, 0] = np.nan
    np.savez_compressed(nan_path, kernels=invalid)
    static_path = validation / "static_violation.npz"
    invalid = repeated.copy()
    invalid[0, 0, 0, 0] += .02
    np.savez_compressed(static_path, kernels=invalid)
    bad_archive = validation / "bad_archive.npz"
    bad_archive.write_bytes(b"not a ZIP archive")
    cases = {"v2": champion, "baseline": baseline, "missing": validation / "absent.npz",
             "nan": nan_path, "static_violation": static_path, "bad_archive": bad_archive}
    old = {name: run_evaluator(archive / "evaluator/evaluate.py", artifact, "old_" + name, validation)
           for name, artifact in cases.items()}
    for filename in ("evaluate.py", "reporting.py"):
        apply_text(ROOT / "evaluator" / filename, (source / filename).read_text())
    new = {name: run_evaluator(ROOT / "evaluator/evaluate.py", artifact, "root_" + name, validation)
           for name, artifact in cases.items()}
    numerical_keys = ("score", "valid", "admissible", "target_met", "converged",
                      "independent_audit_passed", "target_ratio", "input_sha256", "artifact_sha256")
    regression = []
    for name in cases:
        for key in numerical_keys:
            assert old[name].get(key) == new[name].get(key), (name, key, old[name], new[name])
        result = new[name]
        assert isinstance(result["reason"], str) and result["reason"]
        assert result["core_score"] == result["score"] == result["worst_family_score"]
        assert result["resources"]["cpu_seconds"] >= 0
        assert result["resources"]["wall_seconds"] >= 0
        assert result["resources"]["peak_rss_kib"] > 0
        regression.append({"case": name, "score": result["score"], "valid": result["valid"],
                           "admissible": result["admissible"], "unchanged": True, "reason": result["reason"]})
    assert new["v2"]["score"] == fresh[1]["score"] and new["v2"]["valid"]
    assert new["baseline"]["score"] == 1.0 and new["baseline"]["admissible"] and not new["baseline"]["valid"]
    assert new["v2"]["input_sha256"] == original_status["input_sha256"]
    expected_evaluator = dict(before_evaluator)
    for filename in ("evaluate.py", "reporting.py"):
        expected_evaluator[filename] = hashlib.sha256((source / filename).read_bytes()).hexdigest()
    assert hashes(ROOT / "evaluator") == expected_evaluator
    assert hashes(ROOT / "participant") == before_participant
    assert hashes(ROOT / "input") == before_input
    assert hashes(archive / "evaluator") == before_evaluator
    assert hashlib.sha256((archive / "status.json").read_bytes()).hexdigest() == original_status_hash
    json_write(FINALIZATION / "REPORTING_REGRESSION.json", {
        "passed": True, "formatting_only": True, "records": regression,
        "numerical_keys_compared_exactly": list(numerical_keys),
        "participant_unchanged": True, "input_unchanged": True,
        "physics_audit_and_artifact_guards_unchanged": True,
        "changed_root_evaluator_files": ["evaluate.py", "reporting.py"],
        "original_archives_unchanged": True, "target_ratio": 1.12,
        "input_sha256": new["v2"]["input_sha256"],
    })
    summary_keys = ("score", "valid", "admissible", "converged", "independent_audit_passed")
    status = dict(original_status)
    status.update({
        "schema_version": 2, "status": "solved", "hard": False,
        "hardness_assessment": "not_hard; no genuine difficult ratchet established",
        "solvability_demonstrated_by_fresh": True,
        "original_passing_fresh_count": 2, "original_fresh_results": fresh,
        "fresh_runner_launched": True, "new_fresh_launches_during_finalization": 0,
        "ready_for_initial_attempts": False,
        "active_numerical_generation": 0, "promoted_ratchet_generations": 0,
        "actual_search_replay_count": 23,
        "completed_admissible_replay_count": 23, "completed_passing_replay_count": 15,
        "completed_admissible_failing_replay_count": 8,
        "best_frozen_v2": {**{key: new["v2"][key] for key in summary_keys},
                           "artifact": "champions/generation_1/frozen_submission/witness.npz",
                           "result": "adversary/finalization/validation/root_v2.json",
                           "archive_generation_is_not_a_promoted_ratchet": True},
        "baseline": {key: new["baseline"][key] for key in summary_keys},
        "minimax_review": {
            "case": "middle_cross_45", "target_ratio": 1.09,
            "private_score": 1.094955838159416,
            "actual_search_all_family_endpoint_oracle_score": 1.0877026333364312,
            "genuine_method_level_gap": True,
            "cheap_private_interpolation_score": 1.094290457685765,
            "cheap_private_interpolation_cpu_seconds": 8.621409096999999,
            "hardness_survived_repair": False, "promoted": False,
        },
        "n24_review": {
            "private_score": 1.1219300515770714, "private_valid": True,
            "target_ratio": 1.11, "baseline_score": 1.0,
            "replay_status": "inconclusive_600_second_stage_cap",
            "stage_cap_seconds": 600, "artifact_emitted": False,
            "resource_record": "empty; subsequent JSON parsing error preserved and reader hardened",
            "one_hour_opportunity_tested": False,
            "genuine_optimizer_or_quality_gap_established": False, "promoted": False,
            "evidence": "adversary/generation_1/large_patch_probe/replay_summary.json",
        },
        "reporting_finalization": {
            "formatting_only": True, "numerical_contract_unchanged": True,
            "original_archive": "adversary/finalization/original_root",
            "regression": "adversary/finalization/REPORTING_REGRESSION.json",
            "reason_on_every_evaluation_outcome": True,
            "score_definition": new["v2"]["score_definition"],
            "runtime_and_resource_measurements": True,
        },
        "review_complete": True, "remaining_scheduled_search_seconds": 0,
        "reason": "Solved, not hard: two original independent fresh attempts pass. The minimax method gap admits a cheap interpolation repair; the n24 600-second stop is inconclusive, not a demonstrated one-hour failure. No altered numerical task or ratchet is promoted. Only reporting additions are active; original v2 and baseline numerical verdicts are reproduced exactly.",
    })
    json_write(ROOT / "status.json", status)
    json_write(FINALIZATION / "final_manifest.json", {
        "root_status_sha256": hashlib.sha256((ROOT / "status.json").read_bytes()).hexdigest(),
        "root_evaluator": hashes(ROOT / "evaluator"),
        "root_participant_unchanged": hashes(ROOT / "participant") == before_participant,
        "root_input_unchanged": hashes(ROOT / "input") == before_input,
        "root_changed_paths": ["evaluator/evaluate.py", "evaluator/reporting.py", "status.json"],
        "new_fresh_launches": 0, "promoted_ratchet_generations": 0,
        "original_v2_score": fresh[1]["score"], "rescored_v2_score": new["v2"]["score"],
        "baseline_score": new["baseline"]["score"], "regression_passed": True,
    })
    print(json.dumps({"status": "solved", "hard": False, "v2_score": new["v2"]["score"],
                      "v2_valid": new["v2"]["valid"], "baseline_score": new["baseline"]["score"],
                      "baseline_admissible": new["baseline"]["admissible"], "baseline_valid": new["baseline"]["valid"],
                      "exact_regression_cases": len(regression), "inputs_unchanged": True,
                      "promoted_ratchet_generations": 0}), flush=True)


if __name__ == "__main__":
    main()
