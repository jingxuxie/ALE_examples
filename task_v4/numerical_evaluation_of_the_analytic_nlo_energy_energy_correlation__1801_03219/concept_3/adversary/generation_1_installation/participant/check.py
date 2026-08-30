#!/usr/bin/env python3
import argparse
import json
import math
import os
from pathlib import Path
import stat
import time


MAX_BYTES = 16384
PAIR_COUNT = 512


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("non-finite JSON value")


def read_design(submission):
    submitted = Path(submission)
    if submitted.is_symlink():
        raise ValueError("submission symlinks are forbidden")
    candidate = submitted / "design.json" if submitted.is_dir() else submitted
    if candidate.name != "design.json":
        raise ValueError("expected a directory or a file named design.json")
    directory_descriptor = os.open(candidate.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        descriptor = os.open(candidate.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory_descriptor)
    finally:
        os.close(directory_descriptor)
    with os.fdopen(descriptor, "rb") as stream:
        details = os.fstat(stream.fileno())
        if not stat.S_ISREG(details.st_mode):
            raise ValueError("design.json must be a regular file")
        if details.st_size > MAX_BYTES:
            raise ValueError("design.json exceeds 16384 bytes")
        payload = stream.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("design.json exceeds 16384 bytes")
    design = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object,
                        parse_constant=reject_constant)
    return design, len(payload)


def validate(design):
    if type(design) is not dict or set(design) != {"schema_version", "a"}:
        raise ValueError("expected exactly schema_version and a")
    if type(design["schema_version"]) is not int or design["schema_version"] != 1:
        raise ValueError("schema_version must be the integer 1")
    values = design["a"]
    if type(values) is not list or len(values) != PAIR_COUNT:
        raise ValueError("a must contain exactly 512 entries")
    if any(type(value) is not int or value not in (0, 1, 2) for value in values):
        raise ValueError("a entries must be integer tokens 0, 1, or 2")
    if [values.count(value) for value in (0, 1, 2)] != [416, 64, 32]:
        raise ValueError("required counts are 416 zeros, 64 ones, 32 twos")
    if any(values[slot] and values[(slot + 1) % PAIR_COUNT] for slot in range(PAIR_COUNT)):
        raise ValueError("occupied pair slots must be separated cyclically")
    return values


def evaluate(submission, target_path=None):
    started = time.perf_counter()
    report = {"core_score": 0.0, "worst_family_score": 0.0, "runtime_score": 0.0,
              "resource_score": 0.0, "valid": False, "passed": False, "reason": "",
              "submission_bytes": None}
    try:
        target_file = target_path or Path(__file__).parent / "input" / "target.json"
        target = json.loads(Path(target_file).read_text(encoding="utf-8"))["cyclic_autocorrelation"]
        design, byte_count = read_design(submission)
        report["submission_bytes"] = byte_count
        values = validate(design)
        observed = [sum(value * values[(slot + lag) % PAIR_COUNT]
                        for slot, value in enumerate(values)) for lag in range(PAIR_COUNT)]
        differences = [actual - expected for actual, expected in zip(observed, target)]
        family_scores = {f"lags_{start}_{start + 127}": float(not any(differences[start:start + 128]))
                         for start in range(0, PAIR_COUNT, 128)}
        passed = not any(differences)
        report.update(valid=True, passed=passed, core_score=float(passed),
                      worst_family_score=min(family_scores.values()), runtime_score=1.0,
                      resource_score=1.0, family_scores=family_scores,
                      matched_lags=sum(value == 0 for value in differences),
                      l1_error=sum(abs(value) for value in differences),
                      squared_error=sum(value * value for value in differences),
                      max_abs_error=max(abs(value) for value in differences),
                      reason="exact full-domain EEC witness" if passed else "autocorrelation mismatch")
    except (ValueError, OSError, TypeError, KeyError, RecursionError, OverflowError):
        report["reason"] = "invalid artifact or unreadable local target"
    report["runtime_seconds"] = time.perf_counter() - started
    if not math.isfinite(report["runtime_seconds"]):
        raise RuntimeError("non-finite runtime")
    return report


def main():
    parser = argparse.ArgumentParser(description="Check a static inverse-EEC witness; never execute it.")
    parser.add_argument("submission")
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    submitted = Path(arguments.submission)
    candidate = submitted / "design.json" if submitted.is_dir() else submitted
    if arguments.report and arguments.report.resolve() == candidate.resolve():
        parser.error("report must not overwrite design.json")
    report = evaluate(arguments.submission)
    output = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
