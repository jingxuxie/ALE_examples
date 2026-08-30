"""Independent full-Fock, analytic-limit, RDM and convergence checks."""

import json
import os
from pathlib import Path
import sys

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "participant/input"))

import numpy as np

from distribution import draw_instance
from exact import ground_state, label_instance, sector_matrix, spin_basis


def independent_fock(hopping, interaction, potential, up_count, down_count):
    n_sites = len(hopping)
    states = [state for state in range(1 << (2 * n_sites))
              if sum((state >> (2 * site)) & 1 for site in range(n_sites)) == up_count
              and sum((state >> (2 * site + 1)) & 1 for site in range(n_sites)) == down_count]
    lookup = {state: index for index, state in enumerate(states)}
    matrix = np.zeros((len(states), len(states)))
    for column, state in enumerate(states):
        for site in range(n_sites):
            up = (state >> (2 * site)) & 1
            down = (state >> (2 * site + 1)) & 1
            matrix[column, column] += interaction[site] * up * down + potential[site] * (up + down)
        for first in range(n_sites):
            for second in range(n_sites):
                if first == second or hopping[first, second] == 0:
                    continue
                for spin in range(2):
                    creation = 2 * first + spin
                    annihilation = 2 * second + spin
                    if not ((state >> annihilation) & 1) or ((state >> creation) & 1):
                        continue
                    sign = (-1) ** ((state & ((1 << annihilation) - 1)).bit_count())
                    intermediate = state ^ (1 << annihilation)
                    sign *= (-1) ** ((intermediate & ((1 << creation) - 1)).bit_count())
                    destination = intermediate | (1 << creation)
                    matrix[lookup[destination], column] -= hopping[first, second] * sign
    return matrix


def rdm_check(hopping, interaction, potential):
    n_sites = len(hopping)
    half = n_sites // 2
    matrix = sector_matrix(hopping, interaction, potential, half, half)
    energy, residual, vector = ground_state(matrix)
    states, occupations, transitions = spin_basis(n_sites, half)
    amplitudes = vector.reshape(len(states), len(states))
    probabilities = amplitudes ** 2
    up_weights = probabilities.sum(axis=1)
    down_weights = probabilities.sum(axis=0)
    density = up_weights @ occupations + down_weights @ occupations
    double = np.einsum("ab,ai,bi->i", probabilities, occupations, occupations)
    one_rdms = []
    for reduced, weights in ((amplitudes @ amplitudes.T, up_weights),
                             (amplitudes.T @ amplitudes, down_weights)):
        one_rdm = np.diag(weights @ occupations)
        for first, second, destinations, sources, signs in transitions:
            value = float(np.sum(reduced[sources, destinations] * signs)) / 2.0
            one_rdm[first, second] = value
            one_rdm[second, first] = value
        one_rdms.append(one_rdm)
    reconstructed = (-np.sum(hopping * (one_rdms[0] + one_rdms[1]))
                     + interaction @ double + potential @ density)
    step = 2e-4
    shifted = interaction.copy()
    shifted[0] += step
    plus = ground_state(sector_matrix(hopping, shifted, potential, half, half))[0]
    shifted[0] -= 2.0 * step
    minus = ground_state(sector_matrix(hopping, shifted, potential, half, half))[0]
    natural = np.concatenate([np.linalg.eigvalsh(one_rdm) for one_rdm in one_rdms])
    return {"energy_error": abs(float(reconstructed - energy)),
            "trace_error": abs(float(density.sum() - n_sites)),
            "hf_derivative_error": abs(float((plus - minus) / (2.0 * step) - double[0])),
            "natural_occupation_min": float(natural.min()),
            "natural_occupation_max": float(natural.max()), "residual": residual}


def main():
    rng = np.random.default_rng(421907)
    report = {"full_fock_max_error": 0.0, "dimer_max_error": 0.0,
              "noninteracting_max_error": 0.0, "atomic_max_error": 0.0,
              "permutation_max_error": 0.0, "restart_max_error": 0.0,
              "potential_shift_max_error": 0.0, "rdm_checks": []}
    hopping = rng.uniform(0.1, 1.3, (4, 4))
    hopping = (hopping + hopping.T) / 2.0
    np.fill_diagonal(hopping, 0.0)
    interaction = rng.uniform(2.0, 8.0, 4)
    potential = rng.normal(size=4)
    for up_count, down_count in ((2, 2), (2, 1), (3, 2), (3, 1), (0, 2)):
        independent = np.linalg.eigvalsh(independent_fock(hopping, interaction, potential,
                                                         up_count, down_count))
        production = np.linalg.eigvalsh(sector_matrix(hopping, interaction, potential,
                                                     up_count, down_count).toarray())
        report["full_fock_max_error"] = max(report["full_fock_max_error"],
                                             float(np.max(abs(independent - production))))
    for repulsion in (0.0, 2.0, 8.0, 20.0):
        tunneling = 0.83
        result = label_instance(np.array([[0.0, tunneling], [tunneling, 0.0]]),
                                np.full(2, repulsion), np.zeros(2))
        radical = np.sqrt(repulsion ** 2 + 16.0 * tunneling ** 2)
        analytic = np.array([radical - 2.0 * tunneling, (radical - repulsion) / 2.0])
        report["dimer_max_error"] = max(report["dimer_max_error"],
                                         float(np.max(abs(analytic - result["gaps"]))))
    for family in range(4):
        hopping, interaction, potential, _ = draw_instance(rng, family, 8)
        result = label_instance(hopping, interaction, potential)
        orbitals = np.linalg.eigvalsh(-hopping + np.diag(potential))
        free = label_instance(hopping, np.zeros(8), potential)
        report["noninteracting_max_error"] = max(report["noninteracting_max_error"],
            float(np.max(abs(free["gaps"] - (orbitals[4] - orbitals[3])))))
        permutation = rng.permutation(8)
        permuted = label_instance(hopping[np.ix_(permutation, permutation)],
                                  interaction[permutation], potential[permutation])
        restarted = label_instance(hopping, interaction, potential, seed=5551, tolerance=4e-13)
        shifted = label_instance(hopping, interaction, potential + 0.437)
        for name, alternate in (("permutation", permuted), ("restart", restarted),
                                ("potential_shift", shifted)):
            report[name + "_max_error"] = max(report[name + "_max_error"],
                float(np.max(abs(alternate["gaps"] - result["gaps"]))))
        report["rdm_checks"].append(rdm_check(hopping, interaction, potential))
    atomic = label_instance(np.zeros((4, 4)), np.full(4, 5.3), np.zeros(4))
    report["atomic_max_error"] = float(np.max(abs(atomic["gaps"] - [5.3, 0.0])))
    for family in range(4):
        hopping, interaction, potential, _ = draw_instance(rng, family, 10)
        first = label_instance(hopping, interaction, potential)
        second = label_instance(hopping, interaction, potential, seed=71913, tolerance=4e-13)
        report["restart_max_error"] = max(report["restart_max_error"],
                                            float(np.max(abs(first["gaps"] - second["gaps"]))))
    report["passed"] = all(value < 2e-8 for name, value in report.items() if name.endswith("max_error"))
    report["passed"] &= all(row["energy_error"] < 2e-8 and row["trace_error"] < 1e-10
                             and row["hf_derivative_error"] < 2e-7
                             and row["natural_occupation_min"] > -1e-9
                             and row["natural_occupation_max"] < 1.0 + 1e-9
                             for row in report["rdm_checks"])
    (ROOT / "evaluator/hidden/source_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
