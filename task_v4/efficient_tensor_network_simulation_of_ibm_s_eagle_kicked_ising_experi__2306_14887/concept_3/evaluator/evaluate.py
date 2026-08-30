"""Trusted checker. No submission code or public simulator is imported."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

N_QUBITS = 12
DEPTH = 24
GROUPS = (0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0)
THRESHOLD = 0.95
Z_DRIFT_BOUND = 0.01
SCENARIO_DIGEST = "0753ffe6019891d37183bdd252a8a781fec81336d3ccc29925a3f0221bfedff9"
MAXIMUM_BYTES = 65536


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def read_artifact(submission):
    artifact = Path(submission) / "pulses.json"
    if artifact.is_symlink() or not artifact.is_file():
        raise ValueError("pulses.json must be a regular non-symlink file")
    with artifact.open("rb") as handle:
        raw = handle.read(MAXIMUM_BYTES + 1)
    if len(raw) > MAXIMUM_BYTES:
        raise ValueError("artifact exceeds 65536 bytes")
    payload = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "angles"}:
        raise ValueError("only schema_version and angles fields are allowed")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise ValueError("schema_version must be integer 1")
    angles = payload["angles"]
    if type(angles) is not list or len(angles) != DEPTH:
        raise ValueError("exactly 24 control rows required")
    for row in angles:
        if type(row) is not list or len(row) != 2:
            raise ValueError("each row must contain exactly two angles")
        for value in row:
            if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > math.pi:
                raise ValueError("angles must be finite numbers in [-pi, pi]")
    return np.asarray(angles, dtype=np.float64), hashlib.sha256(raw).hexdigest()


def apply_one(tensor, matrix, site, n_qubits=N_QUBITS):
    axis = n_qubits - 1 - site
    moved = np.moveaxis(tensor, axis, 0)
    contracted = np.tensordot(matrix, moved, axes=([1], [0]))
    return np.moveaxis(contracted, 0, axis)


def apply_zz(tensor, first, second, exponent, n_qubits=N_QUBITS):
    axes = (n_qubits - 1 - first, n_qubits - 1 - second)
    moved = np.moveaxis(tensor, axes, (0, 1))
    gate = np.diag(np.exp(1j * exponent * np.array([1, -1, -1, 1])))
    contracted = np.tensordot(gate.reshape(2, 2, 2, 2), moved, axes=([2, 3], [0, 1]))
    return np.moveaxis(contracted, (0, 1), axes)


def evolve(angles, scenario):
    tensor = np.full((2,) * N_QUBITS, 1 / math.sqrt(2 ** N_QUBITS), dtype=np.complex128)
    gains = (1 + scenario["gain_a"], 1 + scenario["gain_b"])
    for layer in range(DEPTH):
        for edge in range(layer % 2, N_QUBITS, 2):
            exponent = math.pi / 4 * (1 + scenario["zz_common"] + scenario["zz_local"][edge])
            tensor = apply_zz(tensor, edge, (edge + 1) % N_QUBITS, exponent)
        for site, group in enumerate(GROUPS):
            half_angle = angles[layer, group] * gains[group] / 2
            cosine, sine = math.cos(half_angle), -1j * math.sin(half_angle)
            tensor = apply_one(tensor, np.array([[cosine, sine], [sine, cosine]]), site)
        for site, detuning in enumerate(scenario["z_drift_radians_per_layer"]):
            forward = complex(math.cos(detuning / 2), -math.sin(detuning / 2))
            tensor = apply_one(tensor, np.array([[forward, 0], [0, forward.conjugate()]]), site)
    return tensor.reshape(-1)


def load_scenarios():
    raw = (Path(__file__).resolve().parent / "hidden" / "scenarios.json").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SCENARIO_DIGEST:
        raise RuntimeError("trusted scenario digest mismatch")
    scenarios = json.loads(raw)["scenarios"]
    if len(scenarios) != 223:
        raise RuntimeError("trusted scenario count mismatch")
    for scenario in scenarios:
        if len(scenario["zz_local"]) != 12 or len(scenario["z_drift_radians_per_layer"]) != 12:
            raise RuntimeError("trusted scenario shape mismatch")
        values = [scenario["gain_a"], scenario["gain_b"], scenario["zz_common"],
                  *scenario["zz_local"], *scenario["z_drift_radians_per_layer"]]
        bounds = [0.025, 0.025, 0.015] + [0.005] * 12 + [Z_DRIFT_BOUND] * 12
        if any(type(value) not in (int, float) or not math.isfinite(value) or abs(value) > bound
               for value, bound in zip(values, bounds)):
            raise RuntimeError("trusted scenario outside published calibration family")
    return scenarios, digest


def evaluate(submission):
    started = time.monotonic()
    angles, artifact_digest = read_artifact(submission)
    scenarios, scenario_digest = load_scenarios()
    families = {}
    subfamilies = {}
    norm_error = 0.0
    parity_error = 0.0
    parity_checked = 0
    drift_parities = []
    for scenario in scenarios:
        state = evolve(angles, scenario)
        norm_error = max(norm_error, abs(float(np.vdot(state, state).real) - 1))
        if all(detuning == 0.0 for detuning in scenario["z_drift_radians_per_layer"]):
            parity_error = max(parity_error, float(np.max(np.abs(state - state[::-1]))))
            parity_checked += 1
        else:
            drift_parities.append(float(np.vdot(state, state[::-1]).real))
        fidelity = float(abs((state[0] + state[-1]) / math.sqrt(2)) ** 2)
        families.setdefault(scenario["family"], []).append(fidelity)
        subfamilies.setdefault(scenario["subfamily"], []).append(fidelity)
    scores = [score for family in families.values() for score in family]
    if norm_error > 2e-10 or parity_error > 2e-10 or not all(math.isfinite(score) for score in scores):
        raise RuntimeError("trusted simulator invariant violation")
    minimum = min(scores)
    elapsed = time.monotonic() - started
    passed = minimum >= THRESHOLD
    reason = ("Every frozen scenario meets the fidelity threshold." if passed
              else "At least one frozen scenario is below the fidelity threshold.")
    return {"valid": True, "passed": passed, "score": minimum,
            "min_fidelity": minimum, "mean_fidelity": float(np.mean(scores)),
            "core_score": min(families["core"]),
            "worst_family_score": min(families["worst_family"]),
            "resource_score": 1.0, "runtime": elapsed, "runtime_seconds": elapsed,
            "reason": reason,
            "threshold": THRESHOLD, "scenario_count": len(scores),
            "family_minima": {name: min(values) for name, values in families.items()},
            "subfamily_minima": {name: min(values) for name, values in subfamilies.items()},
            "ratchet_generation": 1, "parity_invariant_scope": "zero_detuning_only",
            "parity_checked_scenarios": parity_checked,
            "nonzero_drift_scenarios": len(drift_parities),
            "minimum_global_x_expectation_with_drift": min(drift_parities),
            "max_norm_error": norm_error, "max_global_x_parity_error": parity_error,
            "artifact_sha256": artifact_digest, "scenario_sha256": scenario_digest,
            "elapsed_seconds": elapsed}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    exit_code = 0
    try:
        result = evaluate(args.submission)
    except (ValueError, OSError, OverflowError, RecursionError) as error:
        elapsed = time.monotonic() - started
        result = {"valid": False, "passed": False, "score": 0.0,
                  "core_score": 0.0, "worst_family_score": 0.0,
                  "resource_score": 0.0, "runtime": elapsed, "runtime_seconds": elapsed,
                  "elapsed_seconds": elapsed, "reason": "Invalid artifact: " + str(error),
                  "threshold": THRESHOLD, "error": str(error)}
        exit_code = 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, allow_nan=False))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
