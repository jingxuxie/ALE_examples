"""Private pre-freeze random calibration, not the participant baseline."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "participant" / "workspace"))
from oracle import DeterminantCC, random_pair_matrix


def run(count, seed, output):
    oracle = DeterminantCC()
    rng = np.random.default_rng(seed)
    best = {"rdm": 0.0, "eom": 0.0, "low_eom": 0.0}
    counts = {"total": 0, "stable": 0, "converged": 0, "ground": 0, "accurate": 0}
    started = time.monotonic()
    output.mkdir(parents=True, exist_ok=True)
    for trial in range(count):
        energies = np.array([-1.2, -0.9, -0.5, 0.5, 0.9, 1.2])
        scale = float(rng.uniform(0.06, 0.65))
        interaction = random_pair_matrix(rng, scale)
        hamiltonian, _, _ = oracle.hamiltonian(energies, interaction)
        counts["total"] += 1
        stability = oracle.hf_stability(hamiltonian)
        if min(np.linalg.eigvalsh(matrix)[0] for matrix in stability) < 0.05:
            continue
        counts["stable"] += 1
        result = oracle.solve(hamiltonian)
        if not result.converged:
            continue
        counts["converged"] += 1
        diagnostics = oracle.diagnostics(hamiltonian, result)
        if diagnostics["ground_overlap"] < 0.95 or diagnostics["fci_gap"] < 0.1:
            continue
        counts["ground"] += 1
        if diagnostics["energy_error"] > 0.005:
            continue
        counts["accurate"] += 1
        metrics = {"rdm": diagnostics["occupation_violation"],
                   "eom": diagnostics["max_eom_imag"], "low_eom": diagnostics["low_pair_imag"]}
        for label, value in metrics.items():
            if value > best[label]:
                best[label] = value
                artifact = {"schema_version": 1, "orbital_energies": energies.tolist(),
                            "pair_matrix": interaction.tolist(), "amplitudes": result.amplitudes.tolist()}
                (output / (label + "_candidate.json")).write_text(json.dumps(artifact, indent=2))
                (output / (label + "_diagnostics.json")).write_text(json.dumps(diagnostics, indent=2))
                print(json.dumps({"trial": trial, "metric": label, "value": value,
                                  "error": diagnostics["energy_error"], "overlap": diagnostics["ground_overlap"]}), flush=True)
        if trial % 1000 == 0:
            print(json.dumps({"trial": trial, "best": best, "counts": counts}), flush=True)
    summary = {"seed": seed, "counts": counts, "best": best, "runtime_seconds": time.monotonic() - started}
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=9131)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    run(arguments.count, arguments.seed, arguments.output)
