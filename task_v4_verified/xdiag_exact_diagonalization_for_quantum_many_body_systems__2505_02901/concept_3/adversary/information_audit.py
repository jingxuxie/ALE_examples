import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant/workspace"))
from physics import LOWER, UPPER, STATES, predict_many


def main():
    random = np.random.default_rng(1588631)
    config = json.loads((ROOT / "participant/input/config.json").read_text())
    cases = json.loads((ROOT / "evaluator/hidden/devices.json").read_text())
    experiments = [{"type": "query", "preparation": int(STATES[(index * 7) % len(STATES)]), "time": 0 if index == 0 else float(random.uniform(0.8, 4.8)), "phases": random.uniform(-np.pi, np.pi, 6).tolist()} for index in range(config["query_budget"])]
    results = []
    step = 1e-5
    for case in cases:
        parameters = np.asarray(case["parameters"])
        base = predict_many(parameters, experiments).ravel()
        derivatives = []
        for parameter_index in range(len(LOWER)):
            displacement = np.zeros(len(LOWER))
            displacement[parameter_index] = step * (UPPER[parameter_index] - LOWER[parameter_index])
            derivatives.append(((predict_many(parameters + displacement, experiments) - predict_many(parameters - displacement, experiments)) / (2 * step)).ravel())
        jacobian = np.asarray(derivatives).T
        fisher = config["shots"] * (jacobian.T @ (jacobian / np.maximum(base[:, None], 1e-14)))
        eigenvalues = np.linalg.eigvalsh(fisher)
        bound = float(np.sqrt(np.trace(np.linalg.inv(fisher)) / len(LOWER)))
        results.append({"id": case["id"], "family": case["family"], "local_normalized_rmse_bound": bound, "fisher_condition": float(eigenvalues[-1] / eigenvalues[0])})
    report = {"devices": results, "mean_local_bound": float(np.mean([entry["local_normalized_rmse_bound"] for entry in results])), "max_local_bound": max(entry["local_normalized_rmse_bound"] for entry in results), "target_rmse": 1 - config["target_core_score"], "note": "Local Fisher bounds only: they assess available information for a fixed admissible design, not global identifiability or a passing solver. They do not demonstrate achievability."}
    (ROOT / "adversary/information_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "devices"}, indent=2))


if __name__ == "__main__":
    main()
