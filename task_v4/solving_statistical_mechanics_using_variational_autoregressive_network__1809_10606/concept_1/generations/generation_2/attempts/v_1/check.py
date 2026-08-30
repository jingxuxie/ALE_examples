import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import json
import sys
import time
from pathlib import Path
import numpy as np
from scipy.special import logsumexp


def check(instance_path, model_path):
    started = time.monotonic()
    instance = json.loads(Path(instance_path).read_text())
    model = json.loads(Path(model_path).read_text())
    assert set(model) == {"mixing", "weights", "biases", "orders"}
    count = instance["n"]
    mixing = np.asarray(model["mixing"])
    weights = np.asarray(model["weights"])
    biases = np.asarray(model["biases"])
    orders = np.asarray(model["orders"])
    components = len(mixing)
    assert components == 8
    assert weights.shape == (components, count, count)
    assert biases.shape == (components, count)
    assert orders.shape == (components, count)
    assert np.all(mixing > 0) and abs(mixing.sum() - 1) < 1e-10
    assert np.all(np.isfinite(weights)) and np.all(np.isfinite(biases))
    assert np.all(np.abs(biases) + np.abs(weights).sum(axis=2) <= 60)
    assert Path(model_path).stat().st_size <= 1024 ** 2
    for component in range(components):
        assert sorted(orders[component]) == list(range(count))
        ordered = weights[component][np.ix_(orders[component], orders[component])]
        assert np.all(ordered[np.triu_indices(count)] == 0)
    indices = np.arange(1 << count, dtype=np.uint32)
    spins = 2.0 * ((indices[:, None] >> np.arange(count)) & 1) - 1.0
    couplings = np.asarray(instance["couplings"])
    fields = np.asarray(instance["fields"])
    log_target = 0.5 * np.sum((spins @ couplings) * spins, axis=1) + spins @ fields
    log_target -= logsumexp(log_target)
    log_model = np.full(1 << count, -np.inf)
    design = [np.ascontiguousarray(np.column_stack((np.ones(1 << position), spins[:1 << position, :position])))
              for position in range(count)]
    for component in range(components):
        order = orders[component]
        joint = np.zeros(1)
        for position, site in enumerate(order):
            values = np.concatenate(([biases[component, site]], weights[component, site, order[:position]]))
            logits = design[position] @ values
            joint = np.concatenate((joint - np.logaddexp(0, logits), joint - np.logaddexp(0, -logits)))
        log_component = joint.reshape((2,) * count).transpose(np.argsort(order[::-1])[::-1]).reshape(-1)
        log_model = np.logaddexp(log_model, np.log(mixing[component]) + log_component)
    metrics = {"kl": float(np.exp(log_model) @ (log_model - log_target)),
               "ess": float(np.exp(-logsumexp(2 * log_target - log_model))),
               "normalization": float(np.exp(logsumexp(log_model))),
               "forward_kl": float(np.exp(log_target) @ (log_target - log_model)),
               "seconds": time.monotonic() - started}
    assert abs(metrics['normalization'] - 1) < 1e-10
    assert metrics['kl'] >= -1e-10 and 0 < metrics['ess'] <= 1 + 1e-10
    print(model_path, json.dumps(metrics), flush=True)
    return metrics


if __name__ == '__main__':
    check(sys.argv[1], sys.argv[2])
