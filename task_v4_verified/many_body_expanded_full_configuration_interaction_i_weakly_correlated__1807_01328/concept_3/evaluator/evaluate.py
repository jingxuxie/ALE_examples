"""Static-array evaluator; never imports or executes participant code."""

import argparse
import hashlib
import io
import json
import os
import resource
import stat
import time
import zipfile
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
HIDDEN = ROOT / "evaluator/hidden"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scores(target, prediction, family):
    error = prediction - target
    per_family = {str(int(value)): float(np.sqrt(np.mean(error[family == value] ** 2)))
                  for value in np.unique(family)}
    return {"core_score": float(np.sqrt(np.mean(error ** 2))),
            "worst_family_score": max(per_family.values()), "family_rmse": per_family,
            "mae": float(np.abs(error).mean()),
            "p95_absolute_error": float(np.quantile(np.abs(error), .95)),
            "max_absolute_error": float(np.abs(error).max())}


def read_prediction(path, expected_ids, maximum_bytes):
    path = Path(path)
    if path.suffix != ".npz":
        raise ValueError("submission must have .npz extension")
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError("symlink submission paths are not accepted")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as handle:
        metadata = os.fstat(handle.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > maximum_bytes:
            raise ValueError("submission must be a regular file within the byte limit")
        payload = handle.read(maximum_bytes + 1)
    if len(payload) > maximum_bytes:
        raise ValueError("submission byte limit exceeded")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = archive.infolist()
        if len(members) != 2 or {member.filename for member in members} != {"ids.npy", "tail.npy"}:
            raise ValueError("NPZ must contain exactly ids and tail, without duplicate members")
        if sum(member.file_size for member in members) > maximum_bytes:
            raise ValueError("uncompressed array byte limit exceeded")
    with np.load(io.BytesIO(payload), allow_pickle=False) as archive:
        ids, prediction = archive["ids"], archive["tail"]
    count = len(expected_ids)
    if ids.shape != (count,) or prediction.shape != (count,):
        raise ValueError(f"ids and tail must both have shape ({count},)")
    if ids.dtype.kind != "U" or ids.dtype.itemsize != 128:
        raise ValueError("ids must have NumPy Unicode dtype U32")
    if prediction.dtype.kind != "f" or prediction.dtype.itemsize not in (4, 8):
        raise ValueError("tail must have float32 or float64 dtype")
    if not np.isfinite(prediction).all():
        raise ValueError("tail must contain only finite real numbers")
    if len(np.unique(ids)) != count:
        raise ValueError("duplicate IDs")
    if set(ids.tolist()) != set(expected_ids.tolist()):
        raise ValueError("missing, extra, or unknown IDs")
    locations = {identifier: index for index, identifier in enumerate(ids.tolist())}
    aligned = prediction[[locations[identifier] for identifier in expected_ids.tolist()]].astype(np.float64)
    if np.max(np.abs(aligned)) > 1e6:
        raise ValueError("tail outside safe numerical range")
    return aligned


def evaluate(path):
    started = time.perf_counter()
    result = {"core_score": None, "worst_family_score": None, "valid": False,
              "passed": False, "reason": "uninitialized", "runtime_seconds": None,
              "resource": {"scope": "evaluator only; submission is static data",
                           "participant_runtime_seconds": None, "peak_rss_mib": None}}
    try:
        freeze = json.loads((HIDDEN / "target_freeze.json").read_text())
        for relative, expected in freeze["sha256"].items():
            if digest(ROOT / relative) != expected:
                raise RuntimeError(f"frozen artifact integrity mismatch: {relative}")
        with np.load(HIDDEN / "test_truth.npz", allow_pickle=False) as archive:
            ids, target, family = archive["ids"], archive["tail"], archive["family"]
        with np.load(HIDDEN / "baseline_predictions.npz", allow_pickle=False) as archive:
            if not np.array_equal(archive["ids"], ids):
                raise RuntimeError("baseline ID order mismatch")
            baseline = scores(target, archive["tail"], family)
        criteria = freeze["criteria"]
        prediction = read_prediction(path, ids, criteria["maximum_submission_bytes"])
        result.update(scores(target, prediction, family))
        limits = {"core_score": min(criteria["absolute_core_limit"],
                                     criteria["relative_core_limit"] * baseline["core_score"]),
                  "worst_family_score": min(criteria["absolute_worst_family_limit"],
                                             criteria["relative_worst_family_limit"] * baseline["worst_family_score"])}
        result["valid"] = True
        result["passed"] = all(result[key] <= limit for key, limit in limits.items())
        result["reason"] = "all_accuracy_targets_met" if result["passed"] else "accuracy_targets_not_met"
        result["limits"] = limits
        result["baseline"] = {key: baseline[key] for key in limits}
        result["n_predictions"] = len(prediction)
        result["energy_unit"] = "synthetic_Eh"
        result["target_version"] = criteria["version"]
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile, EOFError) as error:
        result["reason"] = f"invalid_submission: {type(error).__name__}: {error}"
    except RuntimeError as error:
        result["reason"] = f"evaluator_integrity_error: {error}"
    result["runtime_seconds"] = time.perf_counter() - started
    result["resource"]["peak_rss_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", nargs="?", type=Path)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    submission = args.predictions if args.predictions is not None else args.submission
    if submission is None:
        parser.error("provide predictions.npz, positionally or with --predictions")
    result = evaluate(submission)
    rendered = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
