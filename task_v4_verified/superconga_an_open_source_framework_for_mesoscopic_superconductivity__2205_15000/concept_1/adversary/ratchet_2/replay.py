from common import ROOT, CONCEPT, digest, load_corpus, now, read_json, relative, verify_files, write_json

import argparse
from collections import Counter
import os
from pathlib import Path
import shutil

import numpy as np

from checking import aggregate, checked_field, diagnose, energy_gradient, invalid_case, score_field
from runner import campaign_budget, run_case


def result_gate(exit_path, evaluation_path, notified, policy):
    if not notified:
        return {"status": "awaiting_main_notification", "reason": "no automatic result polling or source inspection"}
    if not exit_path.is_file():
        return {"status": "awaiting_main_notification", "reason": "exit marker absent; source and evaluation not inspected"}
    if not evaluation_path.is_file():
        return {"status": "awaiting_main_notification", "reason": "evaluation not available; source not inspected"}
    exit_record = read_json(exit_path)
    evaluation = read_json(evaluation_path)
    if evaluation.get("passed") is False:
        return {"status": "not_needed", "reason": "A2 fresh evaluation failed; hard task retained; no sidecar search", "exit_record": exit_record, "evaluation": evaluation}
    if evaluation.get("passed") is not True or evaluation.get("valid") is not True:
        return {"status": "awaiting_main_notification", "reason": "evaluation lacks explicit valid passing result; source not inspected"}
    if evaluation.get("core_score", -1) < policy["core_min"] or evaluation.get("worst_family_score", -1) < policy["worst_family_min"]:
        raise ValueError("passing flag conflicts with frozen A2 thresholds")
    return {"status": "passed", "exit_record": exit_record, "evaluation": evaluation}


def validate_source_root(source):
    expected = CONCEPT / "attempts/v_2"
    resolved = source.resolve()
    for ancestor in (resolved, *resolved.parents):
        if ancestor.exists() and expected.exists() and os.path.samefile(ancestor, expected):
            return resolved
    raise ValueError("submission must be the finished v_2 artifact directory or its descendant")


def capture_source(source, gate):
    if gate["status"] != "passed":
        raise ValueError("source capture requires a completed passing evaluation")
    manifest_path = ROOT / "source_manifest.json"
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        verify_files(manifest["sha256"])
        return manifest
    if source is None:
        raise ValueError("pass --submission with the finished artifact directory")
    source = validate_source_root(source)
    paths = []
    total = 0
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError("artifact contains a symlink; requires explicit Main review")
        if path.is_file() and "__pycache__" not in path.parts and ".git" not in path.parts:
            paths.append(path)
            total += path.stat().st_size
    if not (source / "solve.py").is_file() or len(paths) > 128 or total > 32 * 1024**2:
        raise ValueError("choose the actual bounded submission root, not an attempt/archive container")
    original_hashes = {str(path.relative_to(source)): digest(path) for path in paths}
    for path in paths:
        destination = ROOT / "submission" / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        if digest(path) != original_hashes[str(path.relative_to(source))] or digest(destination) != digest(path):
            raise ValueError("source changed during capture despite exit marker")
    write_json(ROOT / "provenance/v2_exit.json", gate["exit_record"])
    write_json(ROOT / "provenance/v2_evaluation.json", gate["evaluation"])
    files = {"submission/" + name: expected for name, expected in original_hashes.items()}
    for name in ("provenance/v2_exit.json", "provenance/v2_evaluation.json"):
        files[name] = digest(ROOT / name)
    manifest = {"captured_at": now(), "original_submission": str(source), "unmodified_algorithm": True, "file_count": len(paths), "total_bytes": total, "sha256": files, "inspection_gate": "Main notified; exit marker present; watcher evaluation explicitly valid and passed"}
    write_json(manifest_path, manifest)
    return manifest


def diagnose_run(reference, record, case_path, stage, policy):
    if not record["valid"]:
        return {"substantive": False, "reason": record["reason"], "infrastructure_or_contract_invalid": True}
    destination = ROOT / "diagnostics" / stage / (reference["case_id"] + ".json")
    if destination.exists():
        return read_json(destination)
    case = read_json(case_path)
    field = checked_field(ROOT / record["field_path"], case, policy["result_max_bytes"])
    diagnostic = diagnose(reference, case, field, policy)
    diagnostic["record_path"] = "runs/" + record["stage"] + "/" + reference["case_id"] + "/record.json"
    write_json(destination, diagnostic)
    return diagnostic


