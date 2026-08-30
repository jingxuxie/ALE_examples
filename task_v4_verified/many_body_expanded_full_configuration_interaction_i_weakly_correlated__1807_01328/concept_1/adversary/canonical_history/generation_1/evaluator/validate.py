import itertools
import json
import sys
from pathlib import Path

import numpy as np
from scipy.linalg import eigh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from pair_model import CASOracle, FAMILIES, increments, sample_model


def independent_energy(model, mask):
    sites = list(range(3)) + [orbital + 3 for orbital in range(8) if mask & (1 << orbital)]
    states = [frozenset(configuration) for configuration in itertools.combinations(sites, 3)]
    orbital_energy = np.asarray(model["orbital_energy"])
    density = np.asarray(model["density"])
    hopping = np.asarray(model["hopping"])
    matrix = np.zeros((len(states), len(states)))
    for row, state in enumerate(states):
        matrix[row, row] = sum(orbital_energy[site] for site in state)
        matrix[row, row] += sum(density[first, second] for first, second in itertools.combinations(sorted(state), 2))
        for column in range(row):
            removed = state - states[column]
            inserted = states[column] - state
            if len(removed) == 1 and len(inserted) == 1:
                matrix[row, column] = matrix[column, row] = hopping[next(iter(removed)), next(iter(inserted))]
    reference = sum(orbital_energy[:3]) + density[0, 1] + density[0, 2] + density[1, 2]
    return float(np.linalg.eigvalsh(matrix)[0] - reference)


def main():
    maximum_error = 0.0
    maximum_residual = 0.0
    checks = 0
    for index, family in enumerate(FAMILIES):
        model = sample_model(91512 + index, family)
        oracle = CASOracle(model)
        table = oracle.all_energies()
        spectrum = oracle.spectrum()
        assert spectrum["reference_weight"] >= 0.94
        assert spectrum["gap"] >= 0.35
        maximum_residual = max(maximum_residual, spectrum["residual"])
        assert spectrum["residual"] < 1e-11
        for mask in (0, 1, 7, 31, 63, 127, 255):
            discrepancy = abs(table[mask] - independent_energy(model, mask))
            maximum_error = max(maximum_error, discrepancy)
            assert discrepancy < 1e-11
            checks += 1
        assert abs(sum(increments(table)) - table[-1]) < 1e-11
        for mask in range(256):
            for orbital in range(8):
                assert table[mask | (1 << orbital)] <= table[mask] + 1e-11
        permutation = np.r_[np.arange(3), np.arange(10, 2, -1)]
        permuted = {"family": family,
                    "orbital_energy": np.asarray(model["orbital_energy"])[permutation].tolist(),
                    "density": np.asarray(model["density"])[np.ix_(permutation, permutation)].tolist(),
                    "hopping": np.asarray(model["hopping"])[np.ix_(permutation, permutation)].tolist()}
        other = CASOracle(permuted).all_energies()
        for mask in range(256):
            reversed_mask = int(f"{mask:08b}"[::-1], 2)
            assert abs(table[mask] - other[reversed_mask]) < 1e-11
    public = np.load(ROOT / "participant/input/practice.npz")["energies"]
    hidden = np.load(ROOT / "evaluator/hidden/cases.npz")["energies"]
    assert np.isfinite(public).all() and np.isfinite(hidden).all()
    assert not any(np.array_equal(first, second) for first in public for second in hidden)
    report = {"valid": True, "independent_diagonalizations": checks,
              "maximum_independent_discrepancy": maximum_error,
              "maximum_eigenpair_residual": maximum_residual,
              "tests": ["independent dense eigensolver", "gap and reference admissibility",
                        "CAS variational nesting", "Mobius reconstruction",
                        "virtual permutation covariance", "finite and disjoint heldout data"]}
    (ROOT / "evaluator/hidden/validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
