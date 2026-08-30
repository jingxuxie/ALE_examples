import argparse
import json
import os
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

from model import compute, load_witness, score


def main():
    parser = argparse.ArgumentParser(description="Diagnostic only: independently rechecked by the private evaluator.")
    parser.add_argument("witness", nargs="?", default="output/witness.json")
    parser.add_argument("--low-only", action="store_true")
    parser.add_argument("--details", action="store_true")
    arguments = parser.parse_args()
    started = time.perf_counter()
    try:
        metrics = compute(load_witness(arguments.witness), complete=not arguments.low_only)
        report = score(metrics)
        if not arguments.details:
            metrics = {key: value for key, value in metrics.items() if key not in ("subset_energies_eh", "increments_eh")}
        report["metrics"] = metrics
    except (ValueError, TypeError, OSError, OverflowError, RecursionError) as error:
        report = dict(valid=False, passed=False, core_score=0.0, reason=str(error))
    report["runtime_seconds"] = time.perf_counter() - started
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
