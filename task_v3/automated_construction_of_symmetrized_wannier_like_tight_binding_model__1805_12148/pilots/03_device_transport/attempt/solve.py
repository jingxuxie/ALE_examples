#!/usr/bin/env python3
"""Sparse, coherent transport through finite full-hopping Wannier devices."""

import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                 "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse

import numpy as np

from transport import solve_transport


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as archive:
        case = {name: archive[name] for name in archive.files}
    result = solve_transport(case)
    np.savez_compressed(arguments.output, **result)


if __name__ == "__main__":
    main()
