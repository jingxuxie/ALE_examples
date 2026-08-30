"""Seal private full-suite evidence without changing activated task assets."""

import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time

STARTED = time.process_time()
from run_suite import CONCEPT, PROTOCOL, SIDECAR, digest, identities


def main():
    active_identity = identities()
    full_reports = []
    for tag in ("candidate_1_full", "candidate_1_full_repeat"):
        report_path = SIDECAR / "reports" / (tag + ".json")
        provenance_path = SIDECAR / "reports" / (tag + ".provenance.json")
        report = json.loads(report_path.read_text())
        provenance = json.loads(provenance_path.read_text())
        if digest(report_path) != provenance["report_sha256"]:
            raise RuntimeError("Report hash mismatch")
        for key in ("prelaunch_seal_sha256", "dataset_manifest_sha256", "policy_sha256", "case_file_sha256", "reference_file_sha256"):
            if provenance[key] != active_identity[key]:
                raise RuntimeError("Wrong active generation identity: " + key)
        if len(report["cases"]) != 20 or not report["complete_suite"]:
            raise RuntimeError("Expected the full unchanged twenty-case suite")
        for filename, expected in provenance["candidate_files_sha256"].items():
            if digest(SIDECAR / "candidate_1" / filename) != expected:
                raise RuntimeError("Candidate source changed after a full-suite run")
        full_reports.append({
            "report": str(report_path.relative_to(SIDECAR)),
            "report_sha256": digest(report_path),
            "provenance": str(provenance_path.relative_to(SIDECAR)),
            "prelaunch_seal_sha256": provenance["prelaunch_seal_sha256"],
            "dataset_manifest_sha256": provenance["dataset_manifest_sha256"],
            "verified_sealed_files": provenance["verified_sealed_files"],
            "command": provenance["command"],
            "codepath": provenance["codepath"],
            "core_score": report["core_score"],
            "worst_family_score": report["worst_family_score"],
            "passed": report["passed"],
            "accepted_cases": sum(case["accepted"] for case in report["cases"]),
            "case_count": len(report["cases"]),
            "runtime": report["runtime"],
            "resources": report["resources"],
            "passing_candidate": provenance["passing_candidate"],
            "consumed_cpu_seconds": provenance["consumed_cpu_seconds"],
            "max_gap_residual": max(case.get("gap_residual", 0) for case in report["cases"]),
            "max_z_residual": max(case.get("z_residual", 0) for case in report["cases"]),
            "max_branch_error": max(case.get("branch_error", 0) for case in report["cases"]),
        })
    imported = set()
    input_loads = []
    forbidden_literals = []
    forbidden_calls = []
    for path in (SIDECAR / "candidate_1").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if any(marker in node.value for marker in ("case_", "continuum_0", "/hidden", "references/", "champions/", "adversary/", "generation_")):
                    forbidden_literals.append({"file": path.name, "line": node.lineno, "value": node.value})
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("open", "exec", "eval", "compile", "__import__"):
                    forbidden_calls.append({"file": path.name, "line": node.lineno, "call": node.func.id})
                if isinstance(node.func, ast.Attribute) and node.func.attr == "load":
                    argument = node.args[0] if node.args else None
                    runtime_input = isinstance(argument, ast.Attribute) and argument.attr == "input"
                    input_loads.append({"file": path.name, "line": node.lineno, "runtime_cli_input_only": runtime_input})
    allowed = {"os", "argparse", "time", "json", "sys", "numpy", "scipy", "v4", "operator_core"}
    if imported - allowed:
        raise RuntimeError("Unexpected candidate import")
    source_files = sorted(path.name for path in (SIDECAR / "candidate_1").iterdir())
    source_audit = {
        "generation": 3,
        "prelaunch_seal_sha256": active_identity["prelaunch_seal_sha256"],
        "dataset_manifest_sha256": active_identity["dataset_manifest_sha256"],
        "imports": sorted(imported),
        "source_files": source_files,
        "no_packaged_numerical_data": source_files == ["operator_core.py", "solve.py", "v4.py"],
        "fixture_or_private_path_literals": forbidden_literals,
        "dynamic_execution_or_direct_file_open_calls": forbidden_calls,
        "numpy_input_loads": input_loads,
        "all_numpy_loads_use_runtime_cli_input": bool(input_loads) and all(entry["runtime_cli_input_only"] for entry in input_loads),
        "manual_review": "Full solver source reviewed: every physical array is derived from the current runtime input; no fixture IDs, reference arrays, stored solution initialization, private file paths, environment-based fixture selection or shell/network execution. The <=8-mode dispatch is an algorithmic cost choice, not an instance identifier.",
        "candidate_imported_in_trusted_parent": False,
        "audit_limit": "Static checks plus source review and sandboxed dynamic scoring; not a general formal proof for arbitrary future source changes."
    }
    source_audit["passed"] = (not forbidden_literals and not forbidden_calls
                              and source_audit["no_packaged_numerical_data"]
                              and source_audit["all_numpy_loads_use_runtime_cli_input"])
    if not source_audit["passed"]:
        raise RuntimeError("Fixture-free source audit failed")
    (SIDECAR / "source_audit.json").write_text(json.dumps(source_audit, indent=2, allow_nan=False) + "\n")
    if digest(SIDECAR / "candidate_1/v4.py") != PROTOCOL["source_sha256"]:
        raise RuntimeError("Earlier private champion source changed")
    audit = json.loads((SIDECAR / "operator_audit.json").read_text())
    provenance_files = sorted((SIDECAR / "reports").glob("*.provenance.json"))
    suite_cpu = sum(json.loads(path.read_text())["consumed_cpu_seconds"] for path in provenance_files)
    audit_cpu = audit["consumed_cpu_seconds"]
    passed = all(report["passed"] for report in full_reports)
    summary = {
        "generation": 3,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "portfolio_status": "stopped_after_confirmed_same_budget_pass" if passed else "stopped_no_confirmed_passing_candidate",
        "passing_candidate": "candidate_1" if passed else None,
        "same_budget_joint_attainability": "demonstrated" if passed else "unknown",
        "fresh_v5_hardness_outcome": "not_observed_by_this_private_sidecar; parent controls final integration",
        "prelaunch_seal_sha256": active_identity["prelaunch_seal_sha256"],
        "dataset_manifest_sha256": active_identity["dataset_manifest_sha256"],
        "policy_sha256": active_identity["policy_sha256"],
        "active_sealed_files_verified_unchanged": active_identity["verified_sealed_files"],
        "candidate_count": 1,
        "candidate_limit": PROTOCOL["maximum_candidates"],
        "candidate_2_attempted": False,
        "source_champion_sha256": PROTOCOL["source_sha256"],
        "candidate_files_sha256": {path.name: digest(path) for path in sorted((SIDECAR / "candidate_1").glob("*.py"))},
        "full_suite_reports": full_reports,
        "diagnostic_reports": ["reports/candidate_1_continuum.json", "operator_audit.json"],
        "operator_audit_passed": audit["passed"],
        "operator_audit_checks_passed": sum(check["passed"] for check in audit["checks"]),
        "fixture_free_source_audit": "source_audit.json",
        "fixture_free_source_audit_passed": source_audit["passed"],
        "operator_audit_max_exact_fusion_relative_error": max(check["relative_error"] for check in audit["checks"] if check["name"].startswith("fused_")),
        "operator_audit_max_prefix_modal_relative_error": max(check["relative_error"] for check in audit["checks"] if check["name"].startswith("prefix_modal_")),
        "source_import_audit": sorted(imported),
        "source_champion_preserved_exactly": True,
        "root_cause_observations": [
            "Mode-by-mode exact FFT application and dense per-mode coarse finite sums caused the prior continuum resource failures.",
            "The candidate fuses all runtime phonon bins into the exact patch-pair Fourier symbol; full-grid nonlinear residuals retain every mode without truncation.",
            "Signed kernel prefix moments construct exact linear-interpolation coarse finite sums; a weighted SVD compresses those warm-start kernels, not raw patch couplings.",
            "The compressed coarse Jacobian preconditions exact full-grid residual corrections; the mode<=8 path keeps the archived private v4 method unchanged.",
            "This is an operator/resource fix, not a quality-gate change, branch-label lookup, or reference-initialized solve."
        ],
        "inference_uses_only_runtime_public_input": True,
        "candidate_imported_in_trusted_parent": False,
        "active_participant_evaluator_status_modified": False,
        "fresh_v5_code_read_or_contacted": False,
        "private_archive": "champions/privileged_generation_3",
        "private_archive_submission": "champions/privileged_generation_3/frozen_submission",
        "archive_write_authorized_by_parent": True,
        "consumed_suite_cpu_seconds": suite_cpu,
        "consumed_operator_audit_cpu_seconds": audit_cpu,
        "consumed_summary_cpu_seconds": time.process_time() - STARTED,
        "cpu_budget_seconds": PROTOCOL["cpu_budget_seconds"],
        "cpu_accounting": "Measured controller process CPU plus parent-observed RUSAGE_CHILDREN for every numerical test; includes trusted residual/branch verification. Lightweight shell editing/inspection overhead is not instrumented.",
        "reproduction": "See each full-suite report's companion provenance and README.md. All source/report artifacts remain private in this directory."
    }
    summary["consumed_cpu_seconds"] = suite_cpu + audit_cpu + summary["consumed_summary_cpu_seconds"]
    summary["remaining_measured_cpu_seconds"] = PROTOCOL["cpu_budget_seconds"] - summary["consumed_cpu_seconds"]
    if summary["remaining_measured_cpu_seconds"] < 0:
        raise RuntimeError("Private CPU budget exceeded")
    (SIDECAR / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    archive = CONCEPT / "champions/privileged_generation_3"
    archive.mkdir()
    submission = archive / "frozen_submission"
    submission.mkdir()
    evidence = archive / "evidence"
    evidence.mkdir()
    for filename, expected in summary["candidate_files_sha256"].items():
        shutil.copyfile(SIDECAR / "candidate_1" / filename, submission / filename)
        if digest(submission / filename) != expected:
            raise RuntimeError("Archive source mismatch")
    for report in full_reports:
        for filename in (report["report"], report["provenance"]):
            shutil.copyfile(SIDECAR / filename, evidence / Path(filename).name)
    for filename in ("operator_audit.json", "source_audit.json", "summary.json", "protocol.json"):
        shutil.copyfile(SIDECAR / filename, evidence / filename)
    shutil.copyfile(SIDECAR / "archive_README.md", archive / "README.md")
    archive_provenance = {
        "generation": 3,
        "private_only": True,
        "passing_candidate": "frozen_submission",
        "active_prelaunch_seal_sha256": active_identity["prelaunch_seal_sha256"],
        "dataset_manifest_sha256": active_identity["dataset_manifest_sha256"],
        "verified_active_sealed_files": active_identity["verified_sealed_files"],
        "source_sidecar": str(SIDECAR),
        "inference_source_is_byte_identical_to_both_passing_full_suite_runs": True,
        "candidate_code_files": summary["candidate_files_sha256"],
        "full_suite_reports": full_reports,
        "source_fixture_free_audit_passed": source_audit["passed"],
        "operator_audit_checks_passed": summary["operator_audit_checks_passed"],
        "source_only_sandbox_mount": "Use frozen_submission, not this archive root; private evidence stays outside the candidate mount.",
        "files": {str(path.relative_to(archive)): digest(path) for path in sorted(archive.rglob("*")) if path.is_file()}
    }
    (archive / "provenance.json").write_text(json.dumps(archive_provenance, indent=2, allow_nan=False) + "\n")
    if identities() != active_identity:
        raise RuntimeError("Active assets changed during archival")
    paths = [path for path in SIDECAR.rglob("*") if path.is_file()
             and "scratch" not in path.relative_to(SIDECAR).parts
             and path.name != "private_seal.json"]
    seal = {"generation": 3, "active_prelaunch_seal_sha256": active_identity["prelaunch_seal_sha256"],
            "dataset_manifest_sha256": active_identity["dataset_manifest_sha256"],
            "private_archive_provenance_sha256": digest(archive / "provenance.json"),
            "files": {str(path.relative_to(SIDECAR)): digest(path) for path in sorted(paths)}}
    (SIDECAR / "private_seal.json").write_text(json.dumps(seal, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: summary[key] for key in ("passing_candidate", "same_budget_joint_attainability", "consumed_cpu_seconds", "active_sealed_files_verified_unchanged", "operator_audit_checks_passed")}))


if __name__ == "__main__":
    main()
