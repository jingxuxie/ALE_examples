import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
CONCEPT = HERE.parents[1]
sys.path.insert(0, str(CONCEPT / "evaluator"))
sys.path.insert(0, str(HERE / "solver"))
from evaluate import load_submission, score_predictions
import model


def load(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def score_campaign(directory, protocol):
    metadata = json.loads((directory / "metadata.json").read_text())
    execution = json.loads((directory / "execution.json").read_text())
    if not execution["completed_prediction"]:
        result = {"campaign": metadata["campaign_index"], "scientific_status": "incomplete_or_infrastructure_failure",
                  "reason": "No completed scientific prediction; do not count path/schema/timeout problems as robustness failures",
                  "execution": execution}
        (directory / "score.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    labels = load(directory / "private" / "queries_truth.npz")
    predictions = load_submission(directory / "output" / "predictions.json", labels["ids"], protocol["max_submission_bytes"])
    scores = score_predictions(predictions, labels, protocol)
    query_data = load(directory / "input" / "queries.npz")
    training = load(directory / "input" / "train.npz")
    development = load(directory / "input" / "development.npz")
    truth_parameters = load(directory / "private" / "parameters.npz")["parameters"]
    resources = [json.loads((directory / "output" / f"resource_device_{device}.json").read_text()) for device in range(4)]
    device_results = {}
    for device in range(4):
        selected = query_data["device"] == device
        query_subset = model.select(query_data, selected)
        true_probabilities = labels["p1"][selected]
        training_rows = training["device"] == device
        stages = {}
        for stage in ["depth24", "depth64", "train", "all"]:
            fit = load(directory / "output" / f"fit_d{device}_{stage}.npz")
            predicted = model.predict(fit["params"], query_subset, threads=1)
            if stage.startswith("depth"):
                rows = int(np.sum(training_rows & (training["length"] <= int(stage[5:]))))
            else:
                rows = int(np.sum(training_rows)) + (int(np.sum(development["device"] == device)) if stage == "all" else 0)
            stages[stage] = {"query_rmse": float(np.sqrt(np.mean((predicted - true_probabilities) ** 2))),
                             "deviance_plus_ridge_per_labeled_row": float(2. * fit["cost"] / rows),
                             "optimizer_optimality": float(fit["optimality"]),
                             "scaled_parameter_rmse": float(np.sqrt(np.mean(((fit["params"] - truth_parameters[device]) / model.SCALE) ** 2))),
                             "at_parameter_bounds": int(np.sum(np.abs(fit["scaled"]) > 1. - 1e-6))}
        log = (directory / f"fit_device_{device}.log").read_text()
        stages_evaluations = re.findall(r"(fit_d\d+_\w+) finished (.*?) nfev (\d+) cost ([^ ]+) optimality ([^\n]+)", log)
        device_results[str(device)] = {"regime": metadata["regimes"][device], "stages": stages,
                                      "optimizer_terminations": [dict(stage=name, message=message, evaluations=int(evaluations),
                                                                      cost=float(cost), optimality=float(optimality))
                                                                   for name, message, evaluations, cost, optimality in stages_evaluations],
                                      "resources": resources[device]}
    scores.update(campaign=metadata["campaign_index"], campaign_kind=metadata["kind"],
                  scientific_status="solved" if scores["passed"] else "substantial_predictive_failure",
                  worst_family_rmse=max(scores["family_rmse"].values()), devices=device_results,
                  campaign_wall_seconds=execution["elapsed_seconds"],
                  total_fit_user_cpu_seconds=sum(record["user_cpu_seconds"] for record in resources),
                  maximum_fit_rss_kib=max(record["max_rss_kib"] for record in resources),
                  maximum_independent_oracle_disagreement=max(record["max_native_independent_difference"] for record in metadata["independent_physics_checks"]))
    (directory / "score.json").write_text(json.dumps(scores, indent=2, allow_nan=False) + "\n")
    return scores


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaigns", nargs="+", type=int)
    arguments = parser.parse_args()
    protocol = json.loads((CONCEPT / "evaluator" / "hidden" / "protocol.json").read_text())
    directories = ([HERE / "campaigns" / f"campaign_{index:02d}" for index in arguments.campaigns]
                   if arguments.campaigns else sorted((HERE / "campaigns").glob("campaign_*")))
    results = []
    for directory in directories:
        if (directory / "execution.json").exists():
            results.append(score_campaign(directory, protocol))
    completed = [result for result in results if result["scientific_status"] != "incomplete_or_infrastructure_failure"]
    failures = [result for result in completed if not result["passed"]]
    summary = {"champion_source": "attempts/v_1 (solved generation 0)",
               "unchanged_original_thresholds": {"macro_rmse": 0.020, "family_rmse": 0.025, "device_family_rmse": 0.040},
               "completed_campaigns": len(completed), "independent_device_fits": 4 * len(completed),
               "substantial_failure_campaigns": [result["campaign"] for result in failures],
               "scientific_conclusion": ("Genuine in-range predictive failure found; inspect device/stage diagnostics before proposing a generation"
                                         if failures else "No substantial predictive failure found in the completed private search"),
               "no_new_generation_written": True,
               "campaigns": [{key: result[key] for key in ["campaign", "campaign_kind", "macro_rmse", "worst_family_rmse",
                                                           "worst_device_family_rmse", "passed", "campaign_wall_seconds",
                                                           "total_fit_user_cpu_seconds", "maximum_fit_rss_kib",
                                                           "maximum_independent_oracle_disagreement"]} for result in completed],
               "infrastructure_failures_not_counted": [result["campaign"] for result in results if result["scientific_status"] == "incomplete_or_infrastructure_failure"]}
    source_hashes = {}
    for name in ["fit.py", "model.py", "simulator.cpp", "validate.py"]:
        original = (CONCEPT / "attempts" / "v_1" / name).read_bytes()
        copied = (HERE / "solver" / name).read_bytes()
        assert original == copied
        source_hashes[name] = hashlib.sha256(original).hexdigest()
    summary["unchanged_champion_source_sha256"] = source_hashes
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
