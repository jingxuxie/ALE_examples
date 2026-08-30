import argparse
import hashlib
import json
import math
import os
import stat
import time
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent


def reject_constant(value):
    raise ValueError("Non-finite JSON literal: " + value)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def load_submission(path, expected_ids, max_bytes):
    path = Path(path)
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("Submission must be a self-contained regular JSON file; symlinks are not allowed")
    if metadata.st_size > max_bytes:
        raise ValueError("Submission exceeds the file-size limit")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError("Submission must be a regular JSON file")
        payload = handle.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError("Submission exceeds the file-size limit")
    document = json.loads(payload.decode("utf-8"), parse_constant=reject_constant,
                          object_pairs_hook=unique_object)
    if not isinstance(document, dict) or set(document) != {"ids", "p1"}:
        raise ValueError("Expected exactly the keys ids and p1")
    ids, probabilities = document["ids"], document["p1"]
    if not isinstance(ids, list) or not isinstance(probabilities, list):
        raise ValueError("ids and p1 must be flat arrays")
    if len(ids) != len(expected_ids) or len(probabilities) != len(expected_ids):
        raise ValueError("Prediction count does not match the complete query set")
    if any(type(identifier) is not int for identifier in ids):
        raise ValueError("IDs must be integers, not booleans or strings")
    if len(set(ids)) != len(ids) or set(ids) != set(expected_ids.tolist()):
        raise ValueError("Duplicate, missing, or extra query IDs")
    if any(type(value) not in (int, float) for value in probabilities):
        raise ValueError("Probabilities must be numbers, not booleans or nested values")
    if any(not math.isfinite(value) or value < 0. or value > 1. for value in probabilities):
        raise ValueError("Probabilities must be finite and in [0,1]")
    indices = {identifier: position for position, identifier in enumerate(ids)}
    return np.array([probabilities[indices[int(identifier)]] for identifier in expected_ids], dtype=float)


def score_predictions(predictions, labels, protocol, bootstrap=True):
    errors = (predictions - labels["p1"]) ** 2
    family_results = {}
    cell_results = {}
    family_scores = []
    bootstrap_results = {}
    generator = np.random.default_rng(4171)
    for family, target in protocol["family_rmse_max"].items():
        selected = labels["family"] == family
        family_errors = errors[selected]
        if not len(family_errors):
            raise ValueError("Evaluator has an empty family")
        mean_square = float(np.mean(family_errors))
        family_results[family] = math.sqrt(mean_square)
        family_scores.append(1. / (1. + mean_square / target ** 2))
        for device in np.unique(labels["device"]):
            cell = selected & (labels["device"] == device)
            if not np.any(cell):
                raise ValueError("Evaluator has an empty device/family cell")
            cell_results[f"device_{device}/{family}"] = float(np.sqrt(np.mean(errors[cell])))
        if bootstrap:
            draws = generator.integers(0, len(family_errors), size=(200, len(family_errors)))
            resamples = np.sqrt(np.mean(family_errors[draws], axis=1))
            bootstrap_results[family] = np.quantile(resamples, [0.025, 0.975]).tolist()
    macro_mse = float(np.mean(np.square(list(family_results.values()))))
    core_score = 1. / (1. + macro_mse / protocol["core_rmse_max"] ** 2)
    worst_score = float(min(family_scores))
    worst_cell = max(cell_results.values())
    passed = core_score >= 0.5 and worst_score >= 0.5 and worst_cell <= protocol["device_family_rmse_max"]
    clipped = np.clip(predictions, 1e-12, 1. - 1e-12)
    truth = labels["p1"]
    kl = truth * np.log(truth / clipped) + (1. - truth) * np.log((1. - truth) / (1. - clipped))
    failures = []
    if core_score < 0.5:
        failures.append("macro RMSE exceeds 0.020")
    if worst_score < 0.5:
        failures.append("at least one family RMSE exceeds 0.025")
    if worst_cell > protocol["device_family_rmse_max"]:
        failures.append("at least one device/family RMSE exceeds 0.040")
    return {
        "core_score": core_score,
        "worst_family_score": worst_score,
        "macro_rmse": math.sqrt(macro_mse),
        "family_rmse": family_results,
        "device_family_rmse": cell_results,
        "worst_device_family_rmse": worst_cell,
        "mean_bernoulli_kl": float(np.mean(kl)),
        "family_rmse_bootstrap_95pct": bootstrap_results,
        "passed": bool(passed),
        "valid": True,
        "reason": "All frozen predictive targets met" if passed else "; ".join(failures),
    }


def evaluate(submission):
    started = time.perf_counter()
    try:
        with (HERE / "hidden" / "protocol.json").open() as handle:
            protocol = json.load(handle)
        manifest_path = HERE / "hidden" / "integrity.json"
        if manifest_path.exists():
            integrity = json.loads(manifest_path.read_text())
            for name, digest in integrity.items():
                actual = hashlib.sha256((HERE / "hidden" / name).read_bytes()).hexdigest()
                if actual != digest:
                    raise RuntimeError("Private evaluator integrity check failed: " + name)
        with np.load(HERE / "hidden" / "truth.npz", allow_pickle=False) as archive:
            labels = {key: archive[key] for key in archive.files}
        predictions = load_submission(submission, labels["ids"], protocol["max_submission_bytes"])
        result = score_predictions(predictions, labels, protocol)
    except (OSError, ValueError, TypeError, OverflowError, RecursionError, UnicodeError) as error:
        result = {"core_score": 0., "worst_family_score": 0., "passed": False,
                  "valid": False, "reason": str(error)}
    result["runtime_seconds"] = time.perf_counter() - started
    result["runtime_scope"] = "static_validation_and_scoring_only"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    destination = arguments.output.resolve()
    if destination == arguments.submission.resolve() or HERE in destination.parents:
        parser.error("Output must not overwrite the submission or evaluator files")
    result = evaluate(arguments.submission)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    os.replace(temporary, destination)
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
