"""Weak NumPy-only random-pool / local-random-multistart inverse search."""

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from shapes import SHAPE_NAMES, calculate, from_coordinates, invariants, random_event


def eligible(event, values):
    return (event[:, 0].min() >= 0.03 and invariants(event).min() >= 1e-4
            and values["y45"] >= 1e-4 and values["thrust_gap"] >= 1e-7
            and values["hemisphere_margin"] >= 1e-6 and values["merge_gap"] >= 1e-8
            and values["pseudojet_norm"] >= 1e-8 and values["hemisphere_occupancy"] >= 2)


def utility(first, second):
    mismatch = max(abs(first[name] - second[name]) for name in SHAPE_NAMES)
    ratio = max(first["y45"], second["y45"]) / min(first["y45"], second["y45"])
    return min(1.0, 1e-7 / max(mismatch, 1e-300)) * min(1.0, (ratio - 1) / 2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260828)
    parser.add_argument("--samples", type=int, default=256)
    parser.add_argument("--steps", type=int, default=100)
    args = parser.parse_args()
    if args.samples < 2 or args.steps < 0:
        parser.error("samples >= 2 and steps >= 0 required")
    started = time.monotonic()
    rng = np.random.default_rng(args.seed)
    pool = []
    for unused in range(args.samples * 100):
        event = random_event(rng)
        values = calculate(event)
        if eligible(event, values):
            pool.append((event, values))
        if len(pool) == args.samples:
            break
    if len(pool) < 2:
        raise RuntimeError("could not sample two resolved events")
    contenders = []
    for first in range(len(pool)):
        for second in range(first):
            contenders.append((utility(pool[first][1], pool[second][1]), first, second))
    contenders.sort(reverse=True)
    best_score = -1.0
    best_events = None
    for score, first, second in contenders[:4]:
        events = [pool[first][0].copy(), pool[second][0].copy()]
        values = [pool[first][1], pool[second][1]]
        for step in range(args.steps):
            selected = int(rng.integers(2))
            scale = 0.02 * 0.03 ** (step / max(1, args.steps - 1))
            proposed = from_coordinates(events[selected][:4, 1:] + scale * rng.normal(size=(4, 3)))
            trial = calculate(proposed)
            trial_score = utility(trial, values[1 - selected])
            if eligible(proposed, trial) and trial_score > score:
                events[selected], values[selected], score = proposed, trial, trial_score
        if score > best_score:
            best_events, best_score = events, score
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"events": [event.tolist() for event in best_events]}, indent=2) + "\n")
    print(json.dumps({"seed": args.seed, "samples": len(pool), "local_starts": 4,
                      "public_estimated_core_score": best_score,
                      "generation_seconds": time.monotonic() - started}))


if __name__ == "__main__":
    main()
