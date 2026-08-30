import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from physics import LOWER, UPPER, STATES, predict_many


def emit(value):
    print(json.dumps(value), flush=True)


def main():
    start = json.loads(sys.stdin.readline())
    config = start["config"]
    random = np.random.default_rng(731)
    experiments = []
    observations = []
    for query_index in range(config["query_budget"]):
        experiment = {
            "type": "query",
            "preparation": int(STATES[(query_index * 7) % len(STATES)]),
            "time": 0.0 if query_index == 0 else float(0.25 + 1.1 * random.random()),
            "phases": [0.0] * 6,
        }
        emit(experiment)
        response = json.loads(sys.stdin.readline())
        experiments.append(experiment)
        observations.append(response["counts"])
    observations = np.asarray(observations)
    smoothed = (observations + 0.1) / (config["shots"] + 6.4)

    def residual(normalized):
        predictions = predict_many(LOWER + (UPPER - LOWER) * normalized, experiments)
        return (np.sqrt(predictions + 1e-10) - np.sqrt(smoothed)).ravel()

    fit = least_squares(residual, np.full(20, 0.5), bounds=(0.00001, 0.99999), max_nfev=65, ftol=1e-6, xtol=1e-6, gtol=1e-6)
    emit({"type": "answer", "parameters": (LOWER + (UPPER - LOWER) * fit.x).tolist()})


if __name__ == "__main__":
    main()
