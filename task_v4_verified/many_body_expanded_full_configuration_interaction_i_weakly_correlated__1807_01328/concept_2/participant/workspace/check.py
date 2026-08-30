import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np

import assay
import model


def main():
    parser = argparse.ArgumentParser(description="Public diagnostic on independent training draws, not the hidden assay.")
    parser.add_argument("witness", nargs="?", type=Path, default=Path("witness.json"))
    parser.add_argument("--seed", type=int)
    parser.add_argument("--samples", type=int)
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    started = time.perf_counter()
    try:
        candidate = model.load_witness(arguments.witness)
        report = assay.evaluate(candidate, assay.training_uniforms(arguments.seed, arguments.samples))
    except (ValueError, TypeError, OSError, OverflowError, RecursionError, MemoryError, np.linalg.LinAlgError) as error:
        report = dict(valid=False, passed=False, core_score=0.0, worst_family_score=0.0, diagnostic_only=True, reason=str(error))
    report["runtime_seconds"] = time.perf_counter() - started
    serialized = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(serialized)
    print(serialized, end="")


if __name__ == "__main__":
    main()
