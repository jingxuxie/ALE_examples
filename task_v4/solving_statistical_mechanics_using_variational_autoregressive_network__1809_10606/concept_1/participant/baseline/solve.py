import json
import os
from pathlib import Path
import sys

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workspace"))
from van import energy, sample_component


def solve(instance):
    count = instance["n"]
    couplings = np.asarray(instance["couplings"])
    fields = np.asarray(instance["fields"])
    rng = np.random.default_rng(831)
    weights = np.tril(rng.normal(0, 0.02, (count, count)), -1)
    biases = np.zeros(count)
    first = np.zeros((count, count + 1))
    second = first.copy()
    for iteration in range(1600):
        anneal = min(1.0, 0.1 + iteration / 1100)
        spins = sample_component(rng, weights, biases, range(count), 384)
        logits = spins @ weights.T + biases
        log_model = -np.logaddexp(0, -spins * logits).sum(axis=1)
        reward = anneal * energy(spins, couplings, fields) + log_model
        residual = ((spins + 1) / 2 - expit(logits)) * (reward - reward.mean())[:, None]
        gradient_weights = np.tril(residual.T @ spins / len(spins), -1)
        gradient = np.column_stack((gradient_weights, residual.mean(axis=0)))
        first = 0.9 * first + 0.1 * gradient
        second = 0.999 * second + 0.001 * gradient**2
        update = 0.025 * (first / (1 - 0.9**(iteration + 1))) / (np.sqrt(second / (1 - 0.999**(iteration + 1))) + 1e-8)
        weights -= update[:, :-1]
        biases -= update[:, -1]
        norm = np.abs(weights).sum(axis=1) + np.abs(biases)
        scale = np.minimum(1, 55 / np.maximum(1, norm))
        weights *= scale[:, None]
        biases *= scale
    return {"mixing": [1.0], "weights": [weights.tolist()], "biases": [biases.tolist()], "orders": [list(range(count))]}


if __name__ == "__main__":
    instance = json.loads(Path(sys.argv[1]).read_text())
    Path(sys.argv[2]).write_text(json.dumps(solve(instance)))
