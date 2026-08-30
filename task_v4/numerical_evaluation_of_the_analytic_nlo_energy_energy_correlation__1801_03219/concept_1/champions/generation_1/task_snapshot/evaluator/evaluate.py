import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np


CONCEPT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONCEPT / "participant" / "workspace"))
from model import bin_average, evaluate, load_model


def grade(submission, broad=False):
    started = time.monotonic()
    model = load_model(Path(submission) / "model.json")
    cases = np.load(CONCEPT / "evaluator" / "hidden" / "cases.npz")
    reference = dict(np.load(CONCEPT / "evaluator" / "hidden" / "oracle.npz"))
    coordinates = cases["coordinates"]
    if broad:
        coordinates = np.unique(np.concatenate([coordinates, np.linspace(-24, 24, 60001)]))
    knot_points = np.concatenate([model["knots"], np.nextafter(model["knots"][1:-1], -np.inf)])
    coordinates = np.concatenate([coordinates, knot_points])
    truth = evaluate(reference, coordinates)
    predicted = evaluate(model, coordinates)
    derivative_truth = evaluate(reference, coordinates, True)
    derivative_prediction = evaluate(model, coordinates, True)
    families = {}
    locations = [("collinear", -24, -10), ("near_collinear", -10, -3),
                 ("central", -3, 3), ("near_back_to_back", 3, 10),
                 ("back_to_back", 10, 25)]
    for label, lower, upper in locations:
        selected = (coordinates >= lower) & (coordinates < upper)
        families[label+"_values"] = (np.abs(predicted[selected]-truth[selected])/(2e-8*(1+np.abs(truth[selected])))).ravel()
        families[label+"_derivatives"] = (np.abs(derivative_prediction[selected]-derivative_truth[selected])/(2e-7*(1+np.abs(derivative_truth[selected])))).ravel()
    bin_predictions = np.array([bin_average(model, left, right) for left, right in cases["bins"]])
    bin_ratios = np.abs(bin_predictions-cases["averages"])/(2e-8*(1+np.abs(cases["averages"])))
    narrow = np.diff(cases["bins"], axis=1).ravel() < 0.02
    families["narrow_bins"] = bin_ratios[narrow].ravel()
    families["broad_bins"] = bin_ratios[~narrow].ravel()
    combination_truth = np.sum(cases["weights"]*cases["values"], axis=1)
    combination_prediction = np.sum(cases["weights"]*evaluate(model, cases["coordinates"]), axis=1)
    families["signed_channel_combinations"] = np.abs(combination_prediction-combination_truth)/(2e-8*(1+np.abs(combination_truth)))
    summaries = {}
    for label, ratios in families.items():
        if not np.isfinite(ratios).all():
            raise ValueError("nonfinite computed response")
        quality = np.clip(1-np.log10(np.maximum(1, ratios))/8, 0, 1)
        summaries[label] = {"score": float(np.mean(quality)),
                            "fraction_within_tolerance": float(np.mean(ratios <= 1)),
                            "max_tolerance_ratio": float(np.max(ratios)),
                            "count": int(len(ratios))}
    worst_ratio = max(row["max_tolerance_ratio"] for row in summaries.values())
    target_path = CONCEPT / "evaluator" / "hidden" / "target.json"
    target = json.loads(target_path.read_text()) if target_path.exists() else {}
    baseline_ratio = target.get("baseline_max_tolerance_ratio")
    improvement = baseline_ratio / max(worst_ratio, 1e-300) if baseline_ratio else None
    passed = worst_ratio <= 1 and (improvement is None or improvement >= 100)
    return {
        "core_score": float(np.mean([row["score"] for row in summaries.values()])),
        "worst_family_score": min(row["score"] for row in summaries.values()),
        "resource_score": min(1.0, 320/model["scalar_count"]),
        "scalar_count": model["scalar_count"], "max_tolerance_ratio": worst_ratio,
        "improvement_factor": improvement, "passed": bool(passed), "valid": True,
        "reason": "all accuracy and compression targets met" if passed else "one or more accuracy/improvement targets missed",
        "families": summaries, "elapsed_seconds": time.monotonic()-started,
        "broad_search": broad,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission")
    parser.add_argument("--report")
    parser.add_argument("--broad", action="store_true")
    arguments = parser.parse_args()
    try:
        report = grade(arguments.submission, arguments.broad)
    except Exception as exception:
        report = {"core_score": 0.0, "worst_family_score": 0.0,
                  "resource_score": 0.0, "passed": False, "valid": False,
                  "reason": f"{type(exception).__name__}: {exception}"}
    if arguments.report:
        Path(arguments.report).write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
