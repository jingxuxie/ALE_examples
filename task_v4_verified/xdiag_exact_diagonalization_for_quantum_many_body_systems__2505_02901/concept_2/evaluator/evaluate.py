import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time

sys.dont_write_bytecode = True
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.linalg import eigh
from physics import assemble

HIDDEN = Path(__file__).resolve().parent / "hidden"


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("Nonfinite JSON number: " + value)


def read_pulse(submission, specification):
    path = Path(submission)
    if path.is_dir():
        path = path / "pulse.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError("Submission must be a regular pulse.json file, not a symlink")
    with path.open("rb") as stream:
        raw = stream.read(specification["submission_max_bytes"] + 1)
    if len(raw) > specification["submission_max_bytes"]:
        raise ValueError("Submission exceeds byte limit")
    payload = json.loads(raw, parse_constant=reject_constant, object_pairs_hook=unique_object)
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "amplitudes"}:
        raise ValueError("Expected exactly schema_version and amplitudes")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise ValueError("schema_version must be integer 1")
    rows = payload["amplitudes"]
    if not isinstance(rows, list) or len(rows) != specification["slices"]:
        raise ValueError("Expected 24 amplitude rows")
    for row in rows:
        if not isinstance(row, list) or len(row) != specification["channels"]:
            raise ValueError("Expected three amplitudes per row")
        for value in row:
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("Amplitudes must be finite real JSON numbers")
    return np.array(rows, dtype=float)


def resource_usage(amplitudes, specification):
    limits = np.array(specification["amplitude_limits"])
    maximum = np.max(np.abs(amplitudes), axis=0)
    tolerance = specification["physical_constraint_tolerance"]
    if np.any(maximum > limits + tolerance):
        return {
            "physical_valid": False,
            "maximum_amplitude_by_channel": maximum.tolist(),
            "maximum_jump_by_channel": None,
            "normalized_control_exposure": None,
            "resource_score": 0.0,
            "physical_failures": ["amplitude limit"],
        }
    jumps = np.diff(np.vstack((np.zeros((1, 3)), amplitudes, np.zeros((1, 3)))), axis=0)
    maximum_jump = np.max(np.abs(jumps), axis=0)
    exposure = float(specification["slice_duration"] * np.sum((amplitudes / limits) ** 2))
    failures = []
    if np.any(maximum > limits + tolerance):
        failures.append("amplitude limit")
    if np.any(maximum_jump > np.array(specification["adjacent_jump_limits"]) + tolerance):
        failures.append("slew/endpoint jump limit")
    if not np.isfinite(exposure) or exposure > specification["normalized_control_exposure_limit"] + tolerance:
        failures.append("integrated control exposure limit")
    return {
        "physical_valid": not failures,
        "maximum_amplitude_by_channel": maximum.tolist(),
        "maximum_jump_by_channel": maximum_jump.tolist(),
        "normalized_control_exposure": exposure if np.isfinite(exposure) else None,
        "resource_score": max(0.0, 1.0 - exposure / specification["normalized_control_exposure_limit"]) if not failures else 0.0,
        "physical_failures": failures,
    }


def propagate(amplitudes, specification, drifts, controls, initial):
    results = []
    for drift in drifts:
        actual = initial.copy()
        for row in amplitudes:
            hamiltonian = drift.copy()
            for channel, amplitude in enumerate(row):
                hamiltonian += amplitude * controls[channel]
            energies, eigenvectors = eigh(hamiltonian, check_finite=True, driver="evr")
            coordinates = eigenvectors.conj().T @ actual
            coordinates *= np.exp(-1j * specification["slice_duration"] * energies)[:, None]
            actual = eigenvectors @ coordinates
        results.append(actual)
    return np.array(results)


