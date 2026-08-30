"""Private radius and valid-neighbor endpoint calibration."""

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

BASE = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "participant" / "workspace"))
from api import CONSTRAINTS, endpoint_failures
from oracle import DeterminantCC


def directions():
    result = []
    for row in range(15):
        for column in range(row, 15):
            matrix = np.zeros((15, 15))
            matrix[row, column] = 1 if row == column else 1 / np.sqrt(2)
            matrix[column, row] = matrix[row, column]
            result.append((row, column, matrix))
    return result


def measure(oracle, data, radius, inset=False):
    interaction = np.array(data["pair_matrix"])
    scale = 1.0
    if inset:
        scale = min(1.0, (1.5 - radius - 1e-7) / np.max(abs(interaction)),
                    (7 - radius - 1e-7) / np.linalg.norm(interaction))
        interaction *= scale
    hamiltonian, _, _ = oracle.hamiltonian(data["orbital_energies"], interaction)
    result = oracle.solve(hamiltonian, data["amplitudes"])
    records = []
    points = [(-1, -1, 0, interaction)]
    for row, column, direction in directions():
        for sign in (1, -1):
            points.append((row, column, sign, interaction + sign * radius * direction))
    for row, column, sign, point in points:
        if np.max(abs(point)) > 1.5 or np.linalg.norm(point) > 7:
            records.append({"axis": [row, column], "sign": sign, "domain_valid": False})
            continue
        matrix, _, _ = oracle.hamiltonian(data["orbital_energies"], point)
        solved = oracle.solve(matrix, result.amplitudes, tolerance=2e-11, max_evaluations=250)
        if not solved.converged:
            records.append({"axis": [row, column], "sign": sign, "domain_valid": True,
                            "failures": ["cc_convergence"]})
            continue
        diagnostic = oracle.diagnostics(matrix, solved)
        failures = endpoint_failures(diagnostic)
        if diagnostic["occupation_violation"] < 0.02:
            failures.append("population_violation")
        records.append({"axis": [row, column], "sign": sign, "domain_valid": True,
                        "failures": failures, "dad": diagnostic["rdm_dad"],
                        "energy_error": diagnostic["energy_error"],
                        "population_violation": diagnostic["occupation_violation"],
                        "overlap": diagnostic["ground_overlap"]})
    valid = [record for record in records if record["domain_valid"]]
    diagnosed = [record for record in valid if "dad" in record]
    return {"radius": radius, "inset": inset, "inset_scale": scale,
            "domain_invalid": len(records) - len(valid), "domain_valid": len(valid),
            "endpoint_passing_points": sum(not record["failures"] for record in valid),
            "failure_clusters_valid_only": dict(Counter(failure for record in valid for failure in record["failures"])),
            "max_dad": max(record["dad"] for record in diagnosed),
            "max_energy_error": max(record["energy_error"] for record in diagnosed),
            "min_population_violation": min(record["population_violation"] for record in diagnosed),
            "records": records}


def main():
    started = time.monotonic()
    oracle = DeterminantCC()
    sources = ["champions/generation_2/submission.json", "attempts/v_2_r2/submission.json",
               "adversary/generation_2/worker_feasibility_champion_high/closest_candidate.json",
               "adversary/generation_2/worker_feasibility_replicate1_high/closest_candidate.json"]
    reports = []
    for relative in sources:
        path = BASE / relative
        if not path.is_file():
            continue
        data = json.loads(path.read_text())
        for radius in (0.001, 0.002, 0.003):
            for inset in (False, True):
                result = measure(oracle, data, radius, inset)
                result["source"] = relative
                reports.append(result)
                print(json.dumps({key: value for key, value in result.items() if key != "records"}), flush=True)
                (OUTPUT / "stencil_calibration.json").write_text(json.dumps({"reports": reports,
                     "runtime_seconds": time.monotonic() - started}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
