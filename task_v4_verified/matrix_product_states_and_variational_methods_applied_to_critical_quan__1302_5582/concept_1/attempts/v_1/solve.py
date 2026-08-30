"""Budget-aware variational solver for the finite open-chain Hamiltonian."""

import time

WALL_START = time.monotonic()

import os

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
from pathlib import Path

from contractor import save_mps
from engine import optimize


def solve(request):
    return optimize(request, WALL_START)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    request = json.loads(Path(args.request).read_text())
    save_mps(args.output, solve(request))


if __name__ == "__main__":
    main()
