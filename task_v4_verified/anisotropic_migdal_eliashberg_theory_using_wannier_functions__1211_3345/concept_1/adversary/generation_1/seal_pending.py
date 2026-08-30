"""Audit and seal a review-only ratchet without touching the active package."""

from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


PENDING = Path(__file__).resolve().parent
ORIGINAL = PENDING.parents[1]
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


def short_score(report):
    return {"accepted_cases": sum(case["accepted"] for case in report["cases"]),
            "total_cases": len(report["cases"]), "core_score": report["core_score"],
            "worst_family_score": report["worst_family_score"], "passed": report["passed"],
            "family_rates": report["family_rates"], "runtime": report["runtime"]}


def main():
    hidden = PACKAGE / "evaluator" / "hidden"
    if (hidden / "prelaunch_seal.json").exists():
        raise FileExistsError("pending generation is already sealed")
    selection = json.loads((PENDING / "selection.json").read_text())
    policy = json.loads((hidden / "policy.json").read_text())
    baseline = json.loads((PACKAGE / "attempts" / "baseline_report.json").read_text())
    fresh = json.loads((PACKAGE / "attempts" / "previous_fresh_report.json").read_text())
    anchor = json.loads((hidden / "baseline_anchor.json").read_text())
    manifest = json.loads((hidden / "manifest.json").read_text())
    assert baseline["complete_suite"] and fresh["complete_suite"]
    assert baseline["core_score"] == 0.5 and baseline["worst_family_score"] == 0
    assert fresh["core_score"] == 0.8 and fresh["worst_family_score"] == 0.5 and not fresh["passed"]
    assert anchor["report_sha256"] == digest(PACKAGE / "attempts" / "baseline_report.json")
    assert anchor["score"] + policy["improvement_target"] <= 1
    assert fresh["baseline_score"] == anchor["score"]
    for report in (baseline, fresh):
        assert report["policy_sha256"] == digest(hidden / "policy.json")
    for family in policy["families"]:
        assert sum(case["family"] == family for case in manifest["cases"]) == 4
    failures = {case["case_id"]: case for case in fresh["cases"] if not case["accepted"]}
    assert set(failures) == set(selection["replacements"])
    assert all(case["cpu_seconds"] >= 12 and case["returncode"] != 0 for case in failures.values())
    audit_log = (PENDING / "pending_audit.log").read_text()
    assert "Ran 23 tests" in audit_log and audit_log.rstrip().endswith("OK")
    write_text(PACKAGE / "adversary" / "audit.log", audit_log)

    snapshot = json.loads((PENDING / "generation_0_snapshot_manifest.json").read_text())
    active_mismatches = []
    for relative, expected in snapshot["sha256"].items():
        if relative.startswith("concept_1/"):
            current = ORIGINAL / relative.removeprefix("concept_1/")
        else:
            current = ORIGINAL.parent / relative
        if digest(current) != expected:
            active_mismatches.append(relative)
    assert not active_mismatches, active_mismatches
    archive_path = PENDING / "generation_0_runnable_snapshot.tar.gz"
    with tarfile.open(archive_path, "r:gz") as archive:
        archive_hashes = {member.name: hashlib.sha256(archive.extractfile(member).read()).hexdigest()
                          for member in archive.getmembers() if member.isfile()}
    assert archive_hashes == snapshot["sha256"]
    archive_smoke = json.loads((PENDING / "archive_smoke.json").read_text())
    assert len(archive_smoke["cases"]) == 1 and archive_smoke["cases"][0]["accepted"]
    assert digest(PACKAGE.parent / "authoring" / "sandbox_runner.py") == snapshot["sha256"]["authoring/sandbox_runner.py"]
    for filename in ("evaluate.py", "launch.py"):
        assert digest(PACKAGE / "evaluator" / filename) == digest(ORIGINAL / "evaluator" / filename)
    assert digest(PACKAGE / "participant" / "baseline" / "solve.py") == anchor["baseline_sha256"]
    assert digest(PACKAGE / "participant" / "workspace" / "solve.py") == anchor["baseline_sha256"]
    provenance = json.loads((ORIGINAL / "champions" / "generation_1" / "provenance.json").read_text())
    assert digest(ORIGINAL / "champions" / "generation_1" / "solve.py") == provenance["source_sha256"]["solve.py"]

    reference_summary = []
    for case_id, probe_id in selection["replacements"].items():
        certificate = json.loads((hidden / "references" / (case_id + ".json")).read_text())
        measurement = json.loads((PENDING / "probes" / probe_id / "measurement.json").read_text())
        assert certificate["valid"] and measurement["resource_failure_well_outside_12_cpu"]
        assert measurement["extended_96_cpu_execution"]["cpu_seconds"] > 3 * policy["cpu_seconds"]
        assert digest(hidden / "cases" / (case_id + ".npz")) == certificate["instance_sha256"]
        assert digest(hidden / "references" / (case_id + ".npz")) == certificate["reference_sha256"]
        reference_summary.append({
            "case_id": case_id, "probe_id": probe_id,
            "normal_eigenvalue": next(case["linear_eigenvalue"] for case in manifest["cases"] if case["case_id"] == case_id),
            "all_frequency_gap_residual": certificate["primary_all_frequency"]["gap_residual"],
            "all_frequency_z_residual": certificate["primary_all_frequency"]["z_residual"],
            "direct_row_gap_residual": certificate["primary_direct_rows"]["gap_residual"],
            "cross_start_error": certificate["second_start_all_frequency"]["branch_error"],
            "extended_fresh_cpu_seconds": measurement["extended_96_cpu_execution"]["cpu_seconds"],
            "fixed_budget_fresh_cpu_seconds": failures[case_id]["cpu_seconds"],
            "failure_cluster": "CPU_limit",
        })
    timestamp = datetime.now(timezone.utc).isoformat()
    audit = {"completed_at": timestamp, "tests_passed": 23, "tests_failed": 0,
             "numerics_and_package_tests": 12, "security_tests": 11,
             "prior_fresh_code_in_public_package": False,
             "public_python_identity": "Only byte-identical original baseline and supplied physics operator",
             "active_generation_zero_files_unchanged": True,
             "generation_zero_archive_files_verified": len(archive_hashes),
             "generation_zero_archive_sha256": digest(archive_path),
             "generation_zero_archive_case_00_smoke_accepted": True,
             "sandbox_runner_bundled_at_expected_relative_path": True,
             "sandbox_runner_sha256": digest(PACKAGE.parent / "authoring" / "sandbox_runner.py"),
             "private_reference_certificates": reference_summary,
             "normal_state_branch_false_success": "rejected",
             "private_files_network_process_thread_access": "denied",
             "symlinks_hardlinks_npz_bombs_object_arrays": "rejected",
             "expanded_40_by_32768_output": "accepted_by_32_MiB_parser"}
    write_json(PACKAGE / "adversary" / "audit_result.json", audit)
    probe_report = json.loads((PENDING / "probe_report.json").read_text())
    oracle = json.loads((PENDING / "probes" / "large_combined_a" / "oracle_certificate.json").read_text())
    evidence = {"generation": 1, "active": False, "target_fixed_before_next_fresh": selection["target_fixed_before_next_fresh_launch"],
                "public_baseline": short_score(baseline), "actual_previous_fresh": short_score(fresh),
                "actual_previous_fresh_sha256": provenance["source_sha256"]["solve.py"],
                "prior_pool_result": "12 of 12 accepted by actual previous fresh; insufficient as a ratchet",
                "selected_failures": reference_summary,
                "root_cause": "At the declared low temperature and independently anisotropic 40-patch grid, the previous fresh solver repeatedly contracts a dense patch-pair-by-frequency tensor and performs scale-sensitive nonlinear iterations. Four isolated runs exceed the CPU budget; extended identical-code runs take 40.50 to 94.79 CPU seconds and return accurate solutions. Thus the evidence is not a filename, output-size, memory-limit, or wall-jitter failure.",
                "physical_scope": "Exact finite-cutoff synthetic Fermi-surface patch Eliashberg models: N=32768, Omega_max/T=12000, last frequency/Omega_max=17.157, four positive modes spanning 1000 or 4000, normal pairing eigenvalue 1.00003 or 1.0001. Combined cases have weak interband coupling and induced gap ratios above 1e7. Patches have independently varied interactions, not repeated padding.",
                "offline_probe_and_reference_cpu_seconds": probe_report["aggregate_cpu_seconds"] + oracle["offline_oracle_cpu_seconds"],
                "joint_12_cpu_second_attainability": "not_established; offline references are quality certificates only",
                "no_new_fresh_agent_launched": True}
    write_json(PENDING / "ratchet_evidence.json", evidence)
    status = json.loads((PACKAGE / "status.json").read_text())
    status.update(concept="concept_1", status="ready_for_parent_review_pending_activation",
                  difficulty_status="provisional_ratchet_candidate",
                  attainability_status="offline_quality_verified_joint_speed_quality_open",
                  objective_frozen=True, participant_and_evaluator_frozen=True,
                  fresh_agent_launched_by_builder=False, fresh_agent_launcher="parent_only",
                  fresh_agent_outcome="generation_1_not_launched", prelaunch_sealed_at=timestamp,
                  policy_sha256=digest(hidden / "policy.json"), baseline=short_score(baseline),
                  previous_fresh_private_evidence=short_score(fresh),
                  objective=dict(selection["target_fixed_before_next_fresh_launch"], baseline_worst_family_score=anchor["score"]),
                  audit={key: audit[key] for key in ("tests_passed", "tests_failed", "active_generation_zero_files_unchanged", "prior_fresh_code_in_public_package")},
                  reference_certification={"valid_cases": 20, "starts_per_new_case": 2,
                      "new_cases": reference_summary, "quality_does_not_establish_budgeted_attainability": True},
                  runtime=fresh["resources"],
                  recommended_parent_runtime={"fresh_agent_seconds": 3600, "typical_evaluation_allowance_seconds": 900},
                  paths={"task": "participant/TASK.md", "format": "participant/input/FORMAT.md",
                         "baseline": "participant/baseline", "submission": "participant/workspace",
                         "evaluator": "evaluator/evaluate.py", "shared_harness": "../authoring/sandbox_runner.py",
                         "baseline_anchor": "evaluator/hidden/baseline_anchor.json",
                         "prelaunch_seal": "evaluator/hidden/prelaunch_seal.json",
                         "audit": "adversary/audit_result.json",
                         "private_previous_fresh_report": "attempts/previous_fresh_report.json"})
    write_json(PACKAGE / "status.json", status)
    sealed_files = {}
    for path in sorted(PACKAGE.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            assert not path.is_symlink()
            sealed_files[str(path.relative_to(PACKAGE))] = digest(path)
    sealed_files["../authoring/sandbox_runner.py"] = digest(PACKAGE.parent / "authoring" / "sandbox_runner.py")
    seal = {"generation": 1, "active": False, "sealed_at": timestamp,
            "fresh_agent_launched_by_builder": False, "parent_review_required_before_activation": True,
            "policy_sha256": digest(hidden / "policy.json"),
            "selection_sha256": digest(PENDING / "selection.json"),
            "baseline_report_sha256": digest(PACKAGE / "attempts" / "baseline_report.json"),
            "baseline_code_sha256": anchor["baseline_sha256"],
            "prior_fresh_code_is_public": False, "files": sealed_files}
    write_json(hidden / "prelaunch_seal.json", seal)
    assert all(digest(PACKAGE / path) == expected for path, expected in sealed_files.items())
    print(json.dumps({"ready": True, "active": False, "package": str(PACKAGE),
                      "sealed_files": len(sealed_files), "baseline": short_score(baseline),
                      "previous_fresh": short_score(fresh), "tests_passed": 23}))


if __name__ == "__main__":
    main()
