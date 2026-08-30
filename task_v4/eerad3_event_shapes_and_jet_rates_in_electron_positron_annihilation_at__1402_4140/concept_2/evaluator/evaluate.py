"""Verify a data-only witness without importing or executing participant code."""

import argparse
import itertools
import json
import math
from pathlib import Path
import sys
import time


sys.path.insert(0, str(Path(__file__).resolve().parent / "hidden"))
from trusted_shapes import NAMES, observables, physics, rotate


SHAPE_ATOL = 1e-7
RATIO_TARGET = 3.0
PHYSICAL_ATOL = 1e-10
INVARIANCE_ATOL = 2e-10
MAX_BYTES = 16384


def reject_constant(value):
    raise ValueError(f"nonfinite JSON constant: {value}")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_submission(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("submission exceeds 16384 bytes")
    payload = json.loads(raw.decode("utf-8"), parse_constant=reject_constant,
                         object_pairs_hook=unique_object)
    if not isinstance(payload, dict) or set(payload) != {"events"}:
        raise ValueError("root must contain exactly the key events")
    events = payload["events"]
    if not isinstance(events, list) or len(events) != 2:
        raise ValueError("events must contain exactly two events")
    for event in events:
        if not isinstance(event, list) or len(event) != 5:
            raise ValueError("each event must contain exactly five partons")
        for row in event:
            if not isinstance(row, list) or len(row) != 4:
                raise ValueError("each parton must be [E,px,py,pz]")
            if any(type(value) not in (int, float) or not math.isfinite(value)
                   or abs(value) > 1 + PHYSICAL_ATOL for value in row):
                raise ValueError("components must be finite numbers in [-1-1e-10,1+1e-10]")
    return events


def check_event(event):
    physical = physics(event)
    for name in ("energy_sum_error", "momentum_residual", "massless_error"):
        if physical[name] > PHYSICAL_ATOL:
            raise ValueError(f"{name} exceeds 1e-10")
    for name, lower in (("energy_min", 0.03), ("sij_min", 1e-4)):
        if physical[name] < lower:
            raise ValueError(f"{name} below {lower}")
    values = observables(event)
    if values["hemisphere_occupancy"] < 2:
        raise ValueError("each thrust hemisphere must contain at least two partons")
    for name, lower in (("y45", 1e-4), ("thrust_gap", 1e-7),
                        ("hemisphere_margin", 1e-6), ("merge_gap", 1e-8),
                        ("pseudojet_norm", 1e-8)):
        if values[name] < lower:
            raise ValueError(f"{name} below {lower}")
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError("nonfinite observable")
    return values, physical


def invariance_error(event, reference):
    maximum = 0.0
    count = 0
    keys = NAMES + ("y34", "y45")
    for permutation in itertools.permutations(range(5)):
        values = observables([event[index] for index in permutation])
        maximum = max(maximum, *(abs(values[key] - reference[key]) for key in keys))
        count += 1
    for quaternion in ((1, 2, 3, 4), (3, -1, 4, 2), (2, 5, -3, 1)):
        rotated = rotate(event, quaternion)
        physical = physics(rotated)
        if max(physical[key] for key in ("massless_error", "momentum_residual")) > PHYSICAL_ATOL:
            raise ValueError("rotation failed physical residual check")
        for permutation in (range(5), (2, 0, 4, 1, 3)):
            values = observables([rotated[index] for index in permutation])
            maximum = max(maximum, *(abs(values[key] - reference[key]) for key in keys))
            count += 1
    return maximum, count


def evaluate(path):
    started = time.perf_counter()
    result = {"core_score": 0.0, "worst_family_score": 0.0, "runtime_score": 1.0,
              "valid": False, "passed": False, "reason": "not evaluated"}
    try:
        events = read_submission(path)
        checked = [check_event(event) for event in events]
        values = [pair[0] for pair in checked]
        result["physics"] = [pair[1] for pair in checked]
        result["observables"] = values
        invariance = [invariance_error(event, value) for event, value in zip(events, values)]
        result["invariance_error"] = max(pair[0] for pair in invariance)
        result["invariance_checks"] = sum(pair[1] for pair in invariance)
        if result["invariance_error"] > INVARIANCE_ATOL:
            raise ValueError("permutation/rotation observable discrepancy exceeds 2e-10")
        result["valid"] = True
        errors = {name: abs(values[0][name] - values[1][name]) for name in NAMES}
        maximum = max(errors.values())
        ratio = max(value["y45"] for value in values) / min(value["y45"] for value in values)
        match_score = 1.0 if maximum <= SHAPE_ATOL else SHAPE_ATOL / maximum
        separation_score = min(1.0, max(0.0, (ratio - 1) / (RATIO_TARGET - 1)))
        result.update({"shape_errors": errors, "max_shape_error": maximum,
                       "y45_ratio": ratio, "core_score": match_score * separation_score,
                       "worst_family_score": min(match_score, separation_score),
                       "family_scores": {"physics": 1.0, "invariance": 1.0,
                                         "shape_match": match_score, "separation": separation_score},
                       "passed": maximum <= SHAPE_ATOL and ratio >= RATIO_TARGET})
        failures = []
        if maximum > SHAPE_ATOL:
            failures.append("six-shape absolute mismatch exceeds 1e-7")
        if ratio < RATIO_TARGET:
            failures.append("y45 ratio below 3")
        result["reason"] = "; ".join(failures) if failures else "certified resolved five-parton counterexample"
    except (ValueError, TypeError, OSError, OverflowError, ZeroDivisionError, RecursionError) as error:
        result.update({"valid": False, "passed": False, "core_score": 0.0,
                       "worst_family_score": 0.0, "reason": str(error)})
    result["evaluation_seconds"] = time.perf_counter() - started
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.submission)
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
