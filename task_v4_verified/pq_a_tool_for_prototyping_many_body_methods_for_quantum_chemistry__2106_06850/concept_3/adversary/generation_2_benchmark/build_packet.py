"""Stage and verify generation two without modifying the active generation-one packet."""

import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
CONCEPT = ROOT.parents[1]
PACKET = ROOT.parent / "generation_2_packet"
POOL = ROOT.parent / "candidate_pool"
SNAPSHOT = ROOT.parent / "generation_1_snapshot" / "participant"


def save_files(files, replace=False):
    patch = "*** Begin Patch\n"
    for relative, data in files.items():
        path = PACKET / relative
        if not path.resolve().is_relative_to(PACKET):
            raise ValueError("write would leave generation_2_packet")
        contents = data if isinstance(data, str) else json.dumps(data, indent=2, allow_nan=False) + "\n"
        if path.exists():
            if not replace:
                raise RuntimeError("refusing to replace staged file: " + relative)
            old = path.read_text()
            patch += "*** Update File: " + str(path) + "\n@@\n" + "".join("-" + line + "\n" for line in old.splitlines())
        else:
            patch += "*** Add File: " + str(path) + "\n"
        patch += "".join("+" + line + "\n" for line in contents.splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True, capture_output=True)


def run_report(command, output):
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    process = subprocess.run(command, cwd=PACKET, env=environment, capture_output=True, text=True, timeout=90)
    if process.returncode not in (0, 1):
        raise RuntimeError(process.stderr + process.stdout)
    report = json.loads(process.stdout)
    save_files({output: report})
    return report


