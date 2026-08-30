#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import stat
import time


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
    if len(token) > 12:
        raise InvalidArtifact("oversized integer token")
    return int(token)


def reject_constant(token):
    raise InvalidArtifact("nonfinite JSON constant")


def validate_target(target):
    pair_count = target["pair_count"]
    counts = target["counts"]
    correlations = target["cyclic_autocorrelation"]
    if type(pair_count) is not int or pair_count < 4 or pair_count % 4:
        raise ValueError("invalid pair count")
    if target["direction_count"] != 2 * pair_count or target["min_empty_between_occupied"] != 1:
        raise ValueError("invalid event configuration")
    if set(counts) != {"0", "1", "2"} or any(type(value) is not int or value < 0 for value in counts.values()):
        raise ValueError("invalid target counts")
    if sum(counts.values()) != pair_count or 2 * (counts["1"] + counts["2"]) > pair_count:
        raise ValueError("infeasible counts")
    energy_sum = counts["1"] + 2 * counts["2"]
    if energy_sum <= 0 or energy_sum != target["energy_integer_sum"]:
        raise ValueError("invalid energy sum")
    diagonal = counts["1"] + 4 * counts["2"]
    if type(correlations) is not list or len(correlations) != pair_count:
        raise ValueError("target must cover every lag")
    if any(type(value) is not int or not 0 <= value <= diagonal for value in correlations):
        raise ValueError("invalid integer autocorrelation")
    if correlations[0] != diagonal or correlations[1] != 0 or sum(correlations) != energy_sum ** 2:
        raise ValueError("target sum rule failed")
    if any(correlations[lag] != correlations[-lag] for lag in range(pair_count)):
        raise ValueError("target symmetry failed")
    if type(target["max_submission_bytes"]) is not int or target["max_submission_bytes"] <= 0:
        raise ValueError("invalid byte cap")


def read_artifact(submission, byte_limit):
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
            raise InvalidArtifact("design.json must be a regular file")
        if details.st_size > byte_limit:
            raise InvalidArtifact("design.json exceeds the byte cap")
        payload = stream.read(byte_limit + 1)
    if len(payload) > byte_limit:
        raise InvalidArtifact("design.json exceeds the byte cap")
    design = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object,
                        parse_int=integer_token, parse_constant=reject_constant)
    return design, len(payload)


def validate_design(design, target):
    if type(design) is not dict or set(design) != {"schema_version", "a"}:
        raise InvalidArtifact("expected exactly schema_version and a")
    if type(design["schema_version"]) is not int or design["schema_version"] != 1:
        raise InvalidArtifact("schema_version must be the integer 1")
    values = design["a"]
    pair_count = target["pair_count"]
    if type(values) is not list or len(values) != pair_count:
        raise InvalidArtifact(f"a must contain exactly {pair_count} entries")
    counts = [0, 0, 0]
    for value in values:
        if type(value) is not int or value not in (0, 1, 2):
            raise InvalidArtifact("a entries must be integer tokens 0, 1, 2")
        counts[value] += 1
    if counts != [target["counts"][str(value)] for value in (0, 1, 2)]:
        raise InvalidArtifact("wrong ternary counts")
    if any(value and values[(slot + 1) % pair_count] for slot, value in enumerate(values)):
        raise InvalidArtifact("cyclic empty-neighbor constraint violated")
    return values


def autocorrelation(values):
    pair_count = len(values)
    result = [0] * pair_count
    occupied = [(slot, value) for slot, value in enumerate(values) if value]
    for source, source_value in occupied:
        for destination, destination_value in occupied:
            result[(destination - source) % pair_count] += source_value * destination_value
    return result


def score_correlation(observed, expected):
    if len(observed) != len(expected):
        raise ValueError("correlation length mismatch")
    differences = [actual - wanted for actual, wanted in zip(observed, expected)]
    width = len(expected) // 4
    families = {f"lags_{start}_{start + width - 1}": float(not any(differences[start:start + width]))
                for start in range(0, len(expected), width)}
    mismatched = sum(value != 0 for value in differences)
    absolute_error = sum(abs(value) for value in differences)
    return {"core_score": float(mismatched == 0), "worst_family_score": min(families.values()),
            "passed": mismatched == 0, "family_scores": families,
            "matched_lags": len(expected) - mismatched, "mismatched_lags": mismatched,
            "l1_error": absolute_error, "squared_error": sum(value * value for value in differences),
            "max_abs_error": max(abs(value) for value in differences),
            "eec_l1_error": absolute_error / sum(expected)}


def evaluate(submission, target):
    started = time.perf_counter()
    report = {"core_score": 0.0, "worst_family_score": 0.0, "runtime_score": 0.0,
              "resource_score": 0.0, "valid": False, "passed": False, "reason": "",
              "submission_bytes": None, "max_submission_bytes": target["max_submission_bytes"],
              "solver_runtime_observed": False, "configuration_error": False}
    try:
        design, byte_count = read_artifact(submission, target["max_submission_bytes"])
        report["submission_bytes"] = byte_count
        values = validate_design(design, target)
        report.update(score_correlation(autocorrelation(values), target["cyclic_autocorrelation"]))
        report.update(valid=True, runtime_score=1.0, resource_score=1.0,
                      reason="exact full-domain EEC witness" if report["passed"] else "autocorrelation mismatch")
    except InvalidArtifact as error:
        report["reason"] = str(error)
    except (ValueError, TypeError, RecursionError, OverflowError):
        report["reason"] = "malformed or unsupported JSON"
    except OSError:
        report["reason"] = "cannot read regular non-symlink design.json"
    report["runtime_seconds"] = time.perf_counter() - started
    return report


def emit_report(arguments, report, parser):
    submitted = Path(arguments.submission)
    candidate = submitted / "design.json" if submitted.is_dir() else submitted
    if arguments.report and arguments.report.resolve() == candidate.resolve():
        parser.error("report must not overwrite design.json")
    serialized = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(serialized, encoding="utf-8")
    print(serialized, end="")


def main():
    parser = argparse.ArgumentParser(description="Check static JSON, never execute submitted code.")
    parser.add_argument("submission")
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    target = json.loads((Path(__file__).resolve().parent / "input" / "target.json").read_text())
    validate_target(target)
    emit_report(arguments, evaluate(arguments.submission, target), parser)


if __name__ == "__main__":
    main()
