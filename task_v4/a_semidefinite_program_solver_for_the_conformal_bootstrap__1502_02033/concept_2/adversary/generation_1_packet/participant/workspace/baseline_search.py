"""Small coupled-branch search. Produces a candidate even when all screens reject."""

import os

for thread_variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[thread_variable] = "1"

import argparse
import json
import time
from fractions import Fraction
from pathlib import Path

import numpy as np
from numpy.polynomial import chebyshev as cheb

import guard


ROTATION_NUMERATORS = np.array([[1, -2, -2, -4], [2, 1, -4, 2], [2, 4, 1, -2], [4, -2, 2, 1]], dtype=np.int64)
QUANTUM = 10**9


def make_candidate(seed=0, order=4, depth=3e-7, gap=2e-6):
    random = np.random.default_rng(seed)
    point = Fraction(int(random.integers(300000, 700001)), 1000000)
    center = 2.0 * float(point) - 1.0
    neighbor = center + random.choice([-1.0, 1.0]) * random.uniform(1e-5, 2e-3)
    first = np.zeros(order + 1)
    first[-1] = 1.0
    first[0] = -cheb.chebval(center, first)
    second = np.zeros(order + 2)
    second[-1] = 1.0
    second[0] = -cheb.chebval(neighbor, second)
    first_square = cheb.chebmul(first, first) / 32.0
    first_square[0] -= depth
    second_square = cheb.chebmul(second, second) / 24.0
    second_square[0] += gap
    coupling = cheb.chebmul(first, second) / 48.0
    length = max(len(first_square), len(second_square), len(coupling))
    spectral = np.zeros((length, 4, 4))
    spectral[: len(first_square), 0, 0] = first_square
    spectral[: len(second_square), 1, 1] = second_square
    spectral[: len(coupling), 0, 1] = coupling
    spectral[: len(coupling), 1, 0] = coupling
    spectral[0, 2, 2] = 0.4
    spectral[1, 2, 2] = 1.0 / 64.0
    integer_spectral = np.rint(spectral * QUANTUM).astype(np.int64)
    for degree, matrix in enumerate(integer_spectral):
        matrix[3, 3] = (QUANTUM if degree == 0 else 0) - sum(int(matrix[diagonal, diagonal]) for diagonal in range(3))
    numerators = np.array([ROTATION_NUMERATORS @ matrix @ ROTATION_NUMERATORS.T for matrix in integer_spectral], dtype=np.int64)
    return {
        "schema_version": 1,
        "denominator": 25 * QUANTUM,
        "coefficients": numerators.tolist(),
        "x": str(point),
        "vector": [str(Fraction(int(entry), 5)) for entry in ROTATION_NUMERATORS[:, 0]],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="witness.json")
    parser.add_argument("--trials", type=int, default=4)
    parser.add_argument("--seed", type=int, default=1729)
    arguments = parser.parse_args()
    if not 1 <= arguments.trials <= 1000:
        parser.error("--trials must be 1..1000")
    start = time.process_time()
    best_document = None
    best_rank = (-1, float("-inf"))
    best_reports = None
    for trial in range(arguments.trials):
        order = [4, 7, 10, 11][trial % 4]
        document = make_candidate(arguments.seed + trial, order=order)
        coefficients = np.asarray(document["coefficients"], dtype=float) / document["denominator"]
        reports = guard.screen_all(coefficients)
        accepted = sum(item["accepted"] for item in reports)
        rank = (accepted, min(item.get("minimum_seen", float("-inf")) for item in reports))
        if best_document is None or rank > best_rank:
            best_document, best_rank, best_reports = document, rank, reports
        if accepted == len(guard.PROFILES):
            break
    Path(arguments.output).write_text(json.dumps(best_document, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"output": arguments.output, "trials": trial + 1, "profiles_accepted": best_rank[0], "guard_profiles": best_reports, "cpu_seconds": time.process_time() - start, "note": "Candidate only; exact admissibility and evidence are checked independently."}, allow_nan=False))


if __name__ == "__main__":
    main()
