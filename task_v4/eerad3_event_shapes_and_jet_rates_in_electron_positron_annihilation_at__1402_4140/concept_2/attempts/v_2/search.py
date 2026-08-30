import argparse
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
from scipy.optimize import least_squares

ASSETS = Path(__file__).resolve().parents[2] / "participant"
sys.path.insert(0, str(ASSETS / "workspace"))
from shapes import SHAPE_NAMES, SIGNS, calculate, from_coordinates, invariants, random_event


def eligible(event, values):
    return (event[:, 0].min() >= 0.03 and invariants(event).min() >= 1e-4
            and values["y45"] >= 1e-4 and values["thrust_gap"] >= 1e-7
            and values["hemisphere_margin"] >= 1e-6
            and values["merge_gap"] >= 1e-8
            and values["pseudojet_norm"] >= 1e-8
            and values["hemisphere_occupancy"] >= 2)


def decode(coordinates):
    return [from_coordinates(block) for block in coordinates.reshape(2, 4, 3)]


def penalties(event, values):
    spatial = event[:, 1:]
    signed = SIGNS @ spatial
    norms = np.linalg.norm(signed, axis=1)
    axis = signed[np.argmax(norms)] / norms.max()
    projections = np.sort(spatial @ axis)
    return np.concatenate([
        10 * np.maximum(0.035 - event[:, 0], 0),
        10 * np.maximum(0.0002 - invariants(event), 0),
        10 * np.maximum(0.0001 - np.abs(projections), 0),
        [100 * max(0.0002 - values["y45"], 0),
         10 * max(projections[1] + 0.002, 0),
         10 * max(0.002 - projections[-2], 0),
         10 * max(0.00001 - values["thrust_gap"], 0),
         10 * max(0.000001 - values["merge_gap"], 0)],
    ])


def residual(coordinates, ratio):
    events = decode(coordinates)
    values = [calculate(event) for event in events]
    differences = [5 * (values[0][name] - values[1][name]) for name in SHAPE_NAMES]
    separation = 0.1 * (np.log(max(values[0]["y45"], 1e-20)
                                 / max(values[1]["y45"], 1e-20)) - np.log(ratio))
    return np.concatenate([differences, [separation],
                           penalties(events[0], values[0]),
                           penalties(events[1], values[1])])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("submission.json"))
    parser.add_argument("--seed", type=int, default=28082026)
    parser.add_argument("--seconds", type=float, default=1800)
    parser.add_argument("--ratio", type=float, default=4.0)
    args = parser.parse_args()
    started = time.monotonic()
    rng = np.random.default_rng(args.seed)
    pool = []
    while len(pool) < 300:
        event = random_event(rng)
        values = calculate(event)
        if eligible(event, values):
            pool.append((event, values))
    vectors = np.array([[values[name] for name in SHAPE_NAMES] for event, values in pool])
    contenders = []
    for first in range(len(pool)):
        for second in range(first):
            larger, smaller = (first, second) if pool[first][1]["y45"] > pool[second][1]["y45"] else (second, first)
            ratio = pool[larger][1]["y45"] / pool[smaller][1]["y45"]
            if ratio < 2:
                continue
            distance = np.linalg.norm(vectors[first] - vectors[second])
            score = distance + 0.03 * abs(np.log(ratio / args.ratio))
            contenders.append((score, larger, smaller))
    contenders.sort()
    best = np.inf
    print("Pool ready", len(pool), "pairs", len(contenders), flush=True)
    for attempt, (score, first, second) in enumerate(contenders):
        if time.monotonic() - started > args.seconds:
            break
        initial = np.array([pool[first][0][:4, 1:], pool[second][0][:4, 1:]]).ravel()
        solution = least_squares(residual, initial, args=(args.ratio,),
                                 max_nfev=400, ftol=1e-13, xtol=1e-13, gtol=1e-13)
        events = decode(solution.x)
        values = [calculate(event) for event in events]
        mismatch = max(abs(values[0][name] - values[1][name]) for name in SHAPE_NAMES)
        ratio = max(value["y45"] for value in values) / min(value["y45"] for value in values)
        valid = all(eligible(event, value) for event, value in zip(events, values))
        print(json.dumps({"attempt": attempt, "mismatch": mismatch, "ratio": ratio,
                          "valid": valid, "cost": solution.cost, "nfev": solution.nfev,
                          "seconds": time.monotonic() - started}), flush=True)
        quality = mismatch + max(3.1 - ratio, 0)
        if valid and quality < best:
            best = quality
            args.output.write_text(json.dumps({"events": [event.tolist() for event in events]}, indent=2) + "\n")
            print("Saved", args.output, flush=True)
        if valid and mismatch < 1e-10 and ratio > 3.1:
            print(json.dumps(values, indent=2), flush=True)
            return
    raise RuntimeError("No sufficiently accurate pair found within the search budget")


if __name__ == "__main__":
    main()
