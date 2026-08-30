"""Private calibration optimizer. The winning data are never participant inputs."""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "participant" / "workspace"))
from oracle import DeterminantCC


def run(source, destination):
    data = json.loads(source.read_text())
    oracle = DeterminantCC()
    energies = np.asarray(data["orbital_energies"])
    initial = np.asarray(data["amplitudes"])
    indices = np.triu_indices(15)
    vector = np.asarray(data["pair_matrix"])[indices]
    cache = {}
    count = 0
    started = time.monotonic()

    def unpack(parameters):
        interaction = np.zeros((15, 15))
        interaction[indices] = parameters
        interaction[(indices[1], indices[0])] = parameters
        return interaction

    def evaluate(parameters):
        nonlocal count
        key = parameters.tobytes()
        if key not in cache:
            interaction = unpack(parameters)
            hamiltonian, _, _ = oracle.hamiltonian(energies, interaction)
            result = oracle.solve(hamiltonian, initial)
            stats = oracle.diagnostics(hamiltonian, result)
            stats["interaction_norm"] = float(np.linalg.norm(interaction))
            cache.clear()
            cache[key] = (stats, result)
            count += 1
        return cache[key]

    def objective(parameters):
        return float(np.sum((parameters - vector) ** 2))

    def constraints(parameters):
        stats, result = evaluate(parameters)
        return np.array([
            stats["occupation_violation"] - 0.025,
            (8e-5 - stats["energy_error"]) * 100,
            (stats["ground_overlap"] - 0.9992) * 100,
            stats["fci_gap"] - 0.12,
            stats["reference_weight"] - 0.5,
            stats["hf_real_min"] - 0.08,
            stats["hf_imaginary_min"] - 0.08,
            (80 - stats["jacobian_condition"]) / 100,
            1.25 - stats["amplitude_norm"],
            1.5 - stats["lambda_norm"],
            stats["eom_real"][0] - 0.08,
            7 - stats["interaction_norm"],
            (1e-8 - result.residual) * 1e5,
        ])

    def callback(parameters):
        stats, result = evaluate(parameters)
        print(json.dumps({"calls": count, "violation": stats["occupation_violation"],
                          "error": stats["energy_error"], "overlap": stats["ground_overlap"],
                          "gap": stats["fci_gap"], "feasibility": float(min(constraints(parameters)))}), flush=True)
        if min(constraints(parameters)) >= -1e-6:
            artifact = {"schema_version": 1, "orbital_energies": energies.tolist(),
                        "pair_matrix": unpack(parameters).tolist(), "amplitudes": result.amplitudes.tolist()}
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "candidate.json").write_text(json.dumps(artifact, indent=2))
            (destination / "diagnostics.json").write_text(json.dumps(stats, indent=2))

    answer = minimize(objective, vector, method="SLSQP", bounds=[(-1.5, 1.5)] * len(vector),
                      constraints=[{"type": "ineq", "fun": constraints}], callback=callback,
                      options={"maxiter": 60, "ftol": 1e-10, "disp": True})
    callback(answer.x)
    print(json.dumps({"success": bool(answer.success), "calls": count, "runtime_seconds": time.monotonic() - started}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    run(arguments.source, arguments.destination)
