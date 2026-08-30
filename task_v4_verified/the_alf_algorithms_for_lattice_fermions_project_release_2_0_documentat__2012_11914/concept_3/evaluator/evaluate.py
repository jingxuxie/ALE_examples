"""Evaluate a submission without exposing hidden labels to its process."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/input"))
from runtime import ExecutionError, WALL_SECONDS, execute_submission
from scoring import score_prediction


MANIFEST_SHA256 = "8e405034f1ab12b88c609de33a84d0063d485e8993ef1aa45c2a906d6fd951bd"
CORE_MIN = 90.0
WORST_MIN = 85.0


def load(path):
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def verify_manifest():
    manifest_path = ROOT / "evaluator/hidden/split_manifest.json"
    contents = manifest_path.read_bytes()
    if hashlib.sha256(contents).hexdigest() != MANIFEST_SHA256:
        raise ValueError("fixed hidden split manifest integrity failure")
    manifest = json.loads(contents)
    heldout = next(split for split in manifest["splits"] if split["name"] == "heldout")
    for suffix in ("input", "labels"):
        path = ROOT / f"evaluator/hidden/heldout_{suffix}.npz"
        if hashlib.sha256(path.read_bytes()).hexdigest() != heldout[f"{suffix}_sha256"]:
            raise ValueError(f"fixed hidden {suffix} integrity failure")
    return heldout


def decision(scientific, runtime):
    reasons = []
    if scientific["core_score"] < CORE_MIN:
        reasons.append(f"core_score below {CORE_MIN:g}")
    if scientific["worst_family_score"] < WORST_MIN:
        reasons.append(f"worst_family_score below {WORST_MIN:g}")
    if runtime > WALL_SECONDS:
        reasons.append("wall time exceeded")
    return not reasons, "; ".join(reasons) if reasons else "meets all frozen thresholds"


def evaluate(submission):
    report = {
        "mode": "D_HIDDEN_PREDICTION",
        "valid": False,
        "passed": False,
        "core_score": 0.0,
        "worst_family_score": 0.0,
        "runtime": 0.0,
        "runtime_seconds": 0.0,
        "resource_score": 0.0,
        "reason": "not evaluated",
        "hidden_manifest_sha256": MANIFEST_SHA256,
        "thresholds": {"core_score": CORE_MIN, "worst_family_score": WORST_MIN},
    }
    try:
        heldout = verify_manifest()
        prediction, resources = execute_submission(
            submission,
            ROOT / "evaluator/hidden/heldout_input.npz",
            ROOT / "participant/input",
        )
        report.update(resources)
        report["runtime"] = resources["runtime_seconds"]
        report["resource_score"] = 100.0 * max(0.0, 1.0 - resources["runtime_seconds"] / WALL_SECONDS)
        inputs = load(ROOT / "evaluator/hidden/heldout_input.npz")
        if hashlib.sha256(inputs["sample_id"].tobytes()).hexdigest() != heldout["ordered_id_sha256"]:
            raise ValueError("fixed hidden row-order integrity failure")
        labels = load(ROOT / "evaluator/hidden/heldout_labels.npz")
        scientific = score_prediction(prediction, inputs, labels)
        report.update(scientific)
        report["valid"] = True
        report["passed"], report["reason"] = decision(scientific, resources["runtime_seconds"])
    except ExecutionError as error:
        report.update(error.details)
        report["runtime"] = error.runtime_seconds
        report["runtime_seconds"] = error.runtime_seconds
        report["reason"] = str(error)
    except Exception as error:
        report["reason"] = f"evaluation rejected: {type(error).__name__}: {error}"
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = evaluate(arguments.submission)
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
