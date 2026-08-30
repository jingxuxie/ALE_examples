import importlib.util
import itertools
import json
from pathlib import Path
import time

import numpy as np
from numpy.polynomial import chebyshev as cheb


ROOT = Path(__file__).resolve().parents[1]


def load(filename, name):
    specification = importlib.util.spec_from_file_location(name, filename)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


ARCHIVE = ROOT / "adversary" / "generation_1_packet" / "evaluator"
SOURCE = ARCHIVE if ARCHIVE.is_dir() else ROOT / "evaluator"
ORIGINAL = load(SOURCE / "_frozen_guard.py", "original")
ENHANCED = load(SOURCE / "_frozen_guard.py", "enhanced")
CHECKER = load(ROOT / "evaluator" / "exact_checker.py", "checker")


def all_minor_candidates(coefficients):
    result = []
    for size in range(1, 5):
        for subset in itertools.combinations(range(4), size):
            determinant = np.zeros(size * (len(coefficients) - 1) + 1)
            for permutation in itertools.permutations(range(size)):
                inversions = sum(permutation[left] > permutation[right]
                                 for left in range(size) for right in range(left + 1, size))
                product = np.array([1.0])
                for row, column in enumerate(permutation):
                    product = cheb.chebmul(product, coefficients[:, subset[row], subset[column]])
                determinant[:len(product)] += (-1.0 if inversions % 2 else 1.0) * product
            result.extend(ORIGINAL._root_projections(determinant))
            result.extend(ORIGINAL._root_projections(cheb.chebder(determinant)))
    candidates = np.asarray(result)
    if len(candidates):
        candidates = np.clip(np.concatenate((candidates, candidates - 2e-7, candidates + 2e-7)), 0, 1)
    return np.unique(candidates)


ENHANCED.determinant_candidates = all_minor_candidates


def main():
    started = time.monotonic()
    witness = json.loads((ROOT / "attempts" / "v_1" / "witness.json").read_text())
    negative_direction = [1, 2, 2, 4]
    null_direction = [-2, 1, 4, -2]
    coefficients = witness["coefficients"]
    assert all(sum(matrix[row][column] * null_direction[column] for column in range(4)) == 0
               for matrix in coefficients for row in range(4))
    permutations = list(itertools.permutations(range(4)))[::4]
    signs = [(1, 1, 1, 1), (1, -1, 1, 1), (1, 1, -1, 1), (1, 1, 1, -1)]
    results = []
    for lifting in [0, 1, 10, 100, 1000, 10000, 100000]:
        for permutation, sign in itertools.product(permutations, signs):
            lifted = np.asarray(coefficients, dtype=np.int64).copy()
            for row in range(4):
                for column in range(4):
                    lifted[0, row, column] += lifting * (null_direction[row] * null_direction[column]
                                                       - negative_direction[row] * negative_direction[column])
            transformed = [[[int(sign[row] * sign[column] * matrix[permutation[row], permutation[column]])
                             for column in range(4)] for row in range(4)] for matrix in lifted]
            candidate = dict(witness, coefficients=transformed,
                             vector=[str(sign[index] * negative_direction[permutation[index]]) + "/5" for index in range(4)])
            checked = CHECKER.check_document(candidate)
            assert checked["evidence_valid"]
            numeric = np.asarray(candidate["coefficients"], dtype=float) / candidate["denominator"]
            old = ORIGINAL.screen_all(numeric)
            new = ENHANCED.screen_all(numeric)
            results.append({"lifting_index": lifting, "lift_eigenvalue": 25 * lifting / candidate["denominator"],
                            "permutation": permutation, "signs": sign, "admissible": True,
                            "original_profiles_accepted": sum(entry["accepted"] for entry in old),
                            "enhanced_profiles_accepted": sum(entry["accepted"] for entry in new),
                            "enhanced_minimum_seen": min(entry.get("minimum_seen", 0) for entry in new),
                            "witness": candidate})
        print(json.dumps({"lifting_index": lifting, "completed": len(results)}), flush=True)
    summary = {"cases": len(results), "all_admissible": True,
               "original_successes": sum(entry["original_profiles_accepted"] == 3 for entry in results),
               "enhanced_successes": sum(entry["enhanced_profiles_accepted"] == 3 for entry in results),
               "common_nullspace_verified_exactly": True,
               "root_cause": "flat smallest eigenbranch and identically zero or near-degenerate full determinant; a separate quartic basin attracts the secondary probes",
               "repair": "root and stationary candidates from every principal minor, not just the full determinant",
               "wall_seconds": time.monotonic() - started, "results": results}
    (ROOT / "adversary" / "generation_1_challenge_search.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2))


if __name__ == "__main__":
    main()
