import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation", type=int, default=1)
    args = parser.parse_args()
    snapshot = ROOT / "adversary" / ("generation_" + str(args.generation) + "_snapshot")
    sys.path.insert(0, str(snapshot / "participant/workspace"))
    from api import CONSTRAINTS, screen
    from oracle import DeterminantCC
    output = ROOT / "adversary" / ("generation_" + str(args.generation) + "_stress")
    output.mkdir(exist_ok=True)
    generator = np.random.default_rng(87280681)
    oracle = DeterminantCC()
    summaries = []
    rows = []
    prefix = "v_" + str(args.generation)
    for label in [prefix, prefix + "_r2"]:
        artifact_path = ROOT / "attempts" / (label + "_frozen") / "submission.json"
        if not artifact_path.is_file():
            continue
        artifact = json.loads(artifact_path.read_text())
        pair = np.asarray(artifact["pair_matrix"])
        amplitudes = np.asarray(artifact["amplitudes"])
        diagnostics, solution = screen(pair, amplitudes, oracle)
        multipliers, left, stationarity = oracle.lambda_state(solution)
        density = oracle.rdm(left, solution.right)
        dad = float(np.linalg.norm(density - density.T, "fro") / math.sqrt(oracle.electrons))
        rotations = []
        probes = []
        for iteration in range(128):
            orthogonal, triangular = np.linalg.qr(generator.normal(size=(6, 6)))
            rotated = orthogonal.T @ density @ orthogonal
            rotations.append(float(np.linalg.norm(rotated - rotated.T, "fro") / math.sqrt(3)))
            orbital = generator.normal(size=6) + 1j * generator.normal(size=6)
            orbital /= np.linalg.norm(orbital)
            probes.append(float(abs(np.vdot(orbital, density @ orbital).imag)))
        failures = Counter()
        endpoint_passes = 0
        quiet = 0
        local_dad = []
        for radius in [1e-5, 1e-4, 1e-3, 3e-3, 1e-2, 3e-2]:
            for trial in range(64):
                direction = generator.normal(size=pair.shape)
                direction = (direction + direction.T) / 2
                direction /= np.linalg.norm(direction, "fro")
                unconstrained = (pair + pair.T) / 2 + radius * direction
                perturbed = np.clip(unconstrained, -CONSTRAINTS["pair_entry_max"], CONSTRAINTS["pair_entry_max"])
                pair_norm = np.linalg.norm(perturbed, "fro")
                if pair_norm > CONSTRAINTS["pair_frobenius_max"]:
                    perturbed *= CONSTRAINTS["pair_frobenius_max"] / pair_norm
                diagnostic, result = screen(perturbed, amplitudes, oracle)
                record = {"champion": label, "radius": radius, "trial": trial,
                          "actual_radius": float(np.linalg.norm(perturbed - pair, "fro")),
                          "domain_projected": bool(np.max(np.abs(perturbed - unconstrained)) > 1e-14),
                          "endpoint_feasible": bool(diagnostic["endpoint_feasible"]),
                          "failures": diagnostic["failures"]}
                failures.update(diagnostic["failures"])
                if result.converged:
                    multipliers, left, residual = oracle.lambda_state(result)
                    changed_density = oracle.rdm(left, result.right)
                    value = float(np.linalg.norm(changed_density - changed_density.T, "fro") / math.sqrt(3))
                    record.update({"dad": value, "occupation_violation": diagnostic["occupation_violation"],
                                   "energy_error": diagnostic["energy_error"]})
                    local_dad.append(value)
                    quiet += int(value <= 1e-3)
                endpoint_passes += int(record["endpoint_feasible"])
                rows.append(record)
        summaries.append({"champion": label, "base_violation": diagnostics["occupation_violation"],
                          "base_dad": dad, "orthogonal_basis_checks": len(rotations),
                          "basis_dad_min": min(rotations), "basis_dad_max": max(rotations),
                          "complex_orbital_probes": len(probes), "max_imaginary_population": max(probes),
                          "hamiltonian_perturbations": 384, "endpoint_passes": endpoint_passes,
                          "dad_min": min(local_dad), "dad_max": max(local_dad),
                          "dad_quiet_cases": quiet, "failure_clusters": dict(failures)})
    report = {"source_generation": args.generation,
              "root_cause": "substantial basis-invariant density non-Hermiticity" if args.generation == 1 else "sensitivity of the screened witness to integral perturbations",
              "proposed_next_screen": "DAD = Frobenius(gamma-gamma.T)/sqrt(3) <= 0.001" if args.generation == 1 else "all existing screens and population violation persist across a public integral-perturbation stencil",
              "remaining_witness_objective": "population violation >=0.02 with all original constraints",
              "perturbation_rule": "Symmetric Frobenius-normalized Gaussian directions, projected back into the original entry and Frobenius bounds; no out-of-domain case is scored as a method failure.",
              "summaries": summaries, "perturbations": rows,
              "qualification": "Endpoint perturbation screens are diagnostic, not passing continuation certificates."}
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
