import os
import sys

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "snapshots/teacher"))
sys.path.insert(0, str(ROOT / "snapshots/trusted"))
from trusted_contractor import load_mps, measure, save_mps
from refine import refine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", required=True)
    args = parser.parse_args()
    request = json.loads(Path(args.request).read_text())
    state = load_mps(args.seed, request)
    output = Path(args.output)
    started = time.process_time()
    wall_started = time.monotonic()

    def checkpoint(tensors, trajectory):
        checked = measure(tensors, request)
        save_mps(output, tensors)
        output.with_suffix(".trajectory.json").write_text(json.dumps(trajectory, indent=2) + "\n")
        print(json.dumps({"energy": checked["energy"], "phase": trajectory[-1]["phase"],
                          "cpu_seconds": time.process_time() - started,
                          "wall_seconds": time.monotonic() - wall_started}), flush=True)

    best, trajectory = refine(state, request, max(1, request["budget_seconds"] - time.process_time() - 2), 30, checkpoint)
    save_mps(output, best)
    output.with_suffix(".trajectory.json").write_text(json.dumps(trajectory, indent=2) + "\n")
    print(json.dumps(measure(load_mps(output, request), request)), flush=True)


if __name__ == "__main__":
    main()
