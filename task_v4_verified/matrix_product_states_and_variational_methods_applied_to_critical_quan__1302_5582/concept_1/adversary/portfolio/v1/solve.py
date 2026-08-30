"""Standalone general private portfolio candidate; no instance lookup."""

import os
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS",
                 "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
from pathlib import Path

from contractor import save_mps
from engine import optimize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    request = json.loads(Path(args.request).read_text())
    tensors, history = optimize(request)
    save_mps(args.output, tensors)
    print(json.dumps({"trajectory": history}, allow_nan=False))


if __name__ == "__main__":
    main()
