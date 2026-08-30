"""Public accuracy-only scoring of saved predictions; no private assets."""

import argparse
import json
from pathlib import Path

import numpy as np

from input.metrics import parse_predictions, score_predictions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("labelled_dataset", type=Path)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--report", type=Path)
    arguments = parser.parse_args()
    settings = json.loads((Path(__file__).resolve().parent / "input/scoring.json").read_text())
    try:
        with np.load(arguments.labelled_dataset, allow_pickle=False) as archive:
            labels, families = archive["gaps"], archive["family"]
        if arguments.predictions.stat().st_size > settings["prediction_bytes"]:
            raise ValueError("prediction file too large")
        predictions = parse_predictions(arguments.predictions.read_text(), len(labels))
        report = score_predictions(predictions, labels, families, settings)
        report.update(valid=True, passed=report["accuracy_passed"],
                      resource_score=None, runtime_seconds=None,
                      reason="public_accuracy_only_resources_not_measured")
    except Exception as error:
        report = {"valid": False, "passed": False, "core_score": 0.0,
                  "worst_family_score": 0.0, "resource_score": None,
                  "runtime_seconds": None, "reason": type(error).__name__ + ": " + str(error)}
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.report:
        arguments.report.write_text(text)
    print(text, end="")
    raise SystemExit(0 if report["valid"] else 2)


if __name__ == "__main__":
    main()
