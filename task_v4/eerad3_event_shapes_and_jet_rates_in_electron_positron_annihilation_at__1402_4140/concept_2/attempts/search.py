"""Privileged generation-only SciPy search; never ship this with participant assets."""

import argparse
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
from scipy.optimize import least_squares


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from shapes import SHAPE_NAMES, calculate, from_coordinates, invariants


def residual(coordinates):
    events = [from_coordinates(block) for block in coordinates.reshape(2, 12)]
    values = [calculate(event) for event in events]
    difference = [values[0][name] - values[1][name] for name in SHAPE_NAMES]
    ratio = math.log(max(values[1]["y45"], 1e-16) / max(values[0]["y45"], 1e-16))
    penalties = [np.asarray(difference), [0.04 * (ratio - math.log(3.5))]]
    for event, value in zip(events, values):
        penalties.extend([
            3 * np.maximum(0.035 - event[:, 0], 0),
            10 * np.maximum(2e-4 - invariants(event), 0),
            [10 * max(2e-4 - value["y45"], 0)],
            [max(1e-5 - value["thrust_gap"], 0)],
            [max(1e-5 - value["hemisphere_margin"], 0)],
            [10 * max(1e-6 - value["merge_gap"], 0)],
        ])
    return np.concatenate(penalties)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=271828)
    parser.add_argument("--starts", type=int, default=24)
    parser.add_argument("--seconds", type=float, default=240)
    parser.add_argument("--output", type=Path, default=ROOT / "champions" / "witness.json")
    parser.add_argument("--log", type=Path, default=ROOT / "attempts" / "postfreeze_search.json")
    args = parser.parse_args()
    started = time.monotonic()
    rng = np.random.default_rng(args.seed)
    records = []
    best = float("inf")
    for attempt in range(args.starts):
        if time.monotonic() - started > args.seconds:
            break
        coordinates = rng.normal(size=(2, 4, 3))
        if attempt % 2 == 0:
            coordinates[1] = coordinates[0] + 0.2 * rng.normal(size=(4, 3))
        solution = least_squares(residual, coordinates.ravel(), max_nfev=350,
                                 ftol=1e-12, xtol=1e-12, gtol=1e-12)
        events = [from_coordinates(block) for block in solution.x.reshape(2, 12)]
        values = [calculate(event) for event in events]
        mismatch = max(abs(values[0][name] - values[1][name]) for name in SHAPE_NAMES)
        ratio = max(value["y45"] for value in values) / min(value["y45"] for value in values)
        merit = float(np.linalg.norm(solution.fun))
        record = {"attempt": attempt, "nfev": solution.nfev, "merit": merit,
                  "shape_error": mismatch, "ratio": ratio,
                  "energy_min": min(float(event[:, 0].min()) for event in events),
                  "sij_min": min(float(invariants(event).min()) for event in events),
                  "elapsed_seconds": time.monotonic() - started}
        records.append(record)
        print(json.dumps(record), flush=True)
        if merit < best:
            best = merit
            args.output.write_text(json.dumps({
                "events": [event.tolist() for event in events]}, indent=2) + "\n")
        args.log.write_text(json.dumps({
            "seed": args.seed, "target_ratio": 3.0, "internal_ratio_goal": 3.5,
            "attempts": records}, indent=2) + "\n")
        if mismatch < 5e-8 and ratio > 3.1 and merit < 1e-8:
            break


if __name__ == "__main__":
    main()
