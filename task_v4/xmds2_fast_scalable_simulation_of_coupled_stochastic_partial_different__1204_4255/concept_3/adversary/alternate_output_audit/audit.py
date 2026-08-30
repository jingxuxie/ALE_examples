import argparse
import hashlib
import json
import stat
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TRUSTED = ROOT / "evaluator/hidden"
sys.path.insert(0, str(TRUSTED))
import field_control as fc


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(name, value):
    destination = HERE / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def inventory():
    protocol = fc.read_json(TRUSTED / "protocol.json")
    result = {"created_utc": datetime.now(timezone.utc).isoformat(), "scope": "original_completed_generation_2_outputs_only", "new_optimization": False, "coefficient_postprocessing": False, "generation_3_built": False, "attempts": {}, "files": [], "distinct_controls": []}
    groups = {}
    for tag in ("v_3", "v_4"):
        run_path = ROOT / "attempts" / (tag + ".run.json")
        run = fc.read_json(run_path, 4 * 1024 * 1024)
        if run.get("status") in (None, "running"):
            raise RuntimeError("Attempt not completed: " + tag)
        result["attempts"][tag] = {"status_before_read": run["status"], "generation": run["generation"], "finished_at": run["finished_at"], "run_record_sha256": digest(run_path), "recorded_file_count": len(run["submission_sha256"])}
        for relative, expected in sorted(run["submission_sha256"].items()):
            source = ROOT / "attempts" / tag / relative
            item = {"attempt": tag, "source": str(source.relative_to(ROOT)), "recorded_sha256": expected, "eligible": False}
            result["files"].append(item)
            if not source.is_file() or source.is_symlink():
                item["reason"] = "missing_or_nonregular"
                continue
            payload = source.read_bytes()
            actual = hashlib.sha256(payload).hexdigest()
            item.update({"actual_sha256": actual, "snapshot_matches": actual == expected, "bytes": len(payload)})
            if actual != expected:
                item["reason"] = "cutoff_hash_mismatch"
                continue
            if len(payload) > protocol["artifact_max_bytes"]:
                item["reason"] = "exceeds_artifact_size_limit"
                continue
            if payload.lstrip()[:1] not in (b"{", b"["):
                item["reason"] = "not_json_document"
                continue
            try:
                artifact = fc.read_json(source, protocol["artifact_max_bytes"])
            except Exception as error:
                item["reason"] = "json_rejected: " + str(error)
                continue
            if not isinstance(artifact, dict) or set(artifact) != {"schema_version", "controls"}:
                item["reason"] = "not_exact_artifact_schema"
                continue
            item["exact_top_level_schema"] = True
            try:
                splines, certificate = fc.validate_artifact(artifact, protocol)
            except Exception as error:
                item["reason"] = "hardware_or_schema_rejected: " + str(error)
                continue
            canonical = hashlib.sha256(json.dumps(artifact, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
            identity = tag + "__" + relative.replace("/", "__")
            target = HERE / "artifacts" / identity
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            item.update({"eligible": True, "reason": "exact_original_valid_control", "canonical_sha256": canonical, "copy": str(target.relative_to(HERE)), "control_diagnostics": certificate})
            if canonical not in groups:
                groups[canonical] = {"id": identity, "canonical_sha256": canonical, "copy": str(target.relative_to(HERE)), "sources": [], "is_canonical_submission": False}
            groups[canonical]["sources"].append({"path": item["source"], "sha256": actual, "attempt": tag, "snapshot_matches": True})
            groups[canonical]["is_canonical_submission"] |= relative == "control.json"
    result["distinct_controls"] = list(groups.values())
    result["counts"] = {"recorded_files": len(result["files"]), "snapshot_mismatches": sum(item.get("snapshot_matches") is False for item in result["files"]), "exact_schema_files": sum(item.get("exact_top_level_schema", False) for item in result["files"]), "valid_control_files": sum(item["eligible"] for item in result["files"]), "distinct_valid_controls": len(groups), "distinct_noncanonical_controls": sum(not item["is_canonical_submission"] for item in groups.values())}
    protected_names = ("evaluator/evaluate.py", "evaluator/hidden/field_control.py", "evaluator/hidden/protocol.json", "evaluator/hidden/cases.json", "participant/input/protocol.json")
    result["protected_sha256"] = {name: digest(ROOT / name) for name in protected_names}
    dump("inventory.json", result)
    print("INVENTORY", json.dumps(result["counts"]), flush=True)
    for item in result["distinct_controls"]:
        print("CANDIDATE", item["id"], [source["path"] for source in item["sources"]], flush=True)
    return result


def rank_key(row):
    return min(row["core_score"] - 0.990, row["worst_family_score"] - 0.985, row["worst_case_score"] - 0.980)


def screen(records):
    started = time.perf_counter()
    protocol = fc.read_json(TRUSTED / "protocol.json")
    cases = fc.read_json(TRUSTED / "cases.json")
    assert len(cases) == 37
    shape = (64, 32)
    key = fc.reference_key(cases, shape)
    prior = ROOT / "adversary/gen2_proof_search"
    reference_paths = sorted(prior.rglob(key + ".npz"))
    if reference_paths:
        reference_path = reference_paths[0]
        with np.load(reference_path, allow_pickle=False) as data:
            initial, target, residual = data["initial"].copy(), data["target"].copy(), float(data["residual"])
    else:
        initial, target, residual = fc.references(cases, shape, HERE / "reference_cache")
        reference_path = HERE / "reference_cache" / (key + ".npz")
    assert residual <= protocol["audit"]["max_reference_residual"]
    freeze = {"case_count": len(cases), "case_sha256": digest(TRUSTED / "cases.json"), "grid": list(shape), "dt": 0.02, "reference_source": str(reference_path.relative_to(ROOT)), "reference_sha256": digest(reference_path), "reference_residual": residual, "protected_sha256": records["protected_sha256"], "note": "Surrogate only. Scores do not certify a pass or a numerical failure."}
    dump("screen_inputs.json", freeze)
    rows = []
    for candidate in records["distinct_controls"]:
        control_started = time.perf_counter()
        artifact = fc.read_json(HERE / candidate["copy"])
        splines, certificate = fc.validate_artifact(artifact, protocol)
        final_state, diagnostics = fc.evolve(splines, cases, shape, 0.02, initial)
        values = fc.fidelities(final_state, target, shape)
        if not np.all(np.isfinite(values)):
            raise ArithmeticError("Nonfinite surrogate score")
        scores = fc.summarize(values, cases, protocol)
        scores["surrogate_thresholds_met"] = scores.pop("passed")
        row = {**candidate, **scores, "valid": True, "passed": False, "reason": "surrogate_only_not_official", "runtime_seconds": time.perf_counter() - control_started, "runtime_score": 0.0, "resource_score": fc.resource_score(splines, protocol), "maximum_diagnostics": {name: float(np.max(value)) for name, value in diagnostics.items()}, "cases": [{"id": case["id"], "family": case["family"], "fidelity": float(value)} for case, value in zip(cases, values)]}
        rows.append(row)
        dump("screens/" + candidate["id"], row)
        report = {"status": "running", "screened": len(rows), "total": len(records["distinct_controls"]), "elapsed_seconds": time.perf_counter() - started, "inputs": freeze, "ranking": sorted(rows, key=rank_key, reverse=True)}
        dump("screening.json", report)
        print("SCREEN", candidate["id"], scores["core_score"], scores["worst_family_score"], scores["worst_case_score"], "seconds", row["runtime_seconds"], flush=True)
    for name, expected in records["protected_sha256"].items():
        assert digest(ROOT / name) == expected
    report["status"] = "complete"
    report["protected_inputs_unchanged"] = True
    dump("screening.json", report)
    print("SCREENING_COMPLETE", len(rows), "seconds", report["elapsed_seconds"], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory-only", action="store_true")
    arguments = parser.parse_args()
    records = inventory()
    if not arguments.inventory_only:
        screen(records)


if __name__ == "__main__":
    main()
