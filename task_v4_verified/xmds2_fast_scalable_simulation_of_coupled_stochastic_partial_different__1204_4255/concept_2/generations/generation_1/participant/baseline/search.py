import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from simulator import DEFAULT, quick


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--trials", type=int, default=3)
    arguments = parser.parse_args()
    if not 1 <= arguments.trials <= 16:
        parser.error("trials must lie in [1,16]")
    generator = np.random.default_rng(19021)
    best = None
    best_gap = -1.0
    started = time.monotonic()
    for trial in range(arguments.trials):
        parameters = dict(DEFAULT)
        parameters.update({
            "dispersion": float(generator.uniform(0.37, 0.44)),
            "nonlinearity": float(generator.uniform(6.2, 7.2)),
            "duration": float(generator.uniform(0.55, 0.7)),
            "shift": float(generator.uniform(-1, 1)),
        })
        metrics = quick(parameters)
        if metrics["observable_gap"] > best_gap:
            best, best_gap = parameters, metrics["observable_gap"]
    destination = Path(arguments.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({"schema_version": 1, "parameters": best}, indent=2) + "\n")
    print(json.dumps({"submission": str(destination), "trials": arguments.trials, "screening_gap": best_gap, "runtime_seconds": time.monotonic() - started}, allow_nan=False))


if __name__ == "__main__":
    main()
