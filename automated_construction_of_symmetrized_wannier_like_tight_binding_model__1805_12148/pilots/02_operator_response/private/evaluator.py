import argparse
import json
import math
from pathlib import Path
import sys
import tempfile
import time
import zipfile

import numpy as np


PILOT = Path(__file__).resolve().parents[1]
WEIGHTS = {
    "ham": 0.08, "connection": 0.26, "centers": 0.04, "energies": 0.02,
    "berry_raw": 0.18, "optical_raw": 0.18,
    "berry_repaired": 0.12, "optical_repaired": 0.12,
}
TOLERANCES = {
    "ham": 2e-8, "connection": 2e-8, "centers": 2e-8, "energies": 2e-8,
    "berry_raw": 2e-6, "optical_raw": 2e-6,
    "berry_repaired": 2e-6, "optical_repaired": 2e-6,
}
SCORING_VERSION = "post_audit_smooth_v1"
MAX_ARRAY_BYTES = 256 * 1024 ** 2


def load_npz(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_ARRAY_BYTES:
        raise ValueError("Missing or oversized output NPZ")
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) > 32 or sum(member.file_size for member in members) > 2 * MAX_ARRAY_BYTES:
            raise ValueError("Oversized NPZ contents")
        for member in members:
            if member.filename not in {name + ".npy" for name in ["rvec", *WEIGHTS, "lattice"]}:
                continue
            with archive.open(member) as stream:
                version = np.lib.format.read_magic(stream)
                if version == (1, 0):
                    shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
                elif version == (2, 0):
                    shape, _, dtype = np.lib.format.read_array_header_2_0(stream)
                else:
                    raise ValueError("Unsupported NPY format version")
                if dtype.hasobject or math.prod(shape) * dtype.itemsize > MAX_ARRAY_BYTES:
                    raise ValueError("Object or oversized array")
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in ["rvec", *WEIGHTS] if name in archive.files}


def relative_error(observed, expected):
    if observed.shape != expected.shape or observed.dtype.kind not in "biufc":
        raise ValueError("Incorrect shape or nonnumeric array")
    if not np.isfinite(observed).all():
        raise ValueError("Nonfinite array")
    denominator = max(float(np.linalg.norm(expected.ravel())), math.sqrt(expected.size) * 1e-12)
    return float(np.linalg.norm((observed - expected).ravel())) / denominator


def vector_lookup(vectors):
    if vectors.ndim != 2 or vectors.shape[1] != 3 or len(vectors) > 8192:
        raise ValueError("Incorrect real-space vector shape")
    if vectors.dtype.kind not in "biuf" or not np.isfinite(vectors).all():
        raise ValueError("Nonnumeric real-space vector")
    if not np.array_equal(vectors, np.rint(vectors)) or np.max(np.abs(vectors), initial=0) > 100000:
        raise ValueError("Noninteger or unbounded real-space vector")
    lookup = {tuple(int(component) for component in vector): index for index, vector in enumerate(vectors)}
    if len(lookup) != len(vectors):
        raise ValueError("Duplicate real-space vector")
    return lookup


def operator_error(observed, expected, observed_vectors, expected_vectors):
    lookup = vector_lookup(observed_vectors)
    expected_lookup = vector_lookup(expected_vectors)
    if observed.shape != (len(observed_vectors),) + expected.shape[1:]:
        raise ValueError("Incorrect operator shape")
    if observed.dtype.kind not in "biufc" or not np.isfinite(observed).all():
        raise ValueError("Nonfinite or nonnumeric operator")
    difference_squared = 0.0
    for vector, expected_index in expected_lookup.items():
        observed_index = lookup.get(vector)
        difference = expected[expected_index] if observed_index is None else observed[observed_index] - expected[expected_index]
        difference_squared += float(np.vdot(difference, difference).real)
    for vector in lookup.keys() - expected_lookup.keys():
        extra = observed[lookup[vector]]
        difference_squared += float(np.vdot(extra, extra).real)
    denominator = max(float(np.linalg.norm(expected.ravel())), math.sqrt(expected.size) * 1e-12)
    return math.sqrt(difference_squared) / denominator


def output_errors(observed, expected):
    errors, issues = {}, {}
    for name in WEIGHTS:
        try:
            if name in ["ham", "connection"]:
                errors[name] = operator_error(observed[name], expected[name], observed["rvec"], expected["rvec"])
            else:
                errors[name] = relative_error(observed[name], expected[name])
            if not math.isfinite(errors[name]):
                raise ValueError("Nonfinite numerical error")
        except (KeyError, ValueError, TypeError, OverflowError) as error:
            errors[name] = None
            issues[name] = str(error)
    return errors, issues


