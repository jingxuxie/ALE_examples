import os
import time

START_CPU = 0.0
START_WALL = time.monotonic()
for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import gc
import json
from pathlib import Path

from contractor import save_mps
from optimizer import optimize


def solve(request):
    return optimize(request, START_CPU, START_WALL)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    request = json.loads(Path(args.request).read_text())
    tensors = solve(request)
    gc.disable()
    if os.environ.get('MPS_DEBUG'):
        print('cpu_before_save', time.process_time(), flush=True)
    save_mps(args.output, tensors)
    if os.environ.get('MPS_DEBUG'):
        print('cpu_after_save', time.process_time(), flush=True)


if __name__ == "__main__":
    main()
    os._exit(0)
