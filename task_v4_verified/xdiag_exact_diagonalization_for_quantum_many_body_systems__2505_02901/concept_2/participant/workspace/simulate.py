import argparse
import json
import os
from pathlib import Path

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.linalg import eigh


def load_problem(input_directory):
    directory = Path(input_directory)
    specification = json.loads((directory / "spec.json").read_text())
    with np.load(directory / "hamiltonians.npz", allow_pickle=False) as archive:
        drifts = archive["drifts"]
        controls = archive["controls"]
        initial = archive["initial"]
    with np.load(directory / "targets.npz", allow_pickle=False) as archive:
        targets = archive["targets"]
    return specification, drifts, controls, initial, targets


def propagate(amplitudes, specification, drifts, controls, initial):
    evolved = []
    for drift in drifts:
        states = initial.copy()
        for amplitudes_slice in amplitudes:
            hamiltonian = drift + np.einsum("c,cij->ij", amplitudes_slice, controls)
            energies, vectors = eigh(hamiltonian, check_finite=False, driver="evd")
            phases = np.exp(-1j * specification["slice_duration"] * energies)
            states = vectors @ (phases[:, None] * (vectors.conj().T @ states))
        evolved.append(states)
    return np.asarray(evolved)


def physical_usage(amplitudes, specification):
    limits = np.asarray(specification["amplitude_limits"])
    jumps = np.diff(np.vstack((np.zeros((1, 3)), amplitudes, np.zeros((1, 3)))), axis=0)
    exposure = float(specification["slice_duration"] * np.sum((amplitudes / limits) ** 2))
    tolerance = specification["physical_constraint_tolerance"]
    admissible = bool(
        np.all(np.abs(amplitudes) <= limits + tolerance)
        and np.all(np.abs(jumps) <= np.asarray(specification["adjacent_jump_limits"]) + tolerance)
        and exposure <= specification["normalized_control_exposure_limit"] + tolerance
    )
    return {
        "physical_valid": admissible,
        "maximum_amplitude_by_channel": np.max(np.abs(amplitudes), axis=0).tolist(),
        "maximum_jump_by_channel": np.max(np.abs(jumps), axis=0).tolist(),
        "normalized_control_exposure": exposure,
    }


def fidelities(states, targets):
    members = []
    for actual, desired in zip(states, targets):
        overlap = desired.conj().T @ actual
        trace = np.trace(overlap)
        aligned = np.exp(-1j * np.angle(trace)) * overlap
        hermitian = (aligned + aligned.conj().T) / 2
        lower = max(0.0, float(np.linalg.eigvalsh(hermitian)[0])) ** 2
        members.append({
            "isometry_fidelity": float(np.clip(abs(trace / actual.shape[1]) ** 2, 0, 1)),
            "minimum_column_fidelity": float(np.clip(np.min(abs(np.diag(overlap)) ** 2), 0, 1)),
            "superposition_floor": float(np.clip(lower, 0, 1)),
        })
    return {
        "core_score": float(np.mean([member["isometry_fidelity"] for member in members])),
        "worst_family_score": min(member["superposition_floor"] for member in members),
        "minimum_column_fidelity": min(member["minimum_column_fidelity"] for member in members),
        "members": members,
    }


def score(amplitudes, problem):
    specification, drifts, controls, initial, targets = problem
    amplitudes = np.asarray(amplitudes, dtype=float)
    if amplitudes.shape != (specification["slices"], specification["channels"]):
        raise ValueError("Expected a (24,3) amplitude array")
    if not np.all(np.isfinite(amplitudes)):
        raise ValueError("Amplitudes must be finite")
    report = physical_usage(amplitudes, specification)
    report.update(fidelities(propagate(amplitudes, specification, drifts, controls, initial), targets))
    report["passed"] = bool(
        report["physical_valid"]
        and report["core_score"] >= specification["mean_isometry_fidelity_min"]
        and report["worst_family_score"] >= specification["worst_superposition_fidelity_min"]
        and report["minimum_column_fidelity"] >= specification["minimum_column_fidelity_min"]
    )
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path(__file__).resolve().parents[1] / "input")
    parser.add_argument("--pulse", type=Path, required=True)
    arguments = parser.parse_args()
    payload = json.loads(arguments.pulse.read_text())
    print(json.dumps(score(payload["amplitudes"], load_problem(arguments.input)), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
