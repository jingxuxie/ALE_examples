import json
import sys
from pathlib import Path
import numpy as np
from scipy.special import logsumexp
from cube import linear_logits
from regional import configurations


def metrics(instance, model):
    count = instance['n']
    assert set(model) == {'mixing', 'weights', 'biases', 'orders'}
    mixing = np.asarray(model['mixing'], dtype=float)
    weights = np.asarray(model['weights'], dtype=float)
    biases = np.asarray(model['biases'], dtype=float)
    orders = np.asarray(model['orders'])
    assert mixing.shape == (8,) and weights.shape == (8, count, count)
    assert biases.shape == (8, count) and orders.shape == (8, count)
    assert np.all(np.isfinite(mixing)) and np.all(mixing > 0)
    assert abs(mixing.sum() - 1) <= 1e-10
    assert np.all(np.isfinite(weights)) and np.all(np.isfinite(biases))
    assert np.max(abs(biases) + abs(weights).sum(axis=2)) <= 60
    components = []
    for component, order in enumerate(orders):
        assert np.array_equal(np.sort(order), np.arange(count))
        joint = np.zeros(1)
        for position, site in enumerate(order):
            assert np.all(weights[component, site, order[position:]] == 0)
            parameters = np.concatenate(([biases[component, site]], weights[component, site, order[:position]]))
            logits = linear_logits(parameters)
            normalizer = np.logaddexp(0, logits)
            joint = np.concatenate((joint - normalizer, joint + logits - normalizer))
        original = joint.reshape((2,) * count).transpose(np.argsort(order[::-1])[::-1]).reshape(-1)
        components.append(original + np.log(mixing[component]))
    log_model = logsumexp(components, axis=0)
    spins = configurations(count)
    couplings = np.asarray(instance['couplings'])
    fields = np.asarray(instance['fields'])
    log_target = .5 * np.sum((spins @ couplings) * spins, axis=1) + spins @ fields
    log_target -= logsumexp(log_target)
    return {'kl': float(np.exp(log_model) @ (log_model - log_target)),
            'ess': float(np.exp(-logsumexp(2 * log_target - log_model))),
            'normalization': float(np.exp(logsumexp(log_model)))}


if __name__ == '__main__':
    instance_path, model_path = map(Path, sys.argv[1:])
    assert model_path.stat().st_size <= 1048576
    print(json.dumps(metrics(json.loads(instance_path.read_text()), json.loads(model_path.read_text()))))