def freeze_initial(reference, field_path, case_path, directory, baseline_source):
    destination = ROOT / directory / reference["case_id"]
    manifest_path = destination / "reference.json"
    if manifest_path.exists():
        frozen = read_json(manifest_path)
        verify_files(frozen["sha256"])
        return frozen
    case = read_json(case_path)
    field = checked_field(field_path, case)
    energy, unused, rms = energy_gradient(case, field)
    case["initial_real"] = field.real.tolist()
    case["initial_imag"] = field.imag.tolist()
    destination.mkdir(parents=True, exist_ok=True)
    write_json(destination / "case.json", case)
    shutil.copyfile(field_path, destination / "baseline.npz")
    result = dict(reference)
    result.update({"case_path": relative(destination / "case.json"), "baseline_path": relative(destination / "baseline.npz"), "baseline_energy": energy, "baseline_gradient_rms": rms, "reference_gap": energy - reference["witness_energy"], "baseline_source": baseline_source, "frozen_at": now()})
    result["sha256"] = {relative(destination / name): digest(destination / name) for name in ("case.json", "baseline.npz")}
    write_json(manifest_path, result)
    return result


def classify_controls(reference, attempts, policy):
    for attempt in attempts:
        if not attempt.get("valid"):
            continue
        if attempt["case_score"] > policy["stable_repeat_closure_max"] or attempt["remaining_gap"] < policy["minimum_remaining_gap"]:
            return "warm_replay_closes_gap", [attempt]
        if not attempt["diagnostic"]["substantive"] and not attempt["diagnostic"].get("control_inconclusive", False):
            return "not_a_stable_topological_gap", [attempt]
    accepted = [attempt for attempt in attempts if attempt.get("valid") and attempt.get("low_load_validated")]
    if len(accepted) < policy["required_frozen_warm_repeats"]:
        return "resource_inconclusive", accepted
    for attempt in accepted:
        if attempt["diagnostic"].get("control_inconclusive", False):
            return "resource_inconclusive", accepted
    return "stable_meaningful_gap", accepted


def controls(reference, broad, policy, source_manifest):
    name = reference["case_id"]
    warm = freeze_initial(reference, ROOT / broad["field_path"], ROOT / reference["case_path"], "warm_discovery_inputs", broad["field_path"])
    discovery = run_case(warm, ROOT / warm["case_path"], "warm_discovery", policy, source_manifest)
    if not discovery["valid"]:
        return {"case_id": name, "status": "resource_inconclusive", "reason": "warm discovery invalid or unavailable", "discovery": discovery}
    best = min((broad, discovery), key=lambda record: record["checked_energy"])
    frozen = freeze_initial(reference, ROOT / best["field_path"], ROOT / reference["case_path"], "frozen_warm_inputs", best["field_path"])
    diagnostic = diagnose_run(frozen, best, ROOT / frozen["case_path"], "frozen_baseline", policy)
    if not diagnostic["substantive"]:
        return {"case_id": name, "status": "resource_inconclusive" if diagnostic.get("control_inconclusive", False) else "warm_discovery_closes_gap", "baseline": frozen, "diagnostic": diagnostic}
    attempts = []
    for attempt in range(1, policy["maximum_repeat_attempts_per_case"] + 1):
        stage = "frozen_repeat_" + str(attempt)
        raw = run_case(frozen, ROOT / frozen["case_path"], stage, policy, source_manifest, require_quiet=True)
        result = dict(raw)
        if raw["valid"]:
            case = read_json(ROOT / frozen["case_path"])
            field = checked_field(ROOT / raw["field_path"], case)
            result.update(score_field(frozen, case, field, raw["resource_accounting"]["wall_seconds"], policy))
            result["diagnostic"] = diagnose_run(frozen, raw, ROOT / frozen["case_path"], stage, policy)
        attempts.append(result)
        classification, accepted = classify_controls(frozen, attempts, policy)
        if classification != "resource_inconclusive":
            break
        if not campaign_budget(policy):
            break
    classification, accepted = classify_controls(frozen, attempts, policy)
    return {"case_id": name, "family": frozen["family"], "status": classification, "baseline": frozen, "baseline_diagnostic": diagnostic, "attempts": attempts, "accepted_low_load_repeats": accepted}


