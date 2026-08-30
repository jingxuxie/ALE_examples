import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import hashlib
import json
import math
from pathlib import Path
import signal
import time

import numpy as np

import audit


def main():
    started = time.monotonic()
    signal.signal(signal.SIGALRM, audit.timeout_handler)
    signal.alarm(180)
    if hasattr(os, "sched_getaffinity"):
        os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:4])
    witness_path = audit.ROOT / "champions/generation_1/witness.json"
    champion = json.loads(witness_path.read_text())
    official = json.loads((audit.ROOT / "attempts/v_1_run/score.json").read_text())
    audit.WITNESS = champion
    audit.ORDERED = audit.SPINS[:, champion["order"]]
    distance = np.count_nonzero(audit.SPINS != champion["pattern"], axis=1)
    audit.SECTOR = np.minimum(distance, 16 - distance) <= champion["radius"]
    weights = np.asarray(champion["weights"], dtype=float)
    bonds = np.asarray(champion["bonds"], dtype=float)
    energy = -(audit.FEATURES @ bonds)
    original = audit.proposal(weights)
    crosscheck = audit.evaluate(energy, champion["beta"], original)
    errors = {name: abs(crosscheck["metrics"][name] - official["metrics"][name]) for name in audit.GATES}
    assert max(errors.values()) < 1e-10
    crosscheck.update(audit.root_residual_correlation(original[0], crosscheck["metrics"]["entropy"]))
    crosscheck["absolute_differences_from_official"] = errors
    audit.save("champion_crosscheck.json", crosscheck)
    beta_rows = []
    floor_summary = []
    for floor in (1e-4, 3e-4, 1e-3, 3e-3, 1e-2):
        scaled = weights * math.log((1 - floor) / floor) / np.abs(weights).sum(axis=1).max()
        distribution = audit.proposal(scaled)
        probability, log_probability, residual = distribution
        centered_energy = energy - probability @ energy
        centered_log = log_probability - probability @ log_probability
        variance_energy = float(probability @ centered_energy ** 2)
        covariance = float(probability @ (centered_energy * centered_log))
        beta_minimum = float(np.clip(-covariance / variance_energy, 1.0, 3.0))
        exact_minimum = audit.evaluate(energy, beta_minimum, distribution)
        fixed_beta = audit.evaluate(energy, champion["beta"], distribution)
        passing = []
        for beta in np.linspace(1, 3, 41):
            report = audit.evaluate(energy, float(beta), distribution)
            report.update(floor=floor, beta=float(beta))
            beta_rows.append(report)
            if report["original_metric_gates_pass"]:
                passing.append(float(beta))
        floor_summary.append({"floor": floor, "at_champion_beta": fixed_beta,
                              "passing_beta_grid": passing, "continuous_variance_minimizer_beta": beta_minimum,
                              "continuous_minimum_variance": exact_minimum["metrics"]["reward_variance"],
                              "variance_quadratic_coefficients": [float(probability @ centered_log ** 2), 2 * covariance, variance_energy]})
    audit.save("champion_beta_profiles.json", beta_rows)
    audit.save("champion_floor_summary.json", floor_summary)
    free = [champion["order"][position] for position in range(1, 16) if not np.any(weights[position])]
    fixed = [site for site in range(16) if site not in free]
    relative = np.zeros(16)
    relative[champion["order"][0]] = 1
    for position, site in enumerate(champion["order"]):
        if position and site in fixed:
            assert np.count_nonzero(weights[position]) == 1 and weights[position, 0] != 0
            relative[site] = np.sign(weights[position, 0])
    generator = np.random.default_rng(202608281807)
    perturbations = []
    core = original[1] >= original[1].max() - 1e-10
    for amplitude in (0.001, 0.003, 0.01, 0.03, 0.1):
        for repetition in range(32):
            noise = generator.uniform(-1, 1, 32)
            noise -= noise.mean()
            noise /= np.max(np.abs(noise))
            perturbed = bonds * (1 + amplitude * noise)
            perturbed_energy = -(audit.FEATURES @ perturbed)
            coupling_matrix = np.zeros((16, 16))
            for coupling, (first, second) in zip(perturbed, audit.EDGES):
                coupling_matrix[first, second] = coupling
                coupling_matrix[second, first] = coupling
            adjusted = weights.copy()
            for position, site in enumerate(champion["order"]):
                if site in free:
                    adjusted[position, 0] = 2 * champion["beta"] * float(coupling_matrix[site] @ relative)
            perturbations.append({"amplitude": amplitude, "repetition": repetition,
                                  "bond_magnitudes": np.abs(perturbed).tolist(),
                                  "old_core_energy_range": float(np.ptp(perturbed_energy[core])),
                                  "ground_degeneracy_tolerance_1e_9": int(np.count_nonzero(np.abs(perturbed_energy - perturbed_energy.min()) < 1e-9)),
                                  "fixed_weights": audit.evaluate(perturbed_energy, champion["beta"], original),
                                  "analytic_floppy_field_adjustment": audit.evaluate(perturbed_energy, champion["beta"], audit.proposal(adjusted))})
    audit.save("champion_bond_perturbations.json", perturbations)
    summaries = []
    for amplitude in (0.001, 0.003, 0.01, 0.03, 0.1):
        rows = [row for row in perturbations if row["amplitude"] == amplitude]
        record = {"amplitude": amplitude, "trials": len(rows),
                  "ground_degeneracy_counts": sorted(set(row["ground_degeneracy_tolerance_1e_9"] for row in rows))}
        for mode in ("fixed_weights", "analytic_floppy_field_adjustment"):
            failures = {}
            for row in rows:
                for name in row[mode]["failed_metric_gates"]:
                    failures[name] = failures.get(name, 0) + 1
            record[mode] = {"all_metric_gates_pass": sum(row[mode]["original_metric_gates_pass"] for row in rows),
                            "failure_counts": failures,
                            "median_variance": float(np.median([row[mode]["metrics"]["reward_variance"] for row in rows])),
                            "median_gradient": float(np.median([row[mode]["metrics"]["gradient_infinity"] for row in rows]))}
        summaries.append(record)
    manifest = json.loads((audit.ROOT / "adversary/release_manifest.json").read_text())
    changed = [name for name, digest in manifest["sha256"].items() if hashlib.sha256((audit.ROOT / name).read_bytes()).hexdigest() != digest]
    summary = {"champion_sha256": hashlib.sha256(witness_path.read_bytes()).hexdigest(),
               "original_contract_still_passes": crosscheck["original_metric_gates_pass"],
               "maximum_crosscheck_error": max(errors.values()), "champion_beta": champion["beta"],
               "floors": floor_summary, "perturbations": summaries,
               "frozen_file_changes_relative_to_release": changed,
               "elapsed_seconds": time.monotonic() - started,
               "scope": "completed champion only; standalone exhaustive math; no fresh submissions or target edits"}
    audit.save("champion_summary.json", summary)
    print(json.dumps(summary, indent=2), flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
