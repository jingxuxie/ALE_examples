import itertools
import numpy as np
from scipy.special import logsumexp


def elimination_order(couplings, fixed):
    active = set(range(len(couplings))) - set(fixed)
    neighbors = [set(np.flatnonzero(np.abs(row) > 1e-12)) & active for row in couplings]
    eliminated = []
    while active:
        site = min(active, key=lambda vertex: (len(neighbors[vertex] & active), vertex))
        linked = sorted(neighbors[site] & active)
        if len(linked) > 2:
            return None
        eliminated.append(site)
        active.remove(site)
        if len(linked) == 2:
            first, second = linked
            neighbors[first].add(second)
            neighbors[second].add(first)
    return eliminated


def exact_sparse(couplings, fields):
    count = len(fields)
    if np.count_nonzero(couplings) > 6 * count:
        return None
    chosen = None
    for cut_count in range(4):
        for fixed in itertools.combinations(range(count), cut_count):
            eliminated = elimination_order(couplings, fixed)
            if eliminated is not None:
                chosen = fixed, eliminated
                break
        if chosen is not None:
            break
    if chosen is None:
        return None
    fixed, eliminated = chosen
    models = []
    log_mixing = []
    order = list(fixed) + eliminated[::-1]
    for assignment in itertools.product((-1, 1), repeat=len(fixed)):
        matrix = couplings.copy()
        local_fields = fields.copy()
        assigned = np.asarray(assignment)
        constant = float(fields[list(fixed)] @ assigned)
        if fixed:
            constant += .5 * assigned @ matrix[np.ix_(fixed, fixed)] @ assigned
            local_fields += matrix[:, fixed] @ assigned
            matrix[:, fixed] = 0
            matrix[list(fixed), :] = 0
        weights = np.zeros_like(matrix)
        biases = np.zeros(count)
        for site, spin in zip(fixed, assignment):
            biases[site] = 45 * spin
        for site in eliminated:
            linked = np.flatnonzero(np.abs(matrix[site]) > 1e-14)
            biases[site] = 2 * local_fields[site]
            weights[site, linked] = 2 * matrix[site, linked]
            states = np.asarray(list(itertools.product((-1, 1), repeat=len(linked)))).reshape(-1, len(linked)) if len(linked) else np.zeros((1, 0))
            argument = local_fields[site] + states @ matrix[site, linked]
            factor = np.logaddexp(argument, -argument)
            constant += factor.mean()
            local_fields[linked] += states.T @ factor / len(factor)
            if len(linked) == 2:
                first, second = linked
                increment = (states[:, 0] * states[:, 1]) @ factor / len(factor)
                matrix[first, second] += increment
                matrix[second, first] += increment
            matrix[site, :] = 0
            matrix[:, site] = 0
        models.append((weights, biases))
        log_mixing.append(constant)
    if any(np.max(abs(biases) + abs(weights).sum(axis=1)) > 59 for weights, biases in models):
        return None
    mixing = np.maximum(np.exp(np.asarray(log_mixing) - logsumexp(log_mixing)), 1e-100)
    mixing /= mixing.sum()
    repeats = 8 // len(models)
    return {'mixing': np.repeat(mixing / repeats, repeats).tolist(),
            'weights': [weights.tolist() for weights, biases in models for repeat in range(repeats)],
            'biases': [biases.tolist() for weights, biases in models for repeat in range(repeats)],
            'orders': [order for repeat in range(8)]}
