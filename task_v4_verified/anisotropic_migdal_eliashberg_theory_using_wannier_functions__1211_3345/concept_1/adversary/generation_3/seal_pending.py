"""Audit and seal the inactive final ratchet; never mutate the active generation."""

from datetime import datetime, timezone
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time

PENDING = Path(__file__).resolve().parent
ROOT = PENDING.parents[1]
SIDECAR = ROOT / "adversary" / "prospective_generation3"
PACKAGE = PENDING / "package" / "concept_1"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_text(path, text):
    if path.exists():
        original = path.read_text()
        if original == text:
            return
        difference = list(difflib.unified_diff(original.splitlines(True), text.splitlines(True), n=3))
        body = "*** Update File: " + str(path) + "\n" + "".join("@@\n" if line.startswith("@@") else line for line in difference[2:])
    else:
        body = "*** Add File: " + str(path) + "\n" + "".join("+" + line + "\n" for line in text.splitlines())
    subprocess.run(["apply_patch"], input="*** Begin Patch\n" + body + "*** End Patch\n", text=True, check=True)


def write_json(path, value):
    write_text(path, json.dumps(value, indent=2, allow_nan=False) + "\n")


def summary(report):
    return {"accepted_cases": sum(record["accepted"] for record in report["cases"]),
            "total_cases": len(report["cases"]), "core_score": report["core_score"],
            "worst_family_score": report["worst_family_score"], "passed": report["passed"],
            "family_rates": report["family_rates"], "runtime": report["runtime"]}


