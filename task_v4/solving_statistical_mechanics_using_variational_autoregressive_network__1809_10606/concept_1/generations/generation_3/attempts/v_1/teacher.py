import time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.special import expit, logsumexp
from regional import configurations, regions


def logistic_projection(design, probability, positive, initial):
    parameters = initial.copy()
    identity = np.eye(len(parameters))
    for iteration in range(45):
        logits = design @ parameters
        prediction = expit(logits)
        gradient = design.T @ (probability * prediction - positive) + 1e-7 * parameters
        if np.max(np.abs(gradient)) < 2e-8:
            break
        curvature = probability * prediction * (1 - prediction)
        hessian = design.T @ (curvature[:, None] * design) + 1e-7 * identity
        update = cho_solve(cho_factor(hessian, check_finite=False), gradient, check_finite=False)
        step = min(1., 10 / max(10., np.abs(update).sum()))
        current = probability @ np.logaddexp(0, logits) - positive @ logits + 5e-8 * (parameters @ parameters)
        for trial in range(12):
            candidate = parameters - step * update
            candidate_logits = design @ candidate
            objective = probability @ np.logaddexp(0, candidate_logits) - positive @ candidate_logits + 5e-8 * (candidate @ candidate)
            if objective <= current + 1e-12:
                parameters = candidate
                break
            step *= .5
        else:
            break
    return parameters


def initialize_teacher(instance, verbose=False, samples=32768, distribution=None, clustered=False):
    started = time.monotonic()
    count = instance['n']
    couplings = np.asarray(instance['couplings'])
    fields = np.asarray(instance['fields'])
    if distribution is None:
        from distribution import Distribution
        distribution = Distribution(instance)
    spins = distribution.spins
    log_target = distribution.log_target
    selected = np.argpartition(log_target, -samples)[-samples:]
    probability = np.exp(log_target[selected])
    probability /= probability.sum()
    spins = spins[selected]
    component_probability = [probability] * 8
    mixing = np.full(8, .125)
    centers = None
    if clustered:
        rng = np.random.default_rng(548)
        centers = [spins[np.argmax(probability)].copy()]
        distance = np.full(len(spins), np.inf)
        for component in range(1, 8):
            distance = np.minimum(distance, np.sum((spins - centers[-1]) ** 2, axis=1))
            selection = probability * distance
            centers.append(spins[rng.choice(len(spins), p=selection / selection.sum())].copy())
        centers = np.asarray(centers)
        for iteration in range(30):
            distances = np.sum(centers ** 2, axis=1)[None, :] - 2 * spins @ centers.T
            labels = np.argmin(distances, axis=1)
            updated = centers.copy()
            for component in range(8):
                local_probability = probability * (labels == component)
                mass = local_probability.sum()
                if mass > 1e-12:
                    updated[component] = local_probability @ spins / mass
            if np.max(abs(updated - centers)) < 1e-7:
                break
            centers = updated
        component_probability = [probability * (.001 + .999 * (labels == component)) for component in range(8)]
        mixing = np.asarray([local.sum() for local in component_probability])
        component_probability = [local / mass for local, mass in zip(component_probability, mixing)]
        mixing /= mixing.sum()
    blocks = regions(couplings * (np.abs(couplings) > .65 * np.max(abs(couplings))))
    orders = []
    for component in range(8):
        rng = np.random.default_rng(283 + component)
        order = np.concatenate([rng.permutation(blocks[index]) for index in rng.permutation(len(blocks))])
        if clustered:
            priority = np.argsort(-abs(centers[component] - probability @ spins))[:3]
            order = np.concatenate((priority, [site for site in order if site not in priority]))
        orders.append(order)

    def fit(component):
        order = orders[component]
        probability = component_probability[component]
        design = np.ascontiguousarray(np.column_stack((np.ones(len(spins)), spins[:, order])))
        weights = np.zeros((count, count))
        biases = np.zeros(count)
        for position, site in enumerate(order):
            initial = np.concatenate(([2 * fields[site]], 2 * couplings[site, order[:position]]))
            if position == count - 1:
                parameters = initial
            else:
                parameters = logistic_projection(design[:, :position + 1], probability,
                                                 probability * (spins[:, site] + 1) * .5, initial)
            parameters *= min(1, 59 / max(1, abs(parameters).sum()))
            biases[site] = parameters[0]
            weights[site, order[:position]] = parameters[1:]
        return weights, biases

    with ThreadPoolExecutor(max_workers=4) as executor:
        fitted = list(executor.map(fit, range(8)))
    if verbose:
        print('teacher initialization', time.monotonic() - started, flush=True)
    return {'mixing': mixing.tolist(), 'weights': [entry[0].tolist() for entry in fitted],
            'biases': [entry[1].tolist() for entry in fitted], 'orders': [order.tolist() for order in orders]}
