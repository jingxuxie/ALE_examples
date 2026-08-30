import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "input"))
sys.path.insert(0, str(ROOT / "participant" / "baseline"))
from model import CONFIG, MEASUREMENTS, PREPARATIONS, compile_experiments, probabilities
from solution import fixed_schedule


def features(parameters, experiments):
    batch = compile_experiments(experiments)
    center = probabilities(parameters, batch)
    columns = []
    for parameter_index in range(9):
        delta = np.zeros(9)
        delta[parameter_index] = 1e-5
        columns.append((probabilities(parameters + delta, batch) - probabilities(parameters - delta, batch)) / 2e-5)
    jacobian = np.stack(columns, axis=1) * np.array(CONFIG["normalization"] + [1, 1, 1, 1])
    return jacobian / np.sqrt(center * (1 - center))[:, None]


def main():
    episodes = json.loads((ROOT / "evaluator" / "hidden" / "episodes.json").read_text())["episodes"]
    rng = np.random.default_rng(44120)
    schedule = fixed_schedule()
    candidates = list(schedule)
    for candidate_index in range(2500):
        candidates.append({"prep": [str(rng.choice(PREPARATIONS)), str(rng.choice(PREPARATIONS))],
                           "measure": str(rng.choice(MEASUREMENTS)), "time": float(rng.uniform(0.05, 12)), "shots": 128})
    records = []
    for episode in episodes:
        parameters = np.array(episode["parameters"])
        candidate_features = features(parameters, candidates)
        initial_features = candidate_features[:48]
        information = 128 * initial_features.T @ initial_features
        covariance = np.linalg.inv(information)
        selected = []
        for allocation_index in range(144):
            projected = candidate_features @ covariance
            denominators = 1 + 128 * np.einsum("ij,ij->i", projected, candidate_features)
            gains = 128 * np.sum(projected[:, :5]**2, axis=1) / denominators
            choice = int(np.argmax(gains))
            direction = projected[choice]
            covariance -= 128 * np.outer(direction, direction) / denominators[choice]
            covariance = (covariance + covariance.T) / 2
            selected.append(choice)
        all_features = np.concatenate([initial_features, candidate_features[selected]])
        covariance = np.linalg.inv(128 * all_features.T @ all_features)
        records.append({"family": episode["family"], "oracle_design_local_crlb_rms": float(np.sqrt(np.trace(covariance[:5, :5]) / 5)),
                        "shots": 24576, "queries": 192})
    report = {"diagnostic_only": True, "is_valid_strategy": False,
              "description": "True-parameter local Fisher allocation after a 48-query fixed prefix; finite shots and 192 queries respected. Does not measure estimation error or prove achievability.",
              "mean_local_crlb_rms": float(np.mean([record["oracle_design_local_crlb_rms"] for record in records])),
              "family_mean_local_crlb_rms": {family: float(np.mean([record["oracle_design_local_crlb_rms"] for record in records if record["family"] == family])) for family in CONFIG["suite"]["families"]},
              "episodes": records}
    (ROOT / "adversary" / "design_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "episodes"}, indent=2))


if __name__ == "__main__":
    main()
