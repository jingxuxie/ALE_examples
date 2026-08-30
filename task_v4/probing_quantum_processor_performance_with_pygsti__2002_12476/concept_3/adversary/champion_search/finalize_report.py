import hashlib
import json
import sys
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
CONCEPT = HERE.parents[1]
sys.path.insert(0, str(CONCEPT / "adversary"))
from audit import density_prediction


def load(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def main():
    summary = json.loads((HERE / "summary.json").read_text())
    physics = []
    regimes = {}
    stage_errors = {name: [] for name in ["depth24", "depth64", "train", "all"]}
    maximum_parameter_error = 0.
    for campaign in summary["campaigns"]:
        directory = HERE / "campaigns" / f"campaign_{campaign['campaign']:02d}"
        score = json.loads((directory / "score.json").read_text())
        parameters = load(directory / "private" / "parameters.npz")["parameters"]
        queries = load(directory / "input" / "queries.npz")
        truth = load(directory / "private" / "queries_truth.npz")["p1"]
        for device in range(4):
            selected = np.flatnonzero(queries["device"] == device)
            row = int(selected[(31 * campaign["campaign"] + 19 * device) % len(selected)])
            record = {key: values[row] for key, values in queries.items()}
            probability, eigenvalue, trace_error = density_prediction(parameters[device], record)
            difference = abs(probability - truth[row])
            assert difference < 2e-11 and eigenvalue > -2e-12 and trace_error < 2e-11
            physics.append({"campaign": campaign["campaign"], "device": device, "query_id": int(queries["ids"][row]),
                            "depth": int(record["length"]), "probability_difference": float(difference),
                            "minimum_joint_eigenvalue": eigenvalue, "maximum_trace_error": trace_error})
            details = score["devices"][str(device)]
            regimes.setdefault(details["regime"], []).append(details["stages"]["all"]["query_rmse"])
            for stage in stage_errors:
                stage_errors[stage].append(details["stages"][stage]["query_rmse"])
            maximum_parameter_error = max(maximum_parameter_error, details["stages"]["all"]["scaled_parameter_rmse"])
    frozen = json.loads((CONCEPT / "adversary" / "frozen_manifest.json").read_text())
    mismatches = [name for name, digest in frozen.items()
                  if hashlib.sha256((CONCEPT / name).read_bytes()).hexdigest() != digest]
    result = {
        "completed_campaigns": summary["completed_campaigns"], "independent_devices": summary["independent_device_fits"],
        "private_prediction_queries": 8192 * summary["completed_campaigns"],
        "labeled_rows": (28464 + 2048) * summary["completed_campaigns"],
        "substantial_failure_campaigns": summary["substantial_failure_campaigns"],
        "worst_campaign_macro_rmse": max(record["macro_rmse"] for record in summary["campaigns"]),
        "worst_family_rmse": max(record["worst_family_rmse"] for record in summary["campaigns"]),
        "worst_device_family_rmse": max(record["worst_device_family_rmse"] for record in summary["campaigns"]),
        "campaign_wall_seconds_range": [min(record["campaign_wall_seconds"] for record in summary["campaigns"]),
                                        max(record["campaign_wall_seconds"] for record in summary["campaigns"])],
        "total_fit_user_cpu_seconds": sum(record["total_fit_user_cpu_seconds"] for record in summary["campaigns"]),
        "maximum_fit_rss_mib": max(record["maximum_fit_rss_kib"] for record in summary["campaigns"]) / 1024.,
        "maximum_simultaneous_campaigns": 2, "maximum_simultaneous_learning_cpus": 16,
        "regime_results": {name: {"devices": len(values), "maximum_device_rmse": max(values)} for name, values in regimes.items()},
        "stage_maximum_query_rmse": {name: max(values) for name, values in stage_errors.items()},
        "maximum_final_scaled_parameter_rmse": maximum_parameter_error,
        "parameter_error_is_not_a_failure_condition": True,
        "additional_independent_density_checks": physics,
        "maximum_density_matrix_disagreement": max(record["probability_difference"] for record in physics),
        "frozen_participant_evaluator_manifest_mismatches": mismatches,
        "recommendation": ("Investigate the recorded scientific failure mechanisms before a new generation"
                           if summary["substantial_failure_campaigns"] else
                           "No scientifically justified new generation was found. The champion remains solved under the original disclosed physical ranges and acquisition rules in this finite search. Do not invent tighter noise-floor targets or unidentifiable hidden requirements."),
        "limits": "Finite stress search, not a proof of uniform robustness over all 54-dimensional parameter boxes. No new participant/evaluator generation or fresh-agent attempt was created."
    }
    (HERE / "final_report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    files = sorted(str(path.relative_to(HERE)) for path in HERE.rglob("*") if path.is_file())
    (HERE / "files.json").write_text(json.dumps({"root": str(HERE), "files": files}, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "additional_independent_density_checks"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
