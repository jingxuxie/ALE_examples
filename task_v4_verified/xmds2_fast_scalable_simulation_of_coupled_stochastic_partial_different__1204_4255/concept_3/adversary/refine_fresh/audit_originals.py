import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TRUSTED = ROOT / "evaluator/hidden"
sys.path.insert(0, str(TRUSTED))
from field_control import CHANNELS, evolve, fidelities, read_json, reference_key, references, summarize, validate_artifact


def write_report(report):
    (HERE / "original_audit.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


def hashes_in_record(value, pointer="$"):
    found = {}
    if isinstance(value, dict):
        children = value.items()
    elif isinstance(value, list):
        children = enumerate(value)
    else:
        if isinstance(value, str) and re.fullmatch("[0-9a-fA-F]{64}", value):
            found[value.lower()] = [pointer]
        return found
    for key, child in children:
        for digest, paths in hashes_in_record(child, pointer + "/" + str(key)).items():
            found.setdefault(digest, []).extend(paths)
    return found


def control_hash(artifact):
    values = np.asarray([artifact["controls"][channel] for channel in CHANNELS], dtype="<f8")
    return hashlib.sha256(values.tobytes()).hexdigest()


def main():
    started = time.perf_counter()
    protocol = read_json(TRUSTED / "protocol.json")
    cases = read_json(TRUSTED / "cases.json")
    report = {"role": "privileged_generation_only", "original_cutoff": "2026-08-28T04:20:04-07:00", "status": "inventory", "canonical_full_evaluations_excluded": ["attempts/v_1/control.json", "attempts/v_2/control.json"], "original_passing_artifact": None, "invalid_control_files": [], "ignored_empty_json": [], "candidates": [], "cutoff_record_sha256": {}, "frozen_sha256": {}}
    for relative in ("evaluator/evaluate.py", "evaluator/hidden/field_control.py", "evaluator/hidden/protocol.json", "evaluator/hidden/cases.json", "participant/input/protocol.json"):
        report["frozen_sha256"][relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    canonical_hashes = {control_hash(read_json(ROOT / relative)) for relative in report["canonical_full_evaluations_excluded"]}
    candidates = {}
    for run in ("v_1", "v_2"):
        record_path = ROOT / "attempts" / (run + ".run.json")
        record_payload = record_path.read_bytes()
        report["cutoff_record_sha256"][run] = hashlib.sha256(record_payload).hexdigest()
        recorded_hashes = hashes_in_record(json.loads(record_payload))
        for path in sorted((ROOT / "attempts" / run).rglob("*.json")):
            if path.is_symlink() or path.stat().st_size > protocol["artifact_max_bytes"]:
                continue
            relative = str(path.relative_to(ROOT))
            payload = path.read_bytes()
            if not payload:
                report["ignored_empty_json"].append(relative)
                continue
            try:
                artifact = read_json(path)
            except Exception:
                continue
            if not isinstance(artifact, dict) or "controls" not in artifact:
                continue
            digest = hashlib.sha256(payload).hexdigest()
            proof = {"path": relative, "sha256": digest, "run": run, "cutoff_hash_match": digest in recorded_hashes, "record_pointers": recorded_hashes.get(digest, [])}
            try:
                validate_artifact(artifact, protocol)
            except Exception as error:
                report["invalid_control_files"].append(dict(proof, reason=str(error)))
                continue
            value_hash = control_hash(artifact)
            if value_hash not in candidates:
                candidates[value_hash] = {"control_value_sha256": value_hash, "aliases": [], "excluded_canonical_equivalent": value_hash in canonical_hashes, "artifact": artifact}
            candidates[value_hash]["aliases"].append(proof)
    for entry in candidates.values():
        entry["original_hash_verified"] = any(alias["cutoff_hash_match"] for alias in entry["aliases"])
        entry["source"] = next((alias["path"] for alias in entry["aliases"] if alias["cutoff_hash_match"]), entry["aliases"][0]["path"])
        report["candidates"].append({key: value for key, value in entry.items() if key != "artifact"})
    write_report(report)
    initial, target, residual = references(cases, (64, 32), HERE / "reference_cache")
    report["surrogate"] = {"grid": [64, 32], "dt": 0.02, "reference_residual": residual, "case_count": len(cases)}
    report["status"] = "surrogate_ranking"
    for entry in report["candidates"]:
        if entry["excluded_canonical_equivalent"]:
            continue
        artifact = candidates[entry["control_value_sha256"]]["artifact"]
        splines, certificate = validate_artifact(artifact, protocol)
        state, diagnostic = evolve(splines, cases, (64, 32), 0.02, initial)
        scores = fidelities(state, target, (64, 32))
        summary = summarize(scores, cases, protocol)
        summary["potential_pass_without_audit"] = summary.pop("passed")
        entry["surrogate"] = dict(summary, worst_case_id=cases[int(np.argmin(scores))]["id"], worst_case_index=int(np.argmin(scores)), diagnostics={key: float(np.max(value)) for key, value in diagnostic.items()})
        write_report(report)
        print(json.dumps({"source": entry["source"], "original_hash_verified": entry["original_hash_verified"], "surrogate": entry["surrogate"]}), flush=True)
    fine_shape = tuple(protocol["audit"]["refined_grid"])
    for shape in (tuple(protocol["audit"]["spatial_grid"]), fine_shape):
        expected = TRUSTED / "references" / (reference_key(cases, shape) + ".npz")
        if not expected.is_file():
            raise RuntimeError("trusted reference cache missing; refusing any write outside refine_fresh: " + str(expected))
    fine_cache = TRUSTED / "references" / (reference_key(cases, fine_shape) + ".npz")
    with np.load(fine_cache, allow_pickle=False) as cache:
        initial_fine = cache["initial"].copy()
        target_fine = cache["target"].copy()
    ranked = sorted((entry for entry in report["candidates"] if "surrogate" in entry), key=lambda entry: (entry["surrogate"]["worst_case_score"], entry["surrogate"]["core_score"]), reverse=True)
    report["status"] = "refined_failure_checks"
    for entry in ranked:
        worst = entry["surrogate"]["worst_case_index"]
        artifact = candidates[entry["control_value_sha256"]]["artifact"]
        splines, certificate = validate_artifact(artifact, protocol)
        state, diagnostic = evolve(splines, cases[worst:worst + 1], fine_shape, protocol["audit"]["refined_dt"], initial_fine[worst:worst + 1])
        score = float(fidelities(state, target_fine[worst:worst + 1], fine_shape)[0])
        entry["refined_single_case"] = {"case_id": cases[worst]["id"], "grid": list(fine_shape), "dt": protocol["audit"]["refined_dt"], "raw_fidelity": score, "threshold": 0.98, "excludes_frozen_pass": score < 0.98 - 1e-8, "rationale": "Frozen audited Q is no larger than this same frozen-C-grid raw fidelity; a failing case suffices to exclude a pass.", "diagnostics": {key: float(np.max(value)) for key, value in diagnostic.items()}}
        write_report(report)
        print(json.dumps({"source": entry["source"], "refined_single_case": entry["refined_single_case"]}), flush=True)
        if entry["refined_single_case"]["excludes_frozen_pass"]:
            continue
        output = HERE / (entry["control_value_sha256"][:16] + ".original_evaluation.json")
        command = [sys.executable, "-I", "-B", str(ROOT / "evaluator/evaluate.py"), "--artifact", str(ROOT / entry["source"]), "--output", str(output)]
        process = subprocess.run(command, cwd=HERE, capture_output=True, text=True, timeout=600, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        (HERE / (entry["control_value_sha256"][:16] + ".original_evaluation.log")).write_text(process.stdout + process.stderr)
        result = json.loads(output.read_text())
        entry["full_frozen_evaluation"] = {"output": str(output.relative_to(ROOT)), "command": command, "returncode": process.returncode, "valid": result["valid"], "passed": result["passed"], "core_score": result["core_score"], "worst_family_score": result["worst_family_score"], "worst_case_score": result["worst_case_score"], "reason": result["reason"]}
        if result["passed"] and entry["original_hash_verified"]:
            report["original_passing_artifact"] = entry["source"]
            report["status"] = "original_passing_artifact_found"
            write_report(report)
            print("ORIGINAL_PASS " + json.dumps(entry), flush=True)
            return
        write_report(report)
    report["status"] = "all_other_valid_originals_checked_no_pass"
    report["runtime_seconds"] = time.perf_counter() - started
    report["unique_valid_control_count"] = len(report["candidates"])
    report["noncanonical_unique_control_count"] = len(ranked)
    report["all_source_hashes_verified"] = all(entry["original_hash_verified"] for entry in report["candidates"])
    for relative, digest in report["frozen_sha256"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != digest:
            raise RuntimeError("frozen input changed during audit: " + relative)
    write_report(report)
    print(json.dumps({key: value for key, value in report.items() if key not in ("candidates", "invalid_control_files")}), flush=True)


if __name__ == "__main__":
    main()
