"""Test a small open neighborhood around the private calibration witness."""

import json
import os
import sys
import time
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "participant" / "workspace"))
sys.path.insert(0, str(BASE / "evaluator"))

from api import artifact
from evaluate import evaluate_artifact
from oracle import DeterminantCC, random_pair_matrix


def main():
    started = time.monotonic()
    directory = BASE / "evaluator" / "hidden" / "calibration_refined"
    witness = json.loads((directory / "candidate.json").read_text())
    interaction = np.array(witness["pair_matrix"])
    amplitudes = np.array(witness["amplitudes"])
    oracle = DeterminantCC()
    rng = np.random.default_rng(302017)
    records = []
    probe_path = directory / "robustness_probe.json"
    for trial in range(12):
        changed = interaction + random_pair_matrix(rng, scale=1e-5)
        hamiltonian, _, _ = oracle.hamiltonian(witness["orbital_energies"], changed)
        result = oracle.solve(hamiltonian, amplitudes)
        probe_path.write_text(json.dumps(artifact(changed, result.amplitudes), allow_nan=False))
        report = evaluate_artifact(probe_path, directory)
        records.append({"trial": trial, "passed": report["passed"], "core_score": report["core_score"],
                        "reason": report["reason"], "energy_error": report["diagnostics"].get("energy_error"),
                        "runtime_seconds": report["runtime_seconds"]})
    probe_path.unlink()
    report = {"perturbation_standard_deviation": 1e-5, "seed": 302017, "trials": records,
              "passed": all(row["passed"] for row in records),
              "minimum_core_score": min(row["core_score"] for row in records),
              "runtime_seconds": time.monotonic() - started}
    (directory / "robustness.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({key: value for key, value in report.items() if key != "trials"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
