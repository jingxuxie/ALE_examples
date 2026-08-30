"""Exact rational sign certificate for one relaxed tuple, not the task domain."""

import json
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np

PACKET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKET / "participant" / "workspace"))
from oracle import DeterminantCC


def multiply(left, right):
    columns = list(zip(*right))
    return [[sum((first * second for first, second in zip(row, column) if first and second), Fraction(0))
             for column in columns] for row in left]


def dot(left, right):
    return sum((first * second for first, second in zip(left, right)), Fraction(0))


def main():
    started = time.monotonic()
    data = json.loads((PACKET / "authoring" / "relaxed_bounds_lower_best.json").read_text(), parse_float=Fraction)
    oracle = DeterminantCC()
    assert np.array_equal(oracle.generators, np.rint(oracle.generators))
    generators = oracle.generators.astype(int).tolist()
    cluster = [[sum((coefficient * generator[row][column] for coefficient, generator in zip(data["amplitudes"], generators)), Fraction(0))
                for column in range(20)] for row in range(20)]
    square = multiply(cluster, cluster)
    cube = multiply(square, cluster)
    fourth = multiply(cube, cluster)
    positive = [[Fraction(row == column) + cluster[row][column] + square[row][column] / 2 + cube[row][column] / 6
                 for column in range(20)] for row in range(20)]
    negative = [[Fraction(row == column) - cluster[row][column] + square[row][column] / 2 - cube[row][column] / 6
                 for column in range(20)] for row in range(20)]
    right = [row[oracle.reference] for row in positive]
    bra = [Fraction(index == oracle.reference) for index in range(20)]
    for index, multiplier in zip(oracle.targets, data["multipliers"]):
        bra[index] = multiplier
    left = [dot(bra, column) for column in zip(*negative)]
    normal = negative[-1]
    ground = data["ground_vector"]
    ground_norm = dot(ground, ground)
    overlap_right, overlap_left = dot(right, ground), dot(left, ground)
    coefficient_right = dot(right, right) - overlap_right * right[-1] / ground[-1]
    coefficient_left = dot(left, left) - overlap_left * dot(normal, left) / dot(normal, ground)
    gram_right = dot(right, right) - overlap_right ** 2 / ground_norm
    gram_left = dot(left, left) - overlap_left ** 2 / ground_norm
    checks = {"integer_generators": True, "fourth_cluster_power_zero": all(not entry for row in fourth for entry in row),
              "biorthogonal_normalization_exact": dot(left, right) == 1, "left_triple_exactly_zero": left[-1] == 0,
              "normal_right_exactly_zero": dot(normal, right) == 0,
              "ground_triple_nonzero": ground[-1] != 0, "normal_ground_nonzero": dot(normal, ground) != 0,
              "coefficient_right_strictly_negative": coefficient_right < 0,
              "coefficient_left_strictly_positive": coefficient_left > 0,
              "projected_right_norm_strictly_positive": gram_right > 0,
              "projected_left_norm_strictly_positive": gram_left > 0}
    quantities = {"B11": coefficient_right, "B22": coefficient_left, "G11": gram_right, "G22": gram_left}
    report = {"passed": all(checks.values()), "checks": checks,
              "exact_rational_quantities": {key: str(value) for key, value in quantities.items()},
              "decimal_approximations": {key: float(value) for key, value in quantities.items()},
              "scope": "exact exclusion of the one stored decimal-valued relaxed tuple under exact CCSD/lambda stationarity and a positive Hermitian ground gap",
              "proof": "Rayleigh positivity requires e*B11>0 and e*B22>0. Exact opposite coefficient signs make these inequalities incompatible for every real e. See OBSTRUCTION_NOTES.md for the stationary residual identity.",
              "universal_task_impossibility_proved": False, "runtime_seconds": time.monotonic() - started}
    (PACKET / "authoring" / "exact_relaxed_state_exclusion.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != "exact_rational_quantities"}, indent=2))


if __name__ == "__main__":
    main()
