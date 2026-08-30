"""Exact complex128 state vectors; site zero is the least significant bit."""

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROBLEM = json.loads((ROOT / "input" / "problem.json").read_text())
N_QUBITS = PROBLEM["n_qubits"]
DEPTH = PROBLEM["depth"]
GROUPS = np.asarray(PROBLEM["group_by_site"])
EDGES = PROBLEM["edges"]
DIMENSION = 1 << N_QUBITS
BASIS = np.arange(DIMENSION)
SITE_SIGNS = np.asarray([1 - 2 * ((BASIS >> site) & 1) for site in range(N_QUBITS)])
EDGE_SIGNS = np.asarray([
    1 - 2 * (((BASIS >> first) ^ (BASIS >> second)) & 1)
    for first, second in EDGES
])


def scenario(gain_a=0.0, gain_b=0.0, zz_common=0.0, zz_local=None, z_drift_radians_per_layer=None):
    return {"gain_a": float(gain_a), "gain_b": float(gain_b),
            "zz_common": float(zz_common),
            "zz_local": [0.0] * len(EDGES) if zz_local is None else list(zz_local),
            "z_drift_radians_per_layer": [0.0] * N_QUBITS if z_drift_radians_per_layer is None
            else list(z_drift_radians_per_layer)}


def simulate(angles, scenarios=None):
    """Return shape (number of scenarios, 4096), with no truncation."""
    angles = np.asarray(angles, dtype=np.float64)
    if angles.shape != (DEPTH, 2) or not np.all(np.isfinite(angles)):
        raise ValueError("angles must be a finite (24, 2) array")
    if np.any(np.abs(angles) > np.pi):
        raise ValueError("angles outside [-pi, pi]")
    scenarios = [scenario()] if scenarios is None else list(scenarios)
    if not scenarios:
        raise ValueError("at least one scenario is required")
    count = len(scenarios)
    gains = 1 + np.asarray([[entry["gain_a"], entry["gain_b"]] for entry in scenarios])
    edge_gains = 1 + np.asarray([
        np.asarray(entry["zz_local"]) + entry["zz_common"] for entry in scenarios
    ])
    phases = [np.exp(1j * np.pi / 4 * (edge_gains[:, matching::2] @ EDGE_SIGNS[matching::2]))
              for matching in (0, 1)]
    detunings = np.asarray([entry.get("z_drift_radians_per_layer", [0.0] * N_QUBITS)
                           for entry in scenarios], dtype=np.float64)
    if detunings.shape != (count, N_QUBITS) or not np.all(np.isfinite(detunings)):
        raise ValueError("each scenario needs 12 finite static Z drift angles")
    if np.any(np.abs(detunings) > 0.01):
        raise ValueError("static Z drift outside [-0.01, 0.01]")
    drift_phases = np.exp(-0.5j * (detunings @ SITE_SIGNS))
    states = np.full((count, DIMENSION), 1 / np.sqrt(DIMENSION), dtype=np.complex128)
    for layer, controls in enumerate(angles):
        states *= phases[layer % 2]
        for site, group in enumerate(GROUPS):
            half_angle = controls[group] * gains[:, group] / 2
            cosine = np.cos(half_angle).reshape(count, 1, 1)
            sine = (-1j * np.sin(half_angle)).reshape(count, 1, 1)
            blocks = states.reshape(count, -1, 2, 1 << site)
            lower = blocks[:, :, 0, :].copy()
            upper = blocks[:, :, 1, :].copy()
            blocks[:, :, 0, :] = cosine * lower + sine * upper
            blocks[:, :, 1, :] = sine * lower + cosine * upper
        states *= drift_phases
    return states


def fidelities(angles, scenarios=None):
    states = simulate(angles, scenarios)
    return np.abs((states[:, 0] + states[:, -1]) / np.sqrt(2)) ** 2


def load_pulses(directory):
    return np.asarray(json.loads((Path(directory) / "pulses.json").read_text())["angles"])


def save_pulses(directory, angles):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "angles": np.asarray(angles).tolist()}
    (directory / "pulses.json").write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def training_scenarios():
    return json.loads((ROOT / "input" / "training_scenarios.json").read_text())["scenarios"]
