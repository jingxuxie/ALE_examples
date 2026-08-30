import argparse
import json
import os
import time
from pathlib import Path

STARTED = time.monotonic()
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

from engine import solve
from fleet import load_fleet, objective


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    deadline = STARTED + 44.0
    manifest, cases = load_fleet(arguments.input)
    incumbent = solve(manifest, cases, trials=32, seed=710, diversify=False, deadline=deadline)
    incumbent_value = objective(cases, incumbent["cases"])
    destination = Path(arguments.output)
    destination.write_text(json.dumps(incumbent, allow_nan=False))
    if time.monotonic() + 2.0 < deadline:
        challenger = solve(manifest, cases, trials=256, seed=7714, diversify=True, deadline=deadline)
        if objective(cases, challenger["cases"]) < incumbent_value:
            incumbent = challenger
    destination.write_text(json.dumps(incumbent, allow_nan=False))


if __name__ == "__main__":
    main()