def propose(stable, policy):
    destination = ROOT / "proposal"
    if (destination / "manifest.json").exists():
        manifest = read_json(destination / "manifest.json")
        verify_files(manifest["sha256"])
        return manifest
    references = [entry["baseline"] for entry in stable]
    target = {key: policy[key] for key in ("verification_mode", "minimum_reference_gap", "core_min", "worst_family_min", "regression_relative_tolerance", "stationarity_rms_max", "wall_seconds_per_case", "cpu_seconds_per_case", "cpu_cores", "memory_mib", "scratch_mib", "result_max_bytes")}
    counts = dict(Counter(reference["family"] for reference in references))
    target.update({"frozen_at": now(), "generation": 3, "case_count": len(references), "families": sorted(counts), "family_cardinality": counts, "reference_kind": "preexisting attained witness, not true ground state", "allow_regression": False, "approval_required": True})
    repeat_scores = []
    for index in range(policy["required_frozen_warm_repeats"]):
        repeat_scores.append(aggregate([entry["accepted_low_load_repeats"][index] for entry in stable], target))
    if any(report["passed"] or not report["valid"] for report in repeat_scores):
        raise ValueError("proposed champion controls do not establish a quality-only failure")
    destination.mkdir(exist_ok=True)
    write_json(destination / "target.json", target)
    fields = [destination / "target.json"]
    for reference in references:
        fields.extend(ROOT / reference[key] for key in ("case_path", "baseline_path", "witness_path"))
    manifest = {"schema_version": 1, "status": "proposed_solvability_unknown", "approval_required": True, "installed": False, "cases": references, "champion_repeat_scores": repeat_scores, "unchanged_source_manifest_sha256": digest(ROOT / "source_manifest.json"), "source_pool_manifest_sha256": digest(ROOT / "corpus/manifest.json"), "witnesses_preexist_v2_inspection": True, "no_new_solver_qualification_claim": True, "sha256": {relative(path): digest(path) for path in fields}, "fresh_sessions_launched": 0}
    write_json(destination / "manifest.json", manifest)
    return manifest


def finish(status, manifest, broad, control_results, proposal=None, reason=None):
    report = {"at": now(), "status": status, "reason": reason, "physical_cases_preserved": manifest["physical_case_count"], "selected_replay_count": manifest["selected_replay_count"], "solver_processes_launched": len(list((ROOT / "runs").glob("*/*/launch.json"))), "source_pool_manifest_sha256": digest(ROOT / "corpus/manifest.json"), "broad_results": broad, "controls": control_results, "stable_meaningful_cases": [entry["case_id"] for entry in control_results if entry["status"] == "stable_meaningful_gap"], "proposal": "proposal/manifest.json" if proposal else None, "fresh_sessions_launched": 0, "live_assets_modified": False, "witness_policy": "preexisting physical fields only; no true-ground-state or unmeasured executable-achievability claim"}
    if len(broad) == manifest["selected_replay_count"]:
        diagnostic_target = read_json(ROOT / "policy.json")
        diagnostic_target.update({"case_count": manifest["selected_replay_count"], "families": sorted(manifest["selected_family_counts"]), "family_cardinality": manifest["selected_family_counts"]})
        report["diagnostic_broad_score"] = aggregate([entry["score"] for entry in broad], diagnostic_target)
        report["diagnostic_broad_score_note"] = "Diagnostic closure from preserved generation-1 supplied starts; not a newly installed scoring task or a generation-3 target."
    if (ROOT / "provenance/v2_evaluation.json").exists():
        report["v2_evaluation_provenance"] = {"path": "provenance/v2_evaluation.json", "sha256": digest(ROOT / "provenance/v2_evaluation.json")}
    write_json(ROOT / "report.json", report)
    write_json(ROOT / "status.json", {key: value for key, value in report.items() if key not in ("broad_results", "controls")})
    lines = ["# A2 bounded broad replay", "", "Status: **" + status + "**.", "", "Preserved physical cases: " + str(manifest["physical_case_count"]) + "; preselected meaningful-gap cases: " + str(manifest["selected_replay_count"]) + ".", "Solver launches: " + str(report["solver_processes_launched"]) + "; maximum concurrency one; no fresh agents or live edits.", "", "All case energies, gradients, resource/load audits, fields, and source hashes are retained under this sidecar.", "Preexisting witnesses are not global minima or proofs that a new resource-bounded solver exists."]
    if reason:
        lines.extend(["", "Reason: " + reason])
    if proposal:
        lines.extend(["", "Private generation-3 proposal: `proposal/manifest.json`; target 0.65 core / 0.45 worst family, with exact actual-champion fields supplied as starts. Status remains `proposed_solvability_unknown`; Main approval is required. Nothing is installed."])
    lines.extend(["", "## Broad outcomes", "", "| Case | Valid | Remaining gap | Diagnosis |", "| --- | --- | ---: | --- |"])
    for entry in broad:
        record = entry["record"]
        lines.append("| " + record["case_id"] + " | " + str(record["valid"]) + " | " + str(record.get("remaining_gap", "n/a")) + " | " + entry["diagnostic"]["reason"] + " |")
    if control_results:
        lines.extend(["", "## Controls", ""])
        lines.extend("- " + entry["case_id"] + ": " + entry["status"] for entry in control_results)
    (ROOT / "REPORT.md").write_text("\n".join(lines) + "\n")
    print({key: value for key, value in report.items() if key not in ("broad_results", "controls")}, flush=True)