def component_quality(error, weak_error, tolerance):
    if error is None:
        return 0.0
    return 1 / (1 + 9 * error / max(weak_error, 100 * tolerance))


def score_from_errors(errors, weak_errors):
    quality, weak_quality, components = 0.0, 0.0, {}
    for name, weight in WEIGHTS.items():
        current = component_quality(errors[name], weak_errors[name], TOLERANCES[name])
        baseline = component_quality(weak_errors[name], weak_errors[name], TOLERANCES[name])
        quality += weight * current
        weak_quality += weight * baseline
        components[name] = current
    return {"score": quality, "errors": errors, "component_quality": components,
            "quality": quality, "weak_quality": weak_quality, "weak_errors": weak_errors}


def score_arrays(observed, expected, weak):
    errors, issues = output_errors(observed, expected)
    weak_errors, weak_issues = output_errors(weak, expected)
    if weak_issues:
        raise ValueError("Invalid private weak calibration: " + str(weak_issues))
    result = score_from_errors(errors, weak_errors)
    result["issues"] = issues
    return result


def summarize(cases, split, runtime):
    families, weak_families = {}, {}
    for case in cases:
        families.setdefault(case["family"], []).append(case["score"])
        weak_families.setdefault(case["family"], []).append(case["weak_quality"])
    family_scores = {name: float(np.mean(scores)) for name, scores in families.items()}
    weak_family_scores = {name: float(np.mean(scores)) for name, scores in weak_families.items()}
    return {
        "split": split, "core_score": float(np.mean(list(family_scores.values()))) if families else 0.0,
        "worst_family_score": min(family_scores.values(), default=0.0),
        "family_scores": family_scores, "cases": cases,
        "errors": [{"case": case["name"], "issues": case.get("issues", {})}
                   for case in cases if case.get("issues")],
        "runtime": {"wall_seconds": runtime,
                    "submission_seconds": sum(case.get("runtime", {}).get("seconds", 0.0) for case in cases)},
        "calibration": {"version": SCORING_VERSION, "weak": "stored public Hamiltonian-only workflow",
                        "weak_score": float(np.mean(list(weak_family_scores.values()))) if weak_family_scores else 0.0,
                        "weak_family_scores": weak_family_scores,
                        "exact_reference_score": 1.0, "weights": WEIGHTS, "relative_tolerances": TOLERANCES,
                        "formula": "q=1/(1+9*error/max(weak_error,100*tol)); score=sum(weight*q); invalid component q=0",
                        "tolerance_role": "scale floor only; no tolerance subtraction, clipping, or baseline normalization"},
    }


def evaluate(submission, split):
    sys.path.insert(0, str(PILOT.parent.parent / "authoring"))
    from sandbox_exec import run_submission

    entrypoint = Path(submission).resolve() / "solve.py"
    if not entrypoint.is_file():
        entrypoint = Path(submission).resolve() / "attempt/solve.py"
    if not entrypoint.is_file():
        raise ValueError("Submission directory must contain solve.py or attempt/solve.py")
    manifest = json.loads((PILOT / "private/reference/manifest.json").read_text())
    started = time.monotonic()
    cases = []
    for record in manifest["splits"][split]:
        expected = load_npz(PILOT / record["reference"])
        weak = load_npz(PILOT / record["weak_reference"])
        with tempfile.TemporaryDirectory(prefix=".eval-", dir=PILOT / "private/reference") as temporary:
            output_path = Path(temporary) / "result.npz"
            runtime = run_submission(entrypoint, PILOT / record["input"], output_path,
                                     PILOT / "participant", timeout=180, memory_gib=8)
            issues = {}
            try:
                if runtime["returncode"] != 0:
                    raise ValueError("Submission failed: " + runtime["log_tail"])
                observed = load_npz(output_path)
            except (ValueError, OSError, zipfile.BadZipFile, EOFError) as error:
                observed = {}
                issues["execution"] = str(error)
            result = score_arrays(observed, expected, weak)
            result["issues"].update(issues)
            result.update(name=record["name"], family=record["material"], runtime=runtime)
            cases.append(result)
    report = summarize(cases, split, time.monotonic() - started)
    report["isolation"] = "bwrap unshare-all; no private reference, other cases, authoring source, or network mounts"
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--split", choices=["test", "challenge", "confirmation"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    report = evaluate(arguments.submission, arguments.split)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    summary = {name: report[name] for name in ["core_score", "worst_family_score", "family_scores"]}
    summary["cases_with_errors"] = len(report["errors"])
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
