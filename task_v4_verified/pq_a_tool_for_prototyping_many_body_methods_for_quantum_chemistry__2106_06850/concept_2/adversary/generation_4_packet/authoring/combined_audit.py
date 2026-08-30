"""Private combined-direction audit of completed, never running, submissions."""

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.linalg import eigh

PACKET = Path(__file__).resolve().parents[1]
BASE = PACKET.parents[1]
sys.path.insert(0, str(BASE / "participant" / "workspace"))
from api import CONSTRAINTS, endpoint_failures
from oracle import DeterminantCC


def basis_matrices():
    directions = []
    for row in range(15):
        for column in range(row, 15):
            matrix = np.zeros((15, 15))
            matrix[row, column] = 1 if row == column else 1 / np.sqrt(2)
            matrix[column, row] = matrix[row, column]
            directions.append(matrix)
    return np.array(directions)


def signed_energy_gradient(oracle, interaction, amplitudes, derivatives):
    hamiltonian = oracle.hamiltonian(CONSTRAINTS["orbital_energies"], interaction)[0]
    result = oracle.solve(hamiltonian, amplitudes, tolerance=2e-12, max_evaluations=250)
    _, left, _ = oracle.lambda_state(result)
    _, vectors = eigh(hamiltonian)
    exact = vectors[:, 0]
    gradient = np.einsum("i,kij,j->k", left, derivatives, result.right)
    gradient -= np.einsum("i,kij,j->k", exact, derivatives, exact)
    return gradient, result


def audit_source(source, label, random_count=512):
    started = time.monotonic()
    data = json.loads(source.read_text())
    oracle = DeterminantCC()
    interaction = np.array(data["pair_matrix"])
    amplitudes = np.array(data["amplitudes"])
    directions = basis_matrices()
    zero = oracle.hamiltonian(CONSTRAINTS["orbital_energies"], np.zeros((15, 15)))[0]
    derivatives = np.array([oracle.hamiltonian(CONSTRAINTS["orbital_energies"], direction)[0] - zero
                            for direction in directions])
    gradient, result = signed_energy_gradient(oracle, interaction, amplitudes, derivatives)
    gradient_norm = float(np.linalg.norm(gradient))
    coordinates = gradient / gradient_norm if gradient_norm > 1e-12 else np.eye(120)[0]
    adaptive = np.einsum("k,kij->ij", coordinates, directions)
    rng = np.random.default_rng(428173)
    records = []
    domain_rejections = 0

    def measure(direction, kind, sign=1):
        nonlocal domain_rejections
        point = interaction + sign * 0.001 * direction
        if np.max(abs(point)) > 1.5 or np.linalg.norm(point) > 7:
            domain_rejections += 1
            return None
        hamiltonian = oracle.hamiltonian(CONSTRAINTS["orbital_energies"], point)[0]
        solved = oracle.solve(hamiltonian, result.amplitudes, tolerance=2e-11, max_evaluations=250)
        diagnostic = oracle.diagnostics(hamiltonian, solved)
        failures = endpoint_failures(diagnostic)
        if diagnostic["occupation_violation"] < 0.02:
            failures.append("population_violation")
        record = {"kind": kind, "sign": sign, "radius": float(np.linalg.norm(point - interaction)),
                  "domain_valid": True, "failures": failures, "energy_error": diagnostic["energy_error"],
                  "signed_energy_error": diagnostic["cc_energy"] - diagnostic["fci_energy"],
                  "rdm_dad": diagnostic["rdm_dad"], "population_violation": diagnostic["occupation_violation"],
                  "ground_overlap": diagnostic["ground_overlap"]}
        records.append(record)
        return record

    for sign in (1, -1):
        measure(adaptive, "energy_gradient", sign)
    random_done = 0
    while random_done < random_count:
        coefficients = rng.normal(size=120)
        coefficients /= np.linalg.norm(coefficients)
        direction = np.einsum("k,kij->ij", coefficients, directions)
        if measure(direction, "isotropic") is not None:
            random_done += 1
    finite_difference = []
    for index in range(4):
        coefficients = coordinates if index == 0 else rng.normal(size=120)
        coefficients /= np.linalg.norm(coefficients)
        direction = np.einsum("k,kij->ij", coefficients, directions)
        values = []
        for sign in (1, -1):
            point = interaction + sign * 1e-5 * direction
            hamiltonian = oracle.hamiltonian(CONSTRAINTS["orbital_energies"], point)[0]
            solved = oracle.solve(hamiltonian, result.amplitudes, tolerance=2e-12, max_evaluations=250)
            values.append(solved.energy - eigh(hamiltonian, eigvals_only=True)[0])
        numerical = (values[0] - values[1]) / 2e-5
        analytic = float(gradient @ coefficients)
        finite_difference.append({"analytic": analytic, "finite_difference": numerical,
                                  "absolute_error": abs(analytic - numerical)})
    summary = {"label": label, "source": str(source), "source_is_completed": True,
               "radius": 0.001, "gradient_norm": gradient_norm,
               "largest_coordinate_slope": float(max(abs(gradient))),
               "domain_rejections_not_physics_failures": domain_rejections,
               "valid_probes": len(records), "isotropic_probes": random_count,
               "failure_clusters_valid_only": dict(Counter(failure for row in records for failure in row["failures"])),
               "adaptive_probes": [row for row in records if row["kind"] == "energy_gradient"],
               "isotropic_failed": sum(bool(row["failures"]) for row in records if row["kind"] == "isotropic"),
               "max_energy_error": max(row["energy_error"] for row in records),
               "max_dad": max(row["rdm_dad"] for row in records),
               "finite_difference_checks": finite_difference,
               "runtime_seconds": time.monotonic() - started}
    (PACKET / "authoring" / (label + "_combined_audit.json")).write_text(json.dumps({**summary, "probes": records}, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    audit_source(BASE / "champions/generation_3/submission.json", "completed_v3")
    audit_source(BASE / "adversary/generation_3/private_centered_candidate.json", "author_warm_start", random_count=128)