def fidelity_report(actual, targets, names):
    members = []
    for states, desired, name in zip(actual, targets, names):
        overlap = desired.conj().T @ states
        trace = np.trace(overlap)
        phase = np.angle(trace) if trace != 0 else 0.0
        aligned = np.exp(-1j * phase) * overlap
        lower = float(eigh((aligned + aligned.conj().T) / 2, eigvals_only=True)[0])
        members.append({
            "name": name,
            "isometry_fidelity": float(np.clip(abs(trace / states.shape[1]) ** 2, 0, 1)),
            "minimum_column_fidelity": float(np.clip(np.min(abs(np.diag(overlap)) ** 2), 0, 1)),
            "superposition_floor": float(np.clip(max(0.0, lower) ** 2, 0, 1)),
            "aligned_global_phase": float(phase),
        })
    return {
        "core_score": float(np.mean([member["isometry_fidelity"] for member in members])),
        "worst_family_score": min(member["superposition_floor"] for member in members),
        "minimum_column_fidelity": min(member["minimum_column_fidelity"] for member in members),
        "members": members,
    }


def load_locked_problem():
    manifest = json.loads((HIDDEN / "integrity.json").read_text())
    for filename, digest in manifest.items():
        if hashlib.sha256((HIDDEN / filename).read_bytes()).hexdigest() != digest:
            raise RuntimeError("Locked evaluator asset digest mismatch: " + filename)
    specification = json.loads((HIDDEN / "spec.json").read_text())
    model = json.loads((HIDDEN / "model.json").read_text())
    with np.load(HIDDEN / "targets.npz", allow_pickle=False) as archive:
        targets = archive["targets"]
    basis, drifts, controls, initial = assemble(model)
    if targets.shape != (len(drifts), len(basis), initial.shape[1]) or not np.all(np.isfinite(targets)):
        raise RuntimeError("Invalid evaluator target isometries")
    orthogonality = max(float(np.linalg.norm(target.conj().T @ target - np.eye(initial.shape[1]), ord=2)) for target in targets)
    if orthogonality > specification["numerical_orthonormality_tolerance"]:
        raise RuntimeError("Evaluator targets are not orthonormal")
    return specification, model, drifts, controls, initial, targets


def evaluate(submission):
    start = time.monotonic()
    report = {"core_score": 0.0, "worst_family_score": 0.0, "minimum_column_fidelity": 0.0, "resource_score": 0.0, "runtime_score": 0.0, "valid": False, "passed": False, "evaluator_valid": True, "reason": "Not evaluated"}
    try:
        specification, model, drifts, controls, initial, targets = load_locked_problem()
        try:
            amplitudes = read_pulse(submission, specification)
        except (ValueError, OSError, TypeError, OverflowError, RecursionError) as error:
            report["reason"] = "Invalid submission: " + str(error)
            return report
        report.update(resource_usage(amplitudes, specification))
        if not report["physical_valid"]:
            report["reason"] = "Physical constraint violation: " + "; ".join(report["physical_failures"])
            return report
        actual = propagate(amplitudes, specification, drifts, controls, initial)
        if not np.all(np.isfinite(actual)):
            raise RuntimeError("Nonfinite evaluator propagation")
        report.update(fidelity_report(actual, targets, [member["name"] for member in model["calibrations"]]))
        report["valid"] = True
        report["passed"] = bool(report["core_score"] >= specification["mean_isometry_fidelity_min"] and report["worst_family_score"] >= specification["worst_superposition_fidelity_min"] and report["minimum_column_fidelity"] >= specification["minimum_column_fidelity_min"])
        report["reason"] = "All fixed fidelity and physical constraints satisfied" if report["passed"] else "Admissible pulse misses the fixed coherent-fidelity target"
        report["fixed_target"] = {key: specification[key] for key in ("mean_isometry_fidelity_min", "worst_superposition_fidelity_min", "minimum_column_fidelity_min")}
    except Exception as error:
        report.update({"passed": False, "valid": False, "evaluator_valid": False, "reason": "Evaluator error: " + str(error)})
    finally:
        report["elapsed_seconds"] = time.monotonic() - start
        report["peak_memory_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
        report["runtime_score"] = float(report["elapsed_seconds"] <= 120 and report["peak_memory_mib"] <= 2048)
        if not report["runtime_score"]:
            report.update({"passed": False, "reason": "Evaluator resource limit exceeded"})
    return report


def timeout_handler(signum, frame):
    raise TimeoutError("120 second validation deadline")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(120)
    report = evaluate(arguments.submission)
    signal.alarm(0)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
