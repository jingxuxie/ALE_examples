import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, xlogy

from exact import STATES, LIMIT, evaluate
from fit import fit_target
from minimax import minimax
from sectors import best_sector


def fit_row(probability, site, parents):
    count = len(parents)
    if not count:
        return np.zeros(0), 0.0
    prefixes = np.zeros(65536, dtype=np.int32)
    for position, parent in enumerate(parents + [site]):
        prefixes += (STATES[:, parent] > 0).astype(np.int32) << position
    counts = np.bincount(prefixes, weights=probability, minlength=1 << (count + 1))
    zeros, ones = counts[:1 << count], counts[1 << count:]
    total = zeros + ones
    active = total > 1e-13
    features = (2 * ((np.arange(1 << count)[active, None] >> np.arange(count)) & 1) - 1).astype(float)
    zeros, ones, total = zeros[active], ones[active], total[active]
    entropy = -np.sum(xlogy(zeros, zeros / total) + xlogy(ones, ones / total))

    def objective(split):
        row = split[:count] - split[count:]
        logits = features @ row
        value = total @ np.logaddexp(0, logits) - ones @ logits
        derivative = features.T @ (total * expit(logits) - ones)
        return value, np.r_[derivative, -derivative]

    result = minimize(objective, np.zeros(2 * count), jac=True, method='SLSQP',
                      bounds=[(0, LIMIT)] * (2 * count),
                      constraints={'type': 'ineq', 'fun': lambda split: LIMIT - 2e-12 - split.sum(),
                                   'jac': lambda split: -np.ones(2 * count)},
                      options={'maxiter': 120, 'ftol': 1e-10})
    return result.x[:count] - result.x[count:], float(result.fun - entropy)


def greedy_order(probability, random, temperature=0):
    remaining = list(range(16))
    reverse_order = []
    fitted = {}
    total_error = 0.0
    while remaining:
        choices = []
        for site in remaining:
            parents = [parent for parent in remaining if parent != site]
            row, error = fit_row(probability, site, parents)
            choices.append((error + temperature * random.gumbel(), error, site, parents, row))
        _, error, site, parents, row = min(choices, key=lambda choice: choice[0])
        fitted[site] = dict(zip(parents, row))
        reverse_order.append(site)
        remaining.remove(site)
        total_error += error
    order = reverse_order[::-1]
    weights = np.zeros((16, 16))
    for position, site in enumerate(order):
        for parent_position, parent in enumerate(order[:position]):
            weights[position, parent_position] = fitted[site][parent]
    lengths = np.abs(weights).sum(axis=1)
    weights *= np.minimum(1, (LIMIT - 1e-12) / np.maximum(lengths, 1e-100))[:, None]
    return order, weights, total_error


def search(source, count, seed, prefix, iterations=80, mode='shuffle'):
    random = np.random.default_rng(seed)
    original = json.loads(Path(source).read_text())
    original_roots = list(original['order'])
    if mode == 'root_free':
        original_roots = original_roots[-4:] + original_roots[:-4]
    best = original
    best_score = evaluate(best)['core_score']
    start = time.time()
    for trial in range(count):
        original = best if trial % 4 else json.loads(Path(source).read_text())
        report, (energy, proposal, target, logq, gradient) = evaluate(original, True)
        witness = dict(original)
        if mode == 'greedy':
            order, weights, error = greedy_order(proposal, random, .0001 * (trial % 4))
        else:
            order = list(original['order'])
            if mode == 'insert':
                site = original_roots[-4 + trial % 4]
                order.remove(site)
                order.insert([4, 8, 11][(trial // 4) % 3], site)
            elif mode in ['root', 'root_free']:
                root = original_roots[trial % 16]
                order = [root] + [site for site in order if site != root]
            elif trial % 3 == 0:
                swap = random.choice(np.arange(1, 12), 2, replace=False)
                order[swap[0]], order[swap[1]] = order[swap[1]], order[swap[0]]
            elif trial % 3 == 1:
                order[1:12] = random.permutation(order[1:12]).tolist()
            else:
                swap = random.choice(16, 2, replace=False)
                order[swap[0]], order[swap[1]] = order[swap[1]], order[swap[0]]
            weights = fit_target(proposal, order)
        witness.update(order=order, weights=weights.tolist())
        witness, _, _ = best_sector(witness, strict=False)
        print('initial', trial, round(time.time() - start, 1), evaluate(witness), flush=True)
        result = minimax(witness, iterations, output=f'{prefix}_{trial}.json', verbose=False)
        result, _, _ = best_sector(result, strict=False)
        result_score = evaluate(result)['core_score']
        print('result', trial, round(time.time() - start, 1), evaluate(result), flush=True)
        if result_score > best_score:
            best, best_score = result, result_score
            Path(prefix + '_best.json').write_text(json.dumps(best))
    return best


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--count', type=int, default=10)
    parser.add_argument('--seed', type=int, default=715)
    parser.add_argument('--prefix', default='orders')
    parser.add_argument('--iterations', type=int, default=80)
    parser.add_argument('--mode', default='shuffle')
    arguments = parser.parse_args()
    search(arguments.source, arguments.count, arguments.seed, arguments.prefix, arguments.iterations, arguments.mode)
