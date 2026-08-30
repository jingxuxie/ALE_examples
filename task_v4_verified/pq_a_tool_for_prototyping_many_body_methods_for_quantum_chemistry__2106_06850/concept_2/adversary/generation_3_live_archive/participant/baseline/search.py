"""Reproducible random-search baseline; no privileged witness is embedded."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from api import CONSTRAINTS, artifact, endpoint_failures, robust_screen
from oracle import DeterminantCC, random_pair_matrix


def run(trials, seed, output):
    rng = np.random.default_rng(seed)
    oracle = DeterminantCC()
    energies = CONSTRAINTS["orbital_energies"]
    best = 0.0
    best_artifact = artifact(np.zeros((15, 15)), np.zeros(oracle.count))
    counts = {"trials": trials, "in_domain": 0, "hf_stable": 0, "converged": 0,
              "endpoint_feasible": 0, "path_feasible": 0, "passing": 0}
    started = time.monotonic()
    for trial in range(trials):
        interaction = random_pair_matrix(rng, float(rng.uniform(0.06, 0.65)))
        if np.max(np.abs(interaction)) > CONSTRAINTS["pair_entry_max"] or np.linalg.norm(interaction) > CONSTRAINTS["pair_frobenius_max"]:
            continue
        counts["in_domain"] += 1
        hamiltonian, _, _ = oracle.hamiltonian(energies, interaction)
        stability = oracle.hf_stability(hamiltonian)
        if min(np.linalg.eigvalsh(matrix)[0] for matrix in stability) < CONSTRAINTS["hf_curvature_min"]:
            continue
        counts["hf_stable"] += 1
        result = oracle.solve(hamiltonian)
        if not result.converged:
            continue
        counts["converged"] += 1
        diagnostics = oracle.diagnostics(hamiltonian, result)
        if endpoint_failures(diagnostics):
            continue
        counts["endpoint_feasible"] += 1
        value = diagnostics["occupation_violation"]
        if value <= best:
            continue
        robust = robust_screen(interaction, result.amplitudes, oracle)
        if not robust.get("path_certified", False) or not robust.get("endpoint_feasible", False):
            continue
        value = robust["core_score"]
        if value <= best:
            continue
        counts["path_feasible"] += 1
        best = value
        best_artifact = artifact(interaction, result.amplitudes)
        print(json.dumps({"trial": trial, "population_violation": best}), flush=True)
        if best >= CONSTRAINTS["population_violation_min"]:
            counts["passing"] += 1
            break
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(best_artifact, indent=2, allow_nan=False))
    summary = {"seed": seed, "best_core_score": best,
               "score": min(1.0, best / CONSTRAINTS["population_violation_min"]),
               "passed": bool(counts["passing"]), "counts": counts,
               "runtime_seconds": time.monotonic() - started}
    output.with_suffix(".search.json").write_text(json.dumps(summary, indent=2, allow_nan=False))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260828)
    parser.add_argument("--output", type=Path, default=Path("submission.json"))
    arguments = parser.parse_args()
    run(arguments.trials, arguments.seed, arguments.output)
