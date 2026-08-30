"""Seal generation two for parent review without modifying the active task."""

from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import subprocess


PENDING = Path(__file__).resolve().parent
ROOT = PENDING.parents[1]
PACKAGE = PENDING / "package" / "concept_1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_text(path, text):
    if path.exists():
        old = path.read_text()
        if old == text:
            return
        difference = list(difflib.unified_diff(old.splitlines(True), text.splitlines(True), n=3))
        body = "*** Update File: " + str(path) + "\n" + "".join("@@\n" if line.startswith("@@") else line for line in difference[2:])
    else:
        body = "*** Add File: " + str(path) + "\n" + "".join("+" + line + "\n" for line in text.splitlines())
    subprocess.run(["apply_patch"], input="*** Begin Patch\n" + body + "*** End Patch\n", text=True, check=True)


def write_json(path, value):
    write_text(path, json.dumps(value, indent=2, allow_nan=False) + "\n")


def score(report):
    return {"accepted_cases": sum(case["accepted"] for case in report["cases"]),
            "total_cases": len(report["cases"]), "core_score": report["core_score"],
            "worst_family_score": report["worst_family_score"], "passed": report["passed"],
            "family_rates": report["family_rates"], "runtime": report["runtime"]}


def main():
    hidden = PACKAGE / "evaluator" / "hidden"
    assert not (hidden / "prelaunch_seal.json").exists()
    selection = json.loads((PENDING / "selection.json").read_text())
    policy = json.loads((hidden / "policy.json").read_text())
    original_policy = json.loads((ROOT / "evaluator" / "hidden" / "policy.json").read_text())
    for key, value in original_policy.items():
        if key not in ("version", "frozen_at"):
            assert policy[key] == value
    baseline = json.loads((PACKAGE / "attempts" / "baseline_report.json").read_text())
    fresh = json.loads((PACKAGE / "attempts" / "previous_fresh_report.json").read_text())
    anchor = json.loads((hidden / "baseline_anchor.json").read_text())
    assert baseline["complete_suite"] and fresh["complete_suite"]
    assert baseline["core_score"] == 0.5 and baseline["worst_family_score"] == 0
    assert fresh["core_score"] == 0.8 and fresh["worst_family_score"] == 0.5 and not fresh["passed"]
    assert fresh["baseline_score"] == anchor["score"]
    assert anchor["score"] + policy["improvement_target"] <= 1
    assert anchor["report_sha256"] == digest(PACKAGE / "attempts" / "baseline_report.json")
    for report in (baseline, fresh):
        assert report["policy_sha256"] == digest(hidden / "policy.json")
    failures = {case["case_id"]: case for case in fresh["cases"] if not case["accepted"]}
    assert set(failures) == set(selection["replacements"])
    assert all(case["returncode"] == 0 and case["cpu_seconds"] < 12 and case["branch_error"] > 0.04 for case in failures.values())
    for case_id in ("case_10", "case_11"):
        assert failures[case_id]["gap_residual"] <= policy["gap_residual_max"]
        assert failures[case_id]["branch_error"] > 0.99
    audit_log = (PENDING / "pending_audit.log").read_text()
    assert "Ran 27 tests" in audit_log and audit_log.rstrip().endswith("OK")
    write_text(PACKAGE / "adversary" / "audit.log", audit_log)
    snapshot = json.loads((PENDING / "generation_1_snapshot_manifest.json").read_text())
    mismatches = []
    for relative, expected in snapshot["sha256"].items():
        path = ROOT / relative.removeprefix("concept_1/") if relative.startswith("concept_1/") else ROOT.parent / relative
        if digest(path) != expected:
            mismatches.append(relative)
    assert not mismatches, mismatches
    assert digest(PENDING / snapshot["archive"]) == snapshot["archive_sha256"]
    smoke = json.loads((PENDING / "archive_smoke.json").read_text())
    assert smoke["cases"][0]["accepted"]
    for filename in ("evaluate.py", "launch.py", "hidden/physics.py"):
        assert digest(PACKAGE / "evaluator" / filename) == digest(ROOT / "evaluator" / filename)
    assert digest(PACKAGE.parent / "authoring" / "sandbox_runner.py") == digest(ROOT.parent / "authoring" / "sandbox_runner.py")
    for directory in ("baseline", "workspace"):
        assert digest(PACKAGE / "participant" / directory / "solve.py") == digest(ROOT / "participant" / directory / "solve.py")
    manifest = json.loads((hidden / "manifest.json").read_text())
    for record in manifest["cases"]:
        if record["case_id"] not in selection["replacements"]:
            for folder in ("cases", "references"):
                relative = Path(folder) / (record["case_id"] + ".npz")
                assert digest(hidden / relative) == digest(ROOT / "evaluator" / "hidden" / relative)
    provenance = json.loads((ROOT / "champions" / "generation_2" / "provenance.json").read_text())
    fresh_hash = digest(ROOT / "champions" / "generation_2" / "solve.py")
    assert fresh_hash == provenance["source_sha256"]["solve.py"]
    diagnostic = json.loads((PENDING / "linear_diagnostic.json").read_text())
    assert diagnostic["actual_v3_code_sha256"] == fresh_hash
    reference_summary = []
    for case_id, probe_id in selection["replacements"].items():
        certificate = json.loads((hidden / "references" / (case_id + ".json")).read_text())
        assert certificate["valid"]
        assert digest(hidden / "cases" / (case_id + ".npz")) == certificate["instance_sha256"]
        assert digest(hidden / "references" / (case_id + ".npz")) == certificate["reference_sha256"]
        reference_summary.append({"case_id": case_id, "probe_id": probe_id,
                                  "gap_residual": certificate["primary_all_frequency"]["gap_residual"],
                                  "z_residual": certificate["primary_all_frequency"]["z_residual"],
                                  "cross_start_error": certificate["second_start_all_frequency"]["branch_error"],
                                  "minimum_low_gap_over_piT": certificate["minimum_low_gap_over_piT"],
                                  "patches_with_frequency_sign_changes": certificate["patches_with_frequency_sign_changes"],
                                  "previous_fresh_branch_error": failures[case_id]["branch_error"],
                                  "previous_fresh_cpu_seconds": failures[case_id]["cpu_seconds"]})
    timestamp = datetime.now(timezone.utc).isoformat()
    audit = {"completed_at": timestamp, "tests_passed": 27, "tests_failed": 0,
             "physics_package_and_ratchet_tests": 16, "security_tests": 11,
             "participant_code": "Only unchanged original public baseline/workspace and physics operator",
             "prior_fresh_code_is_public": False, "active_generation_one_unchanged": True,
             "archived_generation_one_files_verified": len(snapshot["sha256"]),
             "archive_smoke_accepted": True, "runner_sha256": digest(PACKAGE.parent / "authoring" / "sandbox_runner.py"),
             "scoring_and_verifier_code_unchanged": True,
             "previous_large_grid_cases_retained": selection["retained_large_grid_cases"],
             "new_reference_certificates": reference_summary,
             "normal_state_false_success_guard": "Rejects actual v3 near-normal outputs despite acceptable residuals and signs",
             "security": "Private reads, network, fork/threads, symlinks/hardlinks, object arrays and NPZ expansion attacks remain tested"}
    write_json(PACKAGE / "adversary" / "audit_result.json", audit)
    probe = json.loads((PENDING / "probe_report.json").read_text())
    evidence = {"generation": 2, "active": False, "actual_previous_fresh_sha256": fresh_hash,
                "public_baseline": score(baseline), "actual_previous_fresh": score(fresh),
                "probe_cases": len(probe["cases"]), "probe_certified_cases": sum(case.get("reference_valid", False) for case in probe["cases"]),
                "probe_previous_fresh_failures": sum(case.get("actual_v3_accepted") is False for case in probe["cases"]),
                "probe_cpu_seconds": probe["aggregate_cpu_seconds"],
                "selected_references": reference_summary, "linear_diagnostic": diagnostic,
                "root_cause": "The actual v3 reduced collocation operators shift supercritical global or sheet-local eigenvalues below one. Their coarse Newton initializers and approximate inverse then produce near-normal or inaccurate weak-sheet outputs even though exact full-grid references remain nonzero. Both globally critical outputs have accepted residuals but branch error approximately one. The four selected failures are numerical/branch failures with return code zero, not resource or dimension failures.",
                "same_budget_quality_and_resources_unchanged": True,
                "joint_generation_two_attainability": "not_established; independent offline certificates are quality evidence only",
                "original_public_baseline_is_anchor": True, "phonon_quadrature_fallback_used": False,
                "no_new_fresh_agent_launched": True}
    write_json(PENDING / "ratchet_evidence.json", evidence)
    status = json.loads((PACKAGE / "status.json").read_text())
    status.update(status="ready_for_parent_review_pending_activation", objective_frozen=True,
                  participant_and_evaluator_frozen=True, prelaunch_sealed_at=timestamp,
                  policy_sha256=digest(hidden / "policy.json"), baseline=score(baseline),
                  previous_fresh_private_evidence=score(fresh),
                  objective=dict(selection["target_fixed_before_next_fresh_launch"], baseline_worst_family_score=anchor["score"]),
                  audit={key: audit[key] for key in ("tests_passed", "tests_failed", "active_generation_one_unchanged", "prior_fresh_code_is_public")},
                  reference_certification={"valid_cases": 20, "new_cases": reference_summary,
                      "starts_per_new_case": 2, "quality_does_not_establish_budgeted_attainability": True},
                  fresh_agent_launcher="parent_only", fresh_agent_outcome="generation_2_not_launched",
                  runtime=fresh["resources"], recommended_parent_runtime={"fresh_agent_seconds": 3600, "typical_evaluation_allowance_seconds": 900},
                  paths={"task": "participant/TASK.md", "format": "participant/input/FORMAT.md", "baseline": "participant/baseline",
                         "submission": "participant/workspace", "evaluator": "evaluator/evaluate.py", "shared_harness": "../authoring/sandbox_runner.py",
                         "baseline_anchor": "evaluator/hidden/baseline_anchor.json", "prelaunch_seal": "evaluator/hidden/prelaunch_seal.json",
                         "audit": "adversary/audit_result.json", "private_previous_fresh_report": "attempts/previous_fresh_report.json"})
    write_json(PACKAGE / "status.json", status)
    files = {}
    for path in sorted(PACKAGE.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            assert not path.is_symlink()
            files[str(path.relative_to(PACKAGE))] = digest(path)
    files["../authoring/sandbox_runner.py"] = digest(PACKAGE.parent / "authoring" / "sandbox_runner.py")
    seal = {"generation": 2, "ratchet_index": 2, "active": False, "sealed_at": timestamp,
            "parent_review_required_before_activation": True, "fresh_agent_launched_by_builder": False,
            "policy_sha256": digest(hidden / "policy.json"), "selection_sha256": digest(PENDING / "selection.json"),
            "baseline_report_sha256": digest(PACKAGE / "attempts" / "baseline_report.json"),
            "baseline_code_sha256": anchor["baseline_sha256"], "prior_fresh_code_is_public": False, "files": files}
    write_json(hidden / "prelaunch_seal.json", seal)
    assert all(digest(PACKAGE / relative) == expected for relative, expected in files.items())
    print(json.dumps({"ready": True, "active": False, "package": str(PACKAGE), "sealed_files": len(files),
                      "baseline": score(baseline), "actual_previous_fresh": score(fresh), "tests_passed": 27}))


if __name__ == "__main__":
    main()