def main():
    started = time.process_time()
    hidden = PACKAGE / "evaluator" / "hidden"
    assert not (hidden / "prelaunch_seal.json").exists()
    selection = json.loads((PENDING / "selection.json").read_text())
    policy = json.loads((hidden / "policy.json").read_text())
    original_policy = json.loads((ROOT / "evaluator" / "hidden" / "policy.json").read_text())
    for key, value in original_policy.items():
        if key not in ("version", "frozen_at"):
            assert policy[key] == value
    baseline = json.loads((PACKAGE / "attempts" / "baseline_report.json").read_text())
    previous_context = json.loads((PACKAGE / "attempts" / "previous_fresh_report.json").read_text())
    fresh = json.loads((PENDING / "clean_v4_report.json").read_text())
    anchor = json.loads((hidden / "baseline_anchor.json").read_text())
    assert baseline["complete_suite"] and fresh["complete_suite"]
    assert baseline["core_score"] == 0.4 and baseline["worst_family_score"] == 0
    assert fresh["core_score"] == 0.8 and fresh["worst_family_score"] == 0.5 and not fresh["passed"]
    assert fresh["baseline_score"] == anchor["score"]
    assert anchor["score"] + policy["improvement_target"] <= 1
    assert anchor["report_sha256"] == digest(PACKAGE / "attempts" / "baseline_report.json")
    assert all(report["policy_sha256"] == digest(hidden / "policy.json") for report in (baseline, fresh))
    failures = {record["case_id"]: record for record in fresh["cases"] if not record["accepted"]}
    assert set(failures) == set(selection["replacements"])
    assert all(record["returncode"] == -24 and record["cpu_seconds"] > 11.5 for record in failures.values())
    write_json(PENDING / "archival_context_v4_report.json", previous_context)
    write_json(PACKAGE / "attempts" / "previous_fresh_report.json", fresh)
    old_audit = PENDING / "pending_audit.log"
    if old_audit.exists() and "FAILED" in old_audit.read_text():
        write_text(PENDING / "initial_audit_noncanonical_TMPDIR.log", old_audit.read_text())
    environment = dict(os.environ, TMPDIR=str(PENDING / "scratch"), PYTHONDONTWRITEBYTECODE="1")
    for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
        environment[variable] = "1"
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    with old_audit.open("wb") as log:
        result = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", str(PACKAGE / "adversary"),
                                 "-p", "test*.py", "-v"], env=environment, stdin=subprocess.DEVNULL,
                                stdout=log, stderr=subprocess.STDOUT, timeout=600)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    audit_cpu = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
    assert result.returncode == 0, old_audit.read_text()
    audit_log = old_audit.read_text()
    count = int(re.search(r"Ran (\d+) tests", audit_log).group(1))
    assert count == 29 and audit_log.rstrip().endswith("OK")
    write_text(PACKAGE / "adversary" / "audit.log", audit_log)
    protocol = json.loads((SIDECAR / "protocol.json").read_text())
    for relative, expected in protocol["active_sealed_files"].items():
        assert digest(ROOT / relative) == expected
    snapshot = json.loads((PENDING / "generation_2_snapshot_manifest.json").read_text())
    assert digest(PENDING / snapshot["archive"]) == snapshot["archive_sha256"]
    for relative, expected in snapshot["sha256"].items():
        path = ROOT / relative.removeprefix("concept_1/") if relative.startswith("concept_1/") else ROOT.parent / relative
        assert digest(path) == expected
    smoke = json.loads((PENDING / "generation_2_archive_smoke.json").read_text())
    assert smoke["cases"][0]["accepted"]
    for name in ("evaluate.py", "launch.py", "hidden/physics.py"):
        assert digest(PACKAGE / "evaluator" / name) == digest(ROOT / "evaluator" / name)
    assert digest(PACKAGE.parent / "authoring" / "sandbox_runner.py") == digest(ROOT.parent / "authoring" / "sandbox_runner.py")
    public_code = {str(path.relative_to(PACKAGE / "participant")): digest(path)
                   for path in (PACKAGE / "participant").rglob("*.py")}
    assert set(public_code) == {"baseline/solve.py", "workspace/solve.py", "input/eliashberg.py"}
    for relative, expected in public_code.items():
        assert digest(ROOT / "participant" / relative) == expected
    evidence = json.loads((SIDECAR / "continuum_audit.json").read_text())
    public_certificate = json.loads((PENDING / "private_public_example/certificate.json").read_text())
    assert public_certificate["valid"]
    assert public_certificate["instance_sha256"] == digest(PACKAGE / "participant/input/examples/phonon_continuum_96.npz")
    write_json(PACKAGE / "adversary" / "public_example_certificate.json", dict(public_certificate, case_id="phonon_continuum_96"))
    certificates = [json.loads((hidden / "references" / (case_id + ".json")).read_text()) for case_id in selection["replacements"]]
    max_residual = max(record[key][metric] for record in certificates
                       for key in ("primary_all_frequency", "second_start_all_frequency", "primary_direct_rows", "second_start_direct_rows")
                       for metric in ("gap_residual", "z_residual"))
    max_cross_start = max(record["second_start_all_frequency"]["branch_error"] for record in certificates)
    accounted = evidence["cpu_accounting"]["accounted_total"] + public_certificate["offline_cpu_seconds"] + snapshot["cpu_seconds"]
    for report in (baseline, previous_context, fresh, smoke):
        accounted += report["runtime"]["candidate_cpu_seconds_total"] + report["runtime"]["trusted_parent_cpu_seconds"]
    accounted += audit_cpu + time.process_time() - started + 20
    assert accounted < 1800
    status = json.loads((PACKAGE / "status.json").read_text())
    status.update(status="ready_for_parent_review", active=False,
                  sealed_at=datetime.now(timezone.utc).isoformat(),
                  difficulty_status="provisional_final_ratchet_candidate",
                  baseline=summary(baseline), previous_actual_fresh=summary(fresh),
                  previous_actual_fresh_submission="champions/generation_3/frozen_submission",
                  public_code_sha256=public_code, quality_attainability="independently_certified_nonzero_branches",
                  joint_speed_quality_attainability="not_established_for_generation_3; extended controls and offline references are not same-budget witnesses",
                  validation={"numerical_and_security_tests_passed": count, "continuum_audit_checks_passed": evidence["checks_passed"],
                              "maximum_reference_residual": max_residual, "maximum_cross_start_branch_error": max_cross_start,
                              "active_generation_2_sealed_files_unchanged": len(protocol["active_sealed_files"]),
                              "generation_2_archive_smoke_passed": True},
                  authoring_resource_accounting={"conservative_additional_cpu_seconds": accounted,
                                                  "additional_cpu_budget_seconds": 1800,
                                                  "initial_joint_pool_cpu_seconds": 520.8245850220001},
                  recommended_fresh_trial_wall_seconds=3600,
                  prelaunch_seal="evaluator/hidden/prelaunch_seal.json")
    write_json(PACKAGE / "status.json", status)
    evidence_summary = {"generation": 3, "active": False, "selection": selection, "baseline": summary(baseline),
                        "actual_v4": summary(fresh), "actual_v4_source_sha256": digest(ROOT / "champions/generation_3/solve.py"),
                        "actual_v4_joint_pool": json.loads((SIDECAR / "actual_v4_joint/evaluation.json").read_text()),
                        "continuum_evidence": evidence, "validation": status["validation"],
                        "resource_accounting": status["authoring_resource_accounting"],
                        "public_example_nonzero_certificate": True, "joint_attainability": "unknown",
                        "no_active_assets_modified": True, "no_prior_fresh_code_public": True, "no_fresh_launch_performed": True}
    write_json(PENDING / "ratchet_evidence.json", evidence_summary)
    lines = ["# Final ratchet 3: ready for parent review", "", "Inactive package only. No new fresh agent was launched. The active generation-2 participant, evaluator and status are unchanged.", "",
             "## Fixed target", "", "Unchanged mode A: core >= 0.90 (18/20), worst family >= 0.75 (3/4 each), and worst-family improvement >= 0.25 over the original public baseline. Gap residual <= 2e-8, Z residual <= 2e-9, branch distance <= 0.002 with the same nonzero/sign guard. Each case gets 12 child CPU seconds, 2048 MiB, one process/thread and an 1800-second wall safety ceiling.", "",
             "## Scores and selection", "", "The unchanged public weak baseline scores core 0.40 / worst 0.00. Actual fresh v4 scores core 0.80 / worst 0.50, failing exactly the four selected cases at the CPU limit. The final replay uses its frozen submission directory only; no privileged archival report is mounted with the candidate.", "",
             "Replace case_06/07/16/17 with continuum_04/06/02/03. All other sixteen cases are byte-identical, including all four nearcritical branch-hard cases and the two representative 32768-frequency critical cases. Maximum patch and Matsubara dimensions stay 40 and 32768.", "",
             "## Physical and numerical evidence", "", "The four new instances use 96 distinct positive log-frequency quadrature nodes, smooth five-peak patch-pair spectra, fixed moderate integrated coupling, varying noncommuting anisotropy, and the original physical frequency window. They are synthetic finite-cutoff Eliashberg inputs, not ab initio material predictions. The sampled normalized kernels agree with 192-node quadrature within 4.78e-11 over 80 transfer-frequency probes; this is a quadrature audit, not an infinite-cutoff or continuum error theorem. No modes or patches are duplicated padding.", "",
             "| Hidden slot | Probe | P x N | Pairing eigenvalue | v4 algorithm with deadline lifted |", "| --- | --- | --- | --- | --- |"]
    for slot, probe in selection["replacements"].items():
        record = next(item for item in evidence["cases"] if item["case_id"] == probe)
        extended = record["deadline_lifted_control"]
        timing = f"{extended['execution']['cpu_seconds']:.3f} CPU s, quality passed" if extended["output_available"] else "90-CPU-s limit reached; no output"
        lines.append(f"| {slot} | {probe} | {record['patches']} x {record['n_freq']} | {record['normal_pairing_eigenvalue']:.6f} | {timing} |")
    lines += ["", f"Builder-owned full-grid Newton references converge from two independent amplitude starts. Independent uncombined signed convolutions and direct signed rows certify residuals <= {max_residual:.3g}; cross-start branch distance <= {max_cross_start:.3g}. The public 96-node / 4096-frequency example is a separate draw with its own private nonzero-branch certificate.", "",
              "The extended control imports the byte-identical actual v4 code only inside the sandbox and lifts only its internal deadline. It does not demonstrate 12-second attainability. The joint large/nearcritical pool was not selected: actual v4 passed all four in at most 2.475 CPU seconds. This ratchet therefore targets a genuine resolved-spectrum computational cost gap, not a smaller critical margin or a polynomial-degree trap.", "",
              "## Audits and privacy", "", f"{count}/{count} numerical/security tests and {evidence['checks_passed']}/{evidence['checks_passed']} continuum checks pass. Evaluator, field checker, sandbox runner, public operator, baseline and workspace source hashes are unchanged. The first test invocation used the host's symlinked /home TMPDIR and correctly triggered the source-path protection; rerunning with canonical /srv TMPDIR fixes only launcher plumbing, with no weakened security check.", "",
              "Previous fresh code remains private in champions/generation_3 and adversary. The participant package adds only scope documentation and one public input NPZ. No private eigenmodes, branch arrays, sheet labels or generator seeds are exposed.", "",
              "## Artifacts and runtime", "", "- Pending task: package/concept_1; sibling package/authoring/sandbox_runner.py.", "- Seal: package/concept_1/evaluator/hidden/prelaunch_seal.json, with files mapping for the parent activator.", "- Full scores: package/concept_1/attempts/baseline_report.json and previous_fresh_report.json.", "- Evidence: ratchet_evidence.json; original pool, continuum generation, certificates and timing controls remain runnable in ../prospective_generation3.", "- Generation-2 archive: generation_2_runnable_snapshot.tar.gz plus generation_2_snapshot_manifest.json; exact shared runner included at its expected sibling path, archived evaluator smoke passed.", "",
              f"Conservative additional authoring accounting is {accounted:.1f} CPU seconds against the 1800-second continuum budget, separate from the original 520.8-CPU-second joint pool. Recommend the parent's 3600-second fresh trial, retaining the fixed 12-CPU-second / 2-GiB / one-thread candidate gate and generous wall ceiling. Joint generation-3 speed/quality attainability remains unknown; difficulty is provisional until the final allowed fresh trial."]
    write_text(PENDING / "REVIEW.md", "\n".join(lines) + "\n")
    files = {str(path.relative_to(PACKAGE)): digest(path) for path in sorted(PACKAGE.rglob("*"))
             if path.is_file() and "__pycache__" not in path.parts and path.name != "prelaunch_seal.json"}
    files["../authoring/sandbox_runner.py"] = digest(PACKAGE.parent / "authoring/sandbox_runner.py")
    seal = {"generation": 3, "ratchet_index": 3, "sealed_at": datetime.now(timezone.utc).isoformat(),
            "ready_for_parent_review": True, "active": False, "fixed_before_next_fresh_launch": True,
            "policy_sha256": digest(hidden / "policy.json"), "files": files,
            "target": selection["target_fixed_before_next_fresh_launch"], "baseline": summary(baseline),
            "previous_actual_fresh": summary(fresh), "audit_tests_passed": count,
            "active_generation_2_unchanged": True, "prior_fresh_code_public": False,
            "joint_resource_quality_attainability": "unknown", "new_fresh_launch_performed": False}
    write_json(hidden / "prelaunch_seal.json", seal)
    assert all(digest(PACKAGE / relative) == expected for relative, expected in files.items())
    print(json.dumps({"ready": True, "active": False, "sealed_files": len(files), "tests_passed": count,
                      "baseline_core_worst": [baseline["core_score"], baseline["worst_family_score"]],
                      "actual_v4_core_worst": [fresh["core_score"], fresh["worst_family_score"]],
                      "policy_sha256": digest(hidden / "policy.json"), "active_files_unchanged": len(protocol["active_sealed_files"]),
                      "conservative_additional_cpu_seconds": accounted}))


if __name__ == "__main__":
    main()
