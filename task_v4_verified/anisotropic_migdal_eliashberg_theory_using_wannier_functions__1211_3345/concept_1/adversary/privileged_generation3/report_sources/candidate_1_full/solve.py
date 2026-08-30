import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import numpy as np
from operator_core import solve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    with np.load(arguments.input, allow_pickle=False) as archive:
        instance = {key: archive[key] for key in archive.files}
    delta, renormalization = solve(instance, exact_newton=False)
    np.savez(arguments.output, delta=delta, z=renormalization)


if __name__ == "__main__":
    main()