def main():
    parser = argparse.ArgumentParser(description="Manually gated, bounded private A2 replay; never watches or launches fresh agents")
    parser.add_argument("--main-notified", action="store_true")
    parser.add_argument("--submission", type=Path)
    args = parser.parse_args()
    manifest, policy = load_corpus()
    if (ROOT / "harness_manifest.json").exists():
        verify_files(read_json(ROOT / "harness_manifest.json")["sha256"])
    gate = result_gate(CONCEPT / "attempts/v_2.exit.json", CONCEPT / "attempts/v_2.evaluation.json", args.main_notified, policy)
    if gate["status"] != "passed":
        if gate["status"] == "not_needed":
            write_json(ROOT / "provenance/v2_exit.json", gate["exit_record"])
            write_json(ROOT / "provenance/v2_evaluation.json", gate["evaluation"])
        finish(gate["status"], manifest, [], [], reason=gate["reason"])
        return
    source_manifest = capture_source(args.submission, gate)
    selected = {reference["case_id"]: reference for reference in manifest["cases"]}
    broad = []
    for name in manifest["replay_order"]:
        reference = selected[name]
        record = run_case(reference, ROOT / reference["case_path"], "broad", policy, source_manifest)
        diagnostic = diagnose_run(reference, record, ROOT / reference["case_path"], "broad", policy)
        if record["valid"]:
            case = read_json(ROOT / reference["case_path"])
            field = checked_field(ROOT / record["field_path"], case)
            score = score_field(reference, case, field, record["resource_accounting"]["wall_seconds"], policy)
        else:
            score = invalid_case(reference, record["reason"], record.get("resource_accounting", {}).get("wall_seconds", 0))
        broad.append({"record": record, "diagnostic": diagnostic, "score": score})
        write_json(ROOT / "broad_progress.json", {"results": broad, "source_manifest_sha256": digest(ROOT / "source_manifest.json")})
        if record["status"] == "budget_exhausted":
            break
    candidates = sorted((entry for entry in broad if entry["record"]["valid"] and entry["diagnostic"]["substantive"]), key=lambda entry: (-entry["record"]["remaining_gap"], entry["record"]["case_id"]))
    control_results = []
    for entry in candidates[:policy["maximum_control_cases"]]:
        name = entry["record"]["case_id"]
        result = controls(selected[name], entry["record"], policy, source_manifest)
        control_results.append(result)
        write_json(ROOT / "controls" / (name + ".json"), result)
    stable = [entry for entry in control_results if entry["status"] == "stable_meaningful_gap"]
    if stable:
        proposal = propose(stable, policy)
        finish("proposed_solvability_unknown", manifest, broad, control_results, proposal)
    elif any(entry["status"] == "resource_inconclusive" for entry in control_results) or any(not entry["record"]["valid"] or entry["diagnostic"].get("control_inconclusive", False) for entry in broad) or len(broad) != manifest["selected_replay_count"] or len(candidates) > policy["maximum_control_cases"]:
        finish("resource_inconclusive", manifest, broad, control_results, reason="bounded controls or infrastructure do not justify either a hard-gap or robust-solution claim; no proposal installed")
    else:
        finish("no_meaningful_ratchet", manifest, broad, control_results, reason="all preselected physical gaps close, lack reliable topological separation, or collapse under valid warm/polish controls; stop without manufacturing targets")


if __name__ == "__main__":
    main()
