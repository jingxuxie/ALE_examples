"""Weak baseline: one sweep, small active bond, final exact parity projection."""

import os

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
from pathlib import Path
import time

from contractor import save_mps
from mps import make_mpo, product_state, project_parity, sweep


def solve(request):
    start = time.process_time()
    constrained = request["sector"] != "any"
    cap = min(3, request["bond_cap"] // (2 if constrained else 1))
    tensors = product_state(request, tilt=0.12)
    tensors = sweep(tensors, make_mpo(request), cap, tolerance=3e-4, maxiter=24,
                    deadline=start + 0.6 * request["budget_seconds"])
    return project_parity(tensors, request["sector"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    request = json.loads(Path(args.request).read_text())
    save_mps(args.output, solve(request))


if __name__ == "__main__":
    main()
