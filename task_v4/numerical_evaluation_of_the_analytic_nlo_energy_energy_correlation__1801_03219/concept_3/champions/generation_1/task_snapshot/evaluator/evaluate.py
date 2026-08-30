#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import time


HIDDEN = Path(__file__).resolve().parent / "hidden"
MAX_BYTES = 16384
PAIR_COUNT = 512


class InvalidArtifact(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidArtifact("duplicate JSON key")
        result[key] = value
    return result


def integer_token(token):
    if len(token) > 8:
        raise InvalidArtifact("oversized integer token")
    return int(token)


def reject_constant(token):
    raise InvalidArtifact("non-finite JSON values are forbidden")


def read_artifact(submission):
    submitted = Path(submission)
    if submitted.is_symlink():
        raise InvalidArtifact("submission symlinks are forbidden")
    candidate = submitted / "design.json" if submitted.is_dir() else submitted
    if candidate.name != "design.json":
        raise InvalidArtifact("expected a directory or a file named design.json")
    directory_descriptor = os.open(candidate.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        descriptor = os.open(candidate.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=directory_descriptor)
    finally:
        os.close(directory_descriptor)
    with os.fdopen(descriptor, "rb") as stream:
        details = os.fstat(stream.fileno())
        if not stat.S_ISREG(details.st_mode):
            raise InvalidArtifact("design.json is not a regular file")
        if details.st_size > MAX_BYTES:
            raise InvalidArtifact("design.json exceeds the 16384-byte limit")
        payload = stream.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise InvalidArtifact("design.json exceeds the 16384-byte limit")
    design = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object,
                        parse_int=integer_token, parse_constant=reject_constant)
    return design, len(payload)


def load_target():
    manifest = json.loads((HIDDEN / "frozen_manifest.json").read_text(encoding="utf-8"))
    payload = (HIDDEN / "target.json").read_bytes()
    if hashlib.sha256(payload).hexdigest() != manifest["target_sha256"]:
        raise RuntimeError("frozen target digest mismatch")
    target = json.loads(payload.decode("utf-8"))
    expected_configuration = {
        "direction_count": 1024, "pair_count": PAIR_COUNT,
        "counts": {"0": 416, "1": 64, "2": 32}, "energy_integer_sum": 128,
        "min_empty_between_occupied": 1, "allowed_values": [0, 1, 2],
    }
    if any(target.get(key) != value for key, value in expected_configuration.items()):
        raise RuntimeError("unexpected frozen target configuration")
    correlations = target["cyclic_autocorrelation"]
    if len(correlations) != PAIR_COUNT or any(type(value) is not int or not 0 <= value <= 192
                                            for value in correlations):
        raise RuntimeError("invalid target autocorrelation")
    if correlations[0] != 192 or correlations[1] != 0 or sum(correlations) != 16384:
        raise RuntimeError("target sum rules failed")
    if any(correlations[lag] != correlations[-lag] for lag in range(PAIR_COUNT)):
        raise RuntimeError("target symmetry failed")
    return correlations, manifest["target_sha256"]


def validate_design(design):
    if type(design) is not dict or set(design) != {"schema_version", "a"}:
        raise InvalidArtifact("expected exactly schema_version and a")
    if type(design["schema_version"]) is not int or design["schema_version"] != 1:
        raise InvalidArtifact("schema_version must be the integer 1")
    values = design["a"]
    if type(values) is not list or len(values) != PAIR_COUNT:
        raise InvalidArtifact("a must be a length-512 array")
    counts = [0, 0, 0]
    for value in values:
        if type(value) is not int or value < 0 or value > 2:
            raise InvalidArtifact("a must contain only integer tokens 0, 1, 2")
        counts[value] += 1
    if counts != [416, 64, 32]:
        raise InvalidArtifact("wrong ternary counts; require 416/64/32")
    for slot, value in enumerate(values):
        if value and values[(slot + 1) % PAIR_COUNT]:
            raise InvalidArtifact("cyclic spacing violated")
    return values


def autocorrelation(values):
    correlations = [0] * PAIR_COUNT
    occupied = [(slot, value) for slot, value in enumerate(values) if value]
    for source, source_value in occupied:
        for destination, destination_value in occupied:
            correlations[(destination - source) % PAIR_COUNT] += source_value * destination_value
    return correlations


def evaluate(submission):
    started = time.perf_counter()
    report = {"core_score": 0.0, "worst_family_score": 0.0, "runtime_score": 0.0,
              "resource_score": 0.0, "valid": False, "passed": False, "reason": "",
              "submission_bytes": None, "max_submission_bytes": MAX_BYTES,
              "solver_runtime_observed": False, "configuration_error": False}
    try:
        target, digest = load_target()
        report["target_sha256"] = digest
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        report["configuration_error"] = True
        report["reason"] = "evaluator configuration error"
        report["runtime_seconds"] = time.perf_counter() - started
        return report
    try:
        design, byte_count = read_artifact(submission)
        report["submission_bytes"] = byte_count
        values = validate_design(design)
        observed = autocorrelation(values)
        differences = [actual - expected for actual, expected in zip(observed, target)]
        family_scores = {f"lags_{start}_{start + 127}": float(not any(differences[start:start + 128]))
                         for start in range(0, PAIR_COUNT, 128)}
        mismatches = [lag for lag, difference in enumerate(differences) if difference]
        passed = not mismatches
        report.update(valid=True, passed=passed, core_score=float(passed),
                      worst_family_score=min(family_scores.values()), runtime_score=1.0,
                      resource_score=1.0, family_scores=family_scores,
                      matched_lags=PAIR_COUNT - len(mismatches), mismatched_lags=len(mismatches),
                      l1_error=sum(abs(value) for value in differences),
                      squared_error=sum(value * value for value in differences),
                      max_abs_error=max(abs(value) for value in differences),
                      reason="exact full-domain EEC witness" if passed else "autocorrelation mismatch")
    except InvalidArtifact as error:
        report["reason"] = str(error)
    except (ValueError, UnicodeError, TypeError, RecursionError, OverflowError):
        report["reason"] = "malformed or unsupported JSON"
    except OSError:
        report["reason"] = "cannot read regular non-symlink design.json"
    report["runtime_seconds"] = time.perf_counter() - started
    return report


def main():
    parser = argparse.ArgumentParser(description="Grade static design.json without executing submitted code.")
    parser.add_argument("submission", help="submission directory or its design.json")
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    submitted = Path(arguments.submission)
    candidate = submitted / "design.json" if submitted.is_dir() else submitted
    if arguments.report and arguments.report.resolve() == candidate.resolve():
        parser.error("report must not overwrite design.json")
    report = evaluate(arguments.submission)
    serialized = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 2 if report["configuration_error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
