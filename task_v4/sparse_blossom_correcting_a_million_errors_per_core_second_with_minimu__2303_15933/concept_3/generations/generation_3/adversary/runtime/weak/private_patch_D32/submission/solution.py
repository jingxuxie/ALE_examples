import os
import sys
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import json
import numpy as np
from scipy.optimize import minimize

input_directory = os.environ.get("DETECTOR_INPUT_DIR", "/participant/input")
if not Path(input_directory).is_dir():
    input_directory = str(Path(__file__).resolve().parents[1] / "input")
sys.path.insert(0, input_directory)
from moments import MomentModel, parity


def main():
    spec = json.loads(sys.stdin.readline())["spec"]
    detector_count = spec["detector_count"]
    masks = [1 << detector for detector in range(detector_count)]
    masks += [(1 << first) | (1 << second) for first, second in spec["detector_edges"]]
    masks = np.array(sorted(set(masks)), dtype=np.int64)
    model = MomentModel(spec, masks)
    totals = np.zeros(len(spec["actions"]))
    sums = np.zeros((len(totals), len(masks)))
    remaining = spec["shot_budget"]
    for action in range(len(totals)):
        allocation = remaining // (len(totals) - action)
        while allocation:
            shots = min(allocation, spec["max_shots_per_query"])
            print(json.dumps({"type": "query", "action": action, "shots": shots}), flush=True)
            observation = json.loads(sys.stdin.readline())
            syndromes = np.array(observation["syndromes"], dtype=np.int64)
            multiplicities = np.array(observation["multiplicities"])
            sums[action] += (1.0 - 2.0 * parity(syndromes[:, None] & masks[None, :])).T @ multiplicities
            totals[action] += shots
            allocation -= shots
            remaining -= shots
    observed = sums / totals[:, None]
    weights = totals[:, None] / np.maximum(1.0 - observed**2, 0.002)
    prior = model.bounds.mean(axis=1)

    def objective(point):
        expected, derivative = model.predict(point, gradient=True)
        residual = expected - observed
        value = np.sum(weights * residual**2) + np.sum((point - prior)**2)
        gradient = 2.0 * np.einsum("af,akf->k", weights * residual, derivative) + 2.0 * (point - prior)
        return value / spec["shot_budget"], gradient / spec["shot_budget"]

    fitted = minimize(objective, prior, jac=True, method="L-BFGS-B", bounds=model.bounds.tolist(),
                      options={"maxiter": 120, "ftol": 1e-10})
    print(json.dumps({"type": "final", "rates": np.exp(fitted.x).tolist()}), flush=True)


if __name__ == "__main__":
    main()
