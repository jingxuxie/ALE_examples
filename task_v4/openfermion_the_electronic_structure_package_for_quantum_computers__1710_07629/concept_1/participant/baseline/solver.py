import json
import sys
from pathlib import Path

import numpy as np


def cost(one_body, factors, orbital, auxiliary):
    rotated = np.einsum("pi,apq,qj->aij", orbital, factors, orbital, optimize=True)
    mixed = np.einsum("ab,bij->aij", auxiliary, rotated, optimize=True)
    weights = np.sum(np.abs(mixed), axis=(1, 2))
    return float(np.abs(orbital.T @ one_body @ orbital).sum() + 0.5 * weights @ weights)


def solve(case):
    one_body = np.asarray(case["one_body"], dtype=float)
    factors = np.asarray(case["factors"], dtype=float)
    dimension = len(one_body)
    rank = len(factors)
    gram = factors.reshape(rank, -1) @ factors.reshape(rank, -1).T
    auxiliary_candidates = [np.eye(rank), np.linalg.eigh(gram)[1].T]
    canonical = np.einsum("ab,bij->aij", auxiliary_candidates[1], factors)
    orbital_candidates = [np.eye(dimension), np.linalg.eigh(one_body)[1]]
    orbital_candidates.append(np.linalg.eigh(np.einsum("aij,ajk->ik", factors, factors))[1])
    orbital_candidates.extend(np.linalg.eigh(factor)[1] for factor in canonical)
    best_cost = float("inf")
    best = None
    for orbital in orbital_candidates:
        for auxiliary in auxiliary_candidates:
            candidate_cost = cost(one_body, factors, orbital, auxiliary)
            if candidate_cost < best_cost:
                best_cost = candidate_cost
                best = (orbital, auxiliary)
    return {"id": case["id"], "orbital": best[0].tolist(), "auxiliary": best[1].tolist()}


def main():
    request = json.loads(Path(sys.argv[1]).read_text())
    solutions = [solve(case) for case in request["cases"]]
    Path(sys.argv[2]).write_text(json.dumps({"solutions": solutions}, allow_nan=False))


if __name__ == "__main__":
    main()
