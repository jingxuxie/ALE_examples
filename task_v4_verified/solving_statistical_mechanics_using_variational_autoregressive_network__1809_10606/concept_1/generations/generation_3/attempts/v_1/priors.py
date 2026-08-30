import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from scipy.special import logsumexp
from cube import linear_logits
from regional import regions


def model_score(model, distribution):
    weights = np.asarray(model['weights'])
    biases = np.asarray(model['biases'])
    orders = np.asarray(model['orders'])
    count = len(biases[0])

    def component_log(component):
        order = orders[component]
        joint = np.zeros(1)
        for position, site in enumerate(order):
            parameters = np.concatenate(([biases[component, site]], weights[component, site, order[:position]]))
            logits = linear_logits(parameters)
            normalizer = np.logaddexp(0, logits)
            joint = np.concatenate((joint - normalizer, joint + logits - normalizer))
        return joint.reshape((2,) * count).transpose(np.argsort(order[::-1])[::-1]).reshape(-1)

    with ThreadPoolExecutor(max_workers=4) as executor:
        logs = np.asarray(list(executor.map(component_log, range(8))))
    log_model = logsumexp(logs + np.log(model['mixing'])[:, None], axis=0)
    difference = log_model - distribution.log_target
    reverse = np.exp(log_model) @ difference
    forward = -distribution.target @ difference
    log_chi = logsumexp(2 * distribution.log_target - log_model)
    return float(reverse + .05 * forward + .002 * (np.exp(min(50, log_chi)) - 1))


def initialize_prior(instance, distribution, verbose=False):
    if instance['n'] != 20:
        return None
    couplings = np.asarray(instance['couplings'])
    fields = np.asarray(instance['fields'])
    blocks = regions(couplings * (abs(couplings) > .65 * np.max(abs(couplings))))
    if len(blocks) != 5 or any(len(block) != 4 for block in blocks):
        return None
    for block in blocks:
        local = couplings[np.ix_(block, block)]
        gauge = np.sign(fields[block])
        strength = np.median(abs(local[np.triu_indices(4, 1)]))
        if strength <= 0 or np.any(local[np.triu_indices(4, 1)] * (gauge[:, None] * gauge[None, :])[np.triu_indices(4, 1)] >= 0):
            return None
        if np.any(abs(fields[block]) < .7 * strength) or np.any(abs(fields[block]) > 1.3 * strength):
            return None
    sites = np.concatenate(blocks)
    gauge = np.sign(fields[sites])
    best_model = None
    best_score = np.inf
    for name in ['template_moderate.json', 'template_cold.json']:
        path = Path(__file__).with_name(name)
        if not path.exists():
            continue
        prior = json.loads(path.read_text())['model']
        weights = np.zeros((8, 20, 20))
        biases = np.zeros((8, 20))
        canonical_weights = np.asarray(prior['weights']) * gauge[None, :, None] * gauge[None, None, :]
        for component in range(8):
            weights[component][np.ix_(sites, sites)] = canonical_weights[component]
        biases[:, sites] = np.asarray(prior['biases']) * gauge
        model = {'mixing': prior['mixing'], 'weights': weights.tolist(), 'biases': biases.tolist(),
                 'orders': sites[np.asarray(prior['orders'])].tolist()}
        score = model_score(model, distribution)
        if verbose:
            print('prior', name, score, flush=True)
        if score < best_score:
            best_model = model
            best_score = score
    return best_model