def main():
    if (PACKET / "participant").exists():
        raise RuntimeError("a participant staging tree already exists; refusing to mutate a possibly frozen packet")
    benchmark = json.loads((ROOT / "benchmark_report.json").read_text())
    assert benchmark["status"] == "bounded_benchmark_complete"
    selected_ids = benchmark["selected_case_ids"]
    pool_targets = {case["case_id"]: case for case in json.loads((POOL / "targets.json").read_text())["cases"]}
    pool_certificates = {circuit["case_id"]: circuit for circuit in json.loads((POOL / "certificates.json").read_text())["circuits"]}
    pool_metadata = {case["case_id"]: case for case in json.loads((POOL / "metadata.json").read_text())["cases"]}
    deep_by_id = {entry["case_id"]: entry for entry in benchmark["deep"]}
    targets, certificates, champion_circuits, selection_cases = [], [], [], []
    for identifier in selected_ids:
        probe = deep_by_id[identifier]
        assert probe["healthy"] and not probe["score"]["pass"] and probe["certificate_free_namespace"]
        target = copy.deepcopy(pool_targets[identifier])
        public_id = "sector_10_%d_d%d" % (target["n_electrons"], target["max_gates"])
        target["case_id"] = public_id
        certificate = copy.deepcopy(pool_certificates[identifier])
        certificate["case_id"] = public_id
        candidate = json.loads((ROOT / probe["work_path"] / "result.json").read_text())["circuits"][0]
        candidate["case_id"] = public_id
        targets.append(target)
        certificates.append(certificate)
        champion_circuits.append(candidate)
        diagnostics = copy.deepcopy(pool_metadata[identifier])
        diagnostics.pop("private_seed", None)
        selection_cases.append({
            "public_case_id": public_id, "private_pool_case_id": identifier,
            "n_orbitals": target["n_orbitals"], "n_electrons": target["n_electrons"], "gate_cap": target["max_gates"],
            "pool_target_sha256": hashlib.sha256((POOL / "cases" / identifier / "targets.json").read_bytes()).hexdigest(),
            "pool_certificate_sha256": hashlib.sha256((POOL / "cases" / identifier / "certificate.json").read_bytes()).hexdigest(),
            "bounded_deep_best_fidelity": probe["score"]["core"],
            "beam_support_trace": probe["beam_support_trace"], "physical_prefix_diagnostics": diagnostics,
            "failure_family": "saturated physical support and full alpha/beta Schmidt rank before a long noncommuting opposite-spin-double suffix; bounded discrete/continuous portfolio did not recover a matching circuit",
        })
    assert {target["max_gates"] for target in targets} == {24, 28, 32}
    assert {target["n_electrons"] for target in targets} == {4, 6}
    target_document = {"schema_version": 1, "fidelity_threshold": 0.999999999, "cases": targets}
    certificate_document = {"schema_version": 1, "circuits": certificates}
    files = {}
    for name in ("baseline/run.py", "workspace/baseline.py", "workspace/check.py"):
        files["participant/" + name] = (SNAPSHOT / name).read_text()
    old_engine = (SNAPSHOT / "workspace/fermion.py").read_text()
    engine = old_engine.replace('integers["max_gates"] <= 20', 'integers["max_gates"] <= 32')
    assert engine != old_engine
    files["participant/workspace/fermion.py"] = engine
    files["evaluator/private/engine.py"] = engine
    files["participant/input/targets.json"] = target_document
    files["evaluator/private/targets.json"] = target_document
    files["evaluator/private/certificates.json"] = certificate_document
    files["evaluator/private/champion_probe_submission.json"] = {"schema_version": 1, "circuits": champion_circuits}
    files["evaluator/evaluate.py"] = (CONCEPT / "evaluator/evaluate.py").read_text()
    files["evaluator/private/judge.py"] = (CONCEPT / "evaluator/private/judge.py").read_text()
    files["evaluator/private/audit.py"] = (CONCEPT / "evaluator/private/audit.py").read_text()
    files["adversary/check_fail_closed.py"] = (CONCEPT / "adversary/check_fail_closed.py").read_text()
    mission = (SNAPSHOT / "TASK.md").read_text().replace("14, 18 and 20 gates", "24, 28 and 32 gates")
    mission = mission.replace("No particular planted circuit or globally shortest decomposition is", "No particular circuit or globally shortest decomposition is")
    files["participant/TASK.md"] = mission
    contract = (SNAPSHOT / "workspace/CONTRACT.md").read_text()
    old_rows = "| sector_8_4 | 8 | 4 (2, 2) | 14 |\n| sector_10_4 | 10 | 4 (2, 2) | 18 |\n| sector_10_6 | 10 | 6 (3, 3) | 20 |"
    new_rows = "\n".join("| %s | 10 | %d (%d, %d) | %d |" % (target["case_id"], target["n_electrons"], target["n_alpha"], target["n_beta"], target["max_gates"]) for target in targets)
    assert old_rows in contract
    contract = contract.replace(old_rows, new_rows)
    for old, target in zip(("sector_8_4", "sector_10_4", "sector_10_6"), targets):
        contract = contract.replace('"case_id":"' + old + '"', '"case_id":"' + target["case_id"] + '"')
    files["participant/workspace/CONTRACT.md"] = contract
    api = (SNAPSHOT / "workspace/API.md").read_text()
    api = api.replace("choices, 90 for 8 orbitals and 250 for 10, independent of initial occupation.", "choices, 250 for each supplied 10-orbital case, independent of initial occupation.")
    api = api.replace("vectors (70, 210, 210", "vectors (210, 210, 210")
    files["participant/workspace/API.md"] = api
    files["attempts/README.md"] = "# Private baseline evidence\n\nThe original public greedy baseline and its measured generation-two score are stored here.\n"
    files["champions/README.md"] = "# Private champions\n\nNo fresh generation-two attempt has been launched by this worker.\n"
    files["adversary/README.md"] = "# Private validation\n\nFail-closed checks only. Bounded completed-champion search evidence is under evaluator/private/.\n"
    files["evaluator/hidden/README.md"] = "# Hidden certificate index\n\nThe index references adjacent ../private/ witnesses, hashes, selection evidence and scores. Both directories are organizer-only.\n"
    files["README.md"] = (
        "# Generation-two staging packet — organizer only\n\n"
        "Expose only participant/. This staging packet does not modify the active generation-one packet. "
        "Main may promote it after review. No fresh agents were launched here.\n\n"
        "Mode C / WITNESS-DESIGN; all three fidelities must be at least 0.999999999; "
        "gate caps are 24/28/32. A fresh solving session receives one hour. The submission is "
        "data-only JSON capped at 131072 bytes. There is no claimed four-core or four-GiB runner limit.\n\n"
        "The baseline is unchanged greedy excitation selection plus limited angle refinement. "
        "The checker engine is unchanged except that its target loader permits caps through 32. "
        "All excitation algebra, determinant signs, spin constraints, norm checks, threshold, "
        "output schema and isolated evaluator behavior are unchanged.\n\n"
        "Private selection evidence records 60-second full-portfolio broad probes on 18 pool cases "
        "and three original controls, followed by additional 300-second probes on the three finalists. "
        "These are bounded failures, not a claim that the completed champion fails with a full hour. "
        "Only public inputs were visible inside explicit allowlist-only bubblewrap namespaces.\n\n"
        "Run `python participant/baseline/run.py --output attempts/baseline.json`; "
        "score with `python -I evaluator/evaluate.py --submission PATH`. "
        "`evaluator/hidden/certificate_index.json` locates all hidden feasibility evidence. "
        "`READY_FOR_MAIN` is written only after baseline, witness, independent dense and parser checks pass.\n"
    )
    selection = {"generation": 2, "verification_mode": "C", "selected_cases": selection_cases,
                 "selection_rule": "among healthy broad failures, minimize maximum best fidelity then summed best fidelity; require depths 24/28/32 and N=4/6 coverage; require every selected case still fails the deeper probe",
                 "scientific_interpretation": "support-cancellation search sees dense/full-rank suffixes rather than the planted zero-producing reverse path; continuous refinement and two-gate bridges also ran. This is an observed bounded search obstruction, not a hardness or minimality proof.",
                 "probe_budgets": {"broad_seconds_per_case": 60, "deep_additional_seconds_per_finalist": 300, "fresh_session_seconds": 3600},
                 "old_controls_passed": benchmark["control_pass_count"], "old_controls_tested": 3,
                 "full_hour_champion_failure_claimed": False, "participant_has_no_certificates_or_champion_code": True,
                 "source_engine_sha256": hashlib.sha256(old_engine.encode()).hexdigest(),
                 "engine_change": "target loader cap bound 20 -> 32 only", "active_generation_one_modified": False}
    files["evaluator/private/selection_manifest.json"] = selection
    files["evaluator/private/champion_search_results.json"] = benchmark
    save_files(files)
    participant_hashes = {str(path.relative_to(PACKET / "participant")): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in sorted((PACKET / "participant").rglob("*")) if path.is_file()}
    private_hashes = {name: hashlib.sha256((PACKET / "evaluator/private" / name).read_bytes()).hexdigest()
                      for name in ("engine.py", "targets.json", "certificates.json")}
    frozen = {"generation": 2, "frozen_at": datetime.now(timezone.utc).isoformat(), "fidelity_threshold": 0.999999999,
              "gate_caps": [24, 28, 32], "participant_sha256": participant_hashes, "private_sha256": private_hashes}
    hidden = {"schema_version": 1, "confidential": True, "verification_mode": "C", "certificates_path": "../private/certificates.json",
              "certificates_sha256": private_hashes["certificates.json"], "targets_path": "../private/targets.json",
              "selection_manifest": "../private/selection_manifest.json", "champion_search_results": "../private/champion_search_results.json",
              "frozen_manifest": "../private/frozen_manifest.json", "witness_score": "../private/witness_score.json", "independent_audit": "../private/audit.json"}
    save_files({"evaluator/private/frozen_manifest.json": frozen, "evaluator/hidden/certificate_index.json": hidden})
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    baseline_process = subprocess.run([sys.executable, "participant/baseline/run.py", "--output", "attempts/baseline.json"],
                                      cwd=PACKET, env=environment, capture_output=True, text=True, timeout=90, check=True)
    save_files({"attempts/baseline_runtime.json": json.loads(baseline_process.stdout)})
    baseline = run_report([sys.executable, "-I", "evaluator/evaluate.py", "--submission", "attempts/baseline.json"], "attempts/baseline_score.json")
    witness = run_report([sys.executable, "-I", "evaluator/evaluate.py", "--submission", "evaluator/private/certificates.json"], "evaluator/private/witness_score.json")
    champion = run_report([sys.executable, "-I", "evaluator/evaluate.py", "--submission", "evaluator/private/champion_probe_submission.json"], "evaluator/private/champion_probe_score.json")
    public = run_report([sys.executable, "participant/workspace/check.py", "--submission", "evaluator/private/certificates.json"], "evaluator/private/public_witness_score.json")
    subprocess.run([sys.executable, "evaluator/private/audit.py"], cwd=PACKET, env=environment, check=True, timeout=90)
    subprocess.run([sys.executable, "adversary/check_fail_closed.py"], cwd=PACKET, env=environment, check=True, timeout=90)
    audit = json.loads((PACKET / "evaluator/private/audit.json").read_text())
    adversary = json.loads((PACKET / "adversary/report.json").read_text())
    assert len(baseline["cases"]) == 3 and not baseline["pass"]
    assert witness["pass"] and public["pass"] and witness["core"] == public["core"]
    assert not champion["pass"] and all(not case["pass"] for case in champion["cases"])
    assert audit["pass"] and adversary["pass"]
    for relative, digest in participant_hashes.items():
        assert hashlib.sha256((PACKET / "participant" / relative).read_bytes()).hexdigest() == digest
    status = {"generation": 2, "verification_mode": "C", "status": "ready_for_main", "participant_frozen": True,
              "packet": str(PACKET), "selected_private_pool_ids": selected_ids, "public_case_ids": [case["case_id"] for case in targets],
              "gate_caps": [24, 28, 32], "fidelity_threshold": 0.999999999, "fresh_session_seconds": 3600,
              "submission_byte_cap": 131072, "baseline_core": baseline["core"], "baseline_pass": baseline["pass"],
              "certificate_core": witness["core"], "certificate_pass": witness["pass"], "bounded_champion_core": champion["core"],
              "bounded_champion_all_cases_fail": True, "independent_audit_pass": audit["pass"], "adversarial_tests_pass": adversary["pass"],
              "participant_hashes_verified": True, "old_control_pass_count": benchmark["control_pass_count"],
              "benchmark_budgets_seconds": {"broad_per_case": 60, "additional_deep_per_finalist": 300},
              "full_hour_champion_failure_claimed": False, "no_active_generation_one_changes": True,
              "freeze_manifest": "evaluator/private/frozen_manifest.json", "selection_manifest": "evaluator/private/selection_manifest.json"}
    save_files({"status.json": status, "READY_FOR_MAIN": status})
    print(json.dumps({"READY_FOR_MAIN": str(PACKET / "READY_FOR_MAIN"), "baseline_core": baseline["core"],
                      "certificate_core": witness["core"], "bounded_champion_core": champion["core"], "selected_pool_ids": selected_ids}), flush=True)


if __name__ == "__main__":
    main()
