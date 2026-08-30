"""Retest final code on a private fixture without mounting its labels."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
sys.dont_write_bytecode = True

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(ROOT / "participant/input"))
from runtime import execute_submission
from scoring import score_prediction


def load(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--fixture", type=Path, default=HERE / "confirmation_fixture")
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    manifest = json.loads((arguments.fixture / "manifest.json").read_text())
    for filename, expected in manifest["files_sha256"].items():
        actual = hashlib.sha256((arguments.fixture / filename).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("fixture integrity mismatch: " + filename)
    prediction, resources = execute_submission(
        arguments.submission,
        arguments.fixture / "input.npz",
        ROOT / "participant/input",
    )
    inputs = load(arguments.fixture / "input.npz")
    labels = load(arguments.fixture / "labels.npz")
    report = {
        **score_prediction(prediction, inputs, labels),
        **resources,
        "conditional_adversary_fixture": manifest,
        "not_official_score_or_pass_decision": True,
        "submission_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(arguments.submission.iterdir())
            if path.is_file() and (path.suffix == ".py" or path.name == "pool.npz")
        },
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2) + "\n")
    np.savez_compressed(arguments.output.with_suffix(".predictions.npz"), **prediction)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
