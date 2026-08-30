"""Exercise OUTPUT_DIR copies, public CLI scoring, and site covariance."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np

from evaluate import INPUT_KEYS, ROOT
from scoring import parse_predictions


def command(*arguments):
    subprocess.run([sys.executable, "-B", *map(str, arguments)], check=True, timeout=120)


def main():
    participant = ROOT / "participant"
    output = ROOT / "attempts/public_workflow"
    submission = output / "submission"
    submission.mkdir(parents=True, exist_ok=True)
    for filename in ("solver.py", "features.py", "model.npz"):
        shutil.copyfile(participant / "baseline" / filename, submission / filename)
    original = output / "original"
    permuted = output / "permuted"
    command(participant / "make_request.py", participant / "input/validation.npz", original)
    command(submission / "solver.py", original / "request.json", original / "predictions.json")
    command(participant / "score.py", participant / "input/validation.npz", original / "predictions.json",
            "--report", output / "public_score.json")
    with np.load(original / "inputs.npz", allow_pickle=False) as archive:
        inputs = dict(archive)
    assert set(inputs) == set(INPUT_KEYS)
    generator = np.random.default_rng(66241)
    for index, size in enumerate(inputs["n_sites"]):
        permutation = generator.permutation(size)
        inputs["hopping"][index, :size, :size] = inputs["hopping"][index, :size, :size][np.ix_(permutation, permutation)]
        for key in ("interaction", "potential"):
            inputs[key][index, :size] = inputs[key][index, :size][permutation]
    permuted.mkdir(exist_ok=True)
    np.savez_compressed(permuted / "inputs.npz", **inputs)
    request = json.loads((original / "request.json").read_text())
    request["inputs"] = str(permuted / "inputs.npz")
    (permuted / "request.json").write_text(json.dumps(request) + "\n")
    command(submission / "solver.py", permuted / "request.json", permuted / "predictions.json")
    first = parse_predictions((original / "predictions.json").read_text(), 256)
    second = parse_predictions((permuted / "predictions.json").read_text(), 256)
    error = float(np.max(np.abs(first - second)))
    report = {"self_contained_output_copy": True, "input_has_no_labels": True,
              "site_permutation_max_abs_prediction_error": error,
              "public_score": json.loads((output / "public_score.json").read_text()),
              "passed": error < 1e-7}
    (ROOT / "adversary/public_workflow_report.json").write_text(json.dumps(report, indent=2) + "\n")
    assert report["passed"], report
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
