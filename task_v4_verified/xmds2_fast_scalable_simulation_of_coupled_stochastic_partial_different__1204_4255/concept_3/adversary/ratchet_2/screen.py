import argparse
import hashlib
import json
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


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def acquire_completed(tag):
    path = ROOT / "attempts" / (tag + ".run.json")
    record = fc.read_json(path, 4 * 1024 * 1024)
    if record.get("status") in (None, "running"):
        raise RuntimeError("Attempt is not cleared for reading: " + tag)
    source = ROOT / "attempts" / tag / "control.json"
    payload = source.read_bytes()
    expected = record["submission_sha256"]["control.json"]
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise RuntimeError("Control does not match completed run snapshot: " + tag)
    gate = {"attempt": tag, "observed_utc": datetime.now(timezone.utc).isoformat(), "run_status_before_attempt_read": record["status"], "run_finished_at": record.get("finished_at"), "run_record_sha256": digest(path), "control_sha256": actual, "cutoff_hash_matches": True, "source": str(source), "generation": record["generation"]}
    dump(tag + ".run_gate.json", gate)
    target = HERE / (tag + ".control.json")
    target.write_bytes(payload)
    artifact = fc.read_json(target)
    gate["artifact_canonical_sha256"] = hashlib.sha256(json.dumps(artifact, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    dump(tag + ".run_gate.json", gate)
    return artifact, gate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True, choices=("v_3", "v_4"))
    arguments = parser.parse_args()
    started = time.perf_counter()
    artifact, gate = acquire_completed(arguments.attempt)
    protocol = fc.read_json(TRUSTED / "protocol.json")
    splines, certificate = fc.validate_artifact(artifact, protocol)
    old = ROOT / "adversary/ratchet_1"
    cases = fc.read_json(old / "broad_cases.json", 1024 * 1024)
    assert len(cases) == 320
    for case in cases:
        for name, bounds in protocol["uncertainty"].items():
            assert bounds[0] <= case[name] <= bounds[1]
    dump("broad_cases.json", cases)
    protected = {name: digest(ROOT / name) for name in ("evaluator/evaluate.py", "evaluator/hidden/field_control.py", "evaluator/hidden/protocol.json", "evaluator/hidden/cases.json", "participant/input/protocol.json")}
    reference_paths = [old / "reference_cache" / (fc.reference_key(cases[offset:offset + 16], (64, 32)) + ".npz") for offset in range(0, len(cases), 16)]
    if not all(path.is_file() for path in reference_paths):
        raise RuntimeError("Preexisting trusted broad reference cache is incomplete")
    freeze = {"attempt_read_gate": gate, "sampling": "All 256 Cartesian corners plus the same 64 Latin-hypercube interiors predetermined in ratchet 1", "interior_seed": 2026082801, "adaptive_samples": 0, "case_count": 320, "grid": [64, 32], "dt": 0.02, "case_sha256": digest(HERE / "broad_cases.json"), "prior_case_sha256": digest(old / "broad_cases.json"), "frozen_root_sha256": protected, "read_only_reference_sha256": {str(path.relative_to(ROOT)): digest(path) for path in reference_paths}, "stage_generation_3_authorized": False, "note": "Screening only; no fresh pass, champion selection or ratchet construction is inferred from a surrogate."}
    dump(arguments.attempt + ".screen_input_freeze.json", freeze)
    old_report = fc.read_json(old / "broad_screen.json", 4 * 1024 * 1024)
    if gate["control_sha256"] == old_report["frozen_inputs"]["artifact_sha256"] and freeze["case_sha256"] == old_report["frozen_inputs"]["case_sha256"]:
        report = dict(old_report)
        report.update({"attempt": arguments.attempt, "frozen_inputs": freeze, "reused_identical_artifact_screen": True, "reuse_source": "adversary/ratchet_1/broad_screen.json", "reuse_source_sha256": digest(old / "broad_screen.json"), "new_simulation_seconds": 0.0})
        dump(arguments.attempt + ".broad_screen.json", report)
        print("EXACT_PREVIOUS_SCREEN_REUSED", arguments.attempt, report["minimum_fidelity"], flush=True)
        return
    results = []
    for batch_index, offset in enumerate(range(0, len(cases), 16)):
        batch = cases[offset:offset + 16]
        with np.load(reference_paths[batch_index], allow_pickle=False) as data:
            initial, target, residual = data["initial"].copy(), data["target"].copy(), float(data["residual"])
        assert residual <= 2e-6
        state, diagnostics = fc.evolve(splines, batch, (64, 32), 0.02, initial)
        scores = fc.fidelities(state, target, (64, 32))
        for index, case in enumerate(batch):
            results.append({"case": case, "fidelity": float(scores[index]), "reference_residual": residual, "diagnostics": {name: float(value[index]) for name, value in diagnostics.items()}})
        dump(arguments.attempt + ".broad_screen.json", {"status": "running", "count": len(results), "results": results, "frozen_inputs": freeze})
        print("PROGRESS", arguments.attempt, len(results), "min", min(entry["fidelity"] for entry in results), "below_0_98", sum(entry["fidelity"] < 0.98 for entry in results), "seconds", time.perf_counter() - started, flush=True)
    assert protected == {name: digest(ROOT / name) for name in protected}
    report = {"status": "complete", "attempt": arguments.attempt, "count": len(results), "corner_count": 256, "interior_count": 64, "below_0_98": sum(entry["fidelity"] < 0.98 for entry in results), "corner_below_0_98": sum(entry["fidelity"] < 0.98 and entry["case"]["id"].startswith("corner_") for entry in results), "interior_below_0_98": sum(entry["fidelity"] < 0.98 and entry["case"]["id"].startswith("interior_") for entry in results), "minimum_fidelity": min(entry["fidelity"] for entry in results), "maximum_boundary_mass": max(entry["diagnostics"]["boundary_mass"] for entry in results), "screen_boundary_guard_exceedances": sum(entry["diagnostics"]["boundary_mass"] > 1e-8 for entry in results), "runtime_seconds": time.perf_counter() - started, "results": results, "frozen_inputs": freeze, "note": "Surrogate leads only. Generation 3 remains conditional on an official G2 pass and both completed grades."}
    dump(arguments.attempt + ".broad_screen.json", report)
    print("SCREEN_COMPLETE", json.dumps({name: value for name, value in report.items() if name not in ("results", "frozen_inputs")}), flush=True)


if __name__ == "__main__":
    main()
