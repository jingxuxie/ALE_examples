import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.optimize import least_squares


ASSETS = Path(__file__).resolve().parents[2] / "participant"
sys.path.insert(0, str(ASSETS / "workspace"))
from shapes import SHAPE_NAMES, calculate, from_coordinates, invariants, random_event


SCALES = np.array([0.15, 0.5, 0.15, 0.2, 0.15, 0.15])
LEFT, RIGHT = np.triu_indices(5, 1)


def eligible(event, values):
    return (
        event[:, 0].min() >= 0.03
        and invariants(event).min() >= 1e-4
        and values["y45"] >= 1e-4
        and values["thrust_gap"] >= 1e-7
        and values["hemisphere_margin"] >= 1e-6
        and values["merge_gap"] >= 1e-8
        and values["pseudojet_norm"] >= 1e-8
        and values["hemisphere_occupancy"] >= 2
    )


def decode(coordinates):
    return [from_coordinates(coordinates[:12]), from_coordinates(coordinates[12:])]


def residual(coordinates, target_ratio):
    events = decode(coordinates)
    values = [calculate(event) for event in events]
    mismatch = np.array([values[0][name] - values[1][name] for name in SHAPE_NAMES])
    result = list(mismatch / SCALES)
    result.append(0.3 * np.log(values[0]["y45"] / values[1]["y45"] / target_ratio))
    for event, observables in zip(events, values):
        result.extend(10 * np.maximum(0.04 - event[:, 0], 0))
        result.extend(100 * np.maximum(0.0003 - invariants(event), 0))
        result.append(100 * max(0.0003 - observables["y45"], 0))
        pair_thrust = 2 * np.linalg.norm(event[LEFT, 1:] + event[RIGHT, 1:], axis=1).max()
        singleton_thrust = 2 * event[:, 0].max()
        result.append(10 * max(singleton_thrust + 0.002 - pair_thrust, 0))
        result.append(10 * max(1e-5 - observables["thrust_gap"], 0))
        result.append(10 * max(1e-4 - observables["hemisphere_margin"], 0))
        result.append(100 * max(1e-6 - observables["merge_gap"], 0))
    return np.array(result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("submission.json"))
    parser.add_argument("--seed", type=int, default=20260828)
    parser.add_argument("--starts", type=int, default=100)
    parser.add_argument("--ratio", type=float, default=4.5)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    started = time.monotonic()
    best_error = float("inf")
    for start in range(args.starts):
        events = []
        while len(events) < 2:
            event = random_event(rng)
            if eligible(event, calculate(event)):
                events.append(event)
        events.sort(key=lambda event: calculate(event)["y45"], reverse=True)
        initial = np.concatenate([event[:4, 1:].reshape(-1) for event in events])
        solution = least_squares(
            residual, initial, args=(args.ratio,), max_nfev=500,
            ftol=1e-12, xtol=1e-12, gtol=1e-12,
        )
        events = decode(solution.x)
        values = [calculate(event) for event in events]
        error = max(abs(values[0][name] - values[1][name]) for name in SHAPE_NAMES)
        ratio = max(value["y45"] for value in values) / min(value["y45"] for value in values)
        valid = all(eligible(event, value) for event, value in zip(events, values))
        print(json.dumps({"start": start, "nfev": solution.nfev, "cost": solution.cost,
                          "error": error, "ratio": ratio, "eligible": valid,
                          "seconds": time.monotonic() - started}), flush=True)
        if error < best_error and valid and ratio >= 3:
            best_error = error
            args.output.write_text(json.dumps({"events": [event.tolist() for event in events]}, indent=2) + "\n")
        if valid and error < 1e-9 and ratio >= 3.2:
            print(json.dumps({"observables": values}, indent=2), flush=True)
            return
    raise RuntimeError("No fully matching witness found")


if __name__ == "__main__":
    main()
