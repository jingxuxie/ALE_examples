import os
import sys
import time

sys.dont_write_bytecode = True
START_CPU = 0.0
START_WALL = time.monotonic()
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
from pathlib import Path

from contractor import save_mps
from optimizer import optimize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    request = json.loads(Path(args.request).read_text())
    tensors = optimize(request, START_CPU, START_WALL)
    save_mps(args.output, tensors)


if __name__ == "__main__":
    main()
