import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from exact import STATES, FEATURES, LIMIT, evaluate, EDGES


def distance_transform(sources):
    distance = np.full(65536, 32, dtype=np.int8)
    distance[sources] = 0
    distance[65535 - np.asarray(sources)] = 0
    indices = np.arange(65536)
    for spin in range(16):
        distance = np.minimum(distance, distance[indices ^ (1 << spin)] + 1)
    return distance


def fit_target(probability, order):
    weights = np.zeros((16, 16))
    prefixes = np.zeros(65536, dtype=np.int32)
    for position, site in enumerate(order):
        prefixes += (STATES[:, site] > 0).astype(np.int32) << position
        if position == 0:
            continue
        counts = np.bincount(prefixes, weights=probability, minlength=1 << (position + 1))
        zeros = counts[:1 << position]
        ones = counts[1 << position:]
        total = zeros + ones
        active = total > 1e-13
        features = (2 * ((np.arange(1 << position)[active, None] >> np.arange(position)) & 1) - 1).astype(float)
        total = total[active]
        ones = ones[active]

        def objective(split):
            row = split[:position] - split[position:]
            logits = features @ row
            value = total @ np.logaddexp(0, logits) - ones @ logits
            derivative = features.T @ (total * expit(logits) - ones)
            return value, np.r_[derivative, -derivative]

        solution = minimize(objective, np.zeros(position * 2), jac=True, method='SLSQP',
                            bounds=[(0, LIMIT)] * (position * 2),
                            constraints={'type': 'ineq', 'fun': lambda split: LIMIT - 1e-12 - split.sum(),
                                         'jac': lambda split: -np.ones(position * 2)},
                            options={'maxiter': 150, 'ftol': 1e-11})
        weights[position, :position] = solution.x[:position] - solution.x[position:]
    lengths = np.abs(weights).sum(axis=1)
    weights *= np.minimum(1, (LIMIT - 1e-12) / np.maximum(lengths, 1e-100))[:, None]
    return weights


def make_target(candidate, beta, softness=5):
    energy = -FEATURES @ candidate['bonds']
    distance = distance_transform(candidate['cluster'])
    outside = np.flatnonzero((energy == energy.min()) & (distance > 0))
    other_distance = distance_transform(outside)
    probability = np.exp(-beta * (energy - energy.min())) * expit(softness * (other_distance - distance))
    probability /= probability.sum()
    return probability


def search(candidates, count, seed, prefix):
    random = np.random.default_rng(seed)
    records = []
    start = time.time()
    seen = set()
    for index, candidate in enumerate(candidates):
        key = (tuple(candidate['bonds']), tuple(sorted(candidate['cluster'])))
        if key in seen:
            continue
        seen.add(key)
        if len(seen) > count:
            break
        cluster_spins = STATES[candidate['cluster']]
        correlation = cluster_spins.T @ cluster_spins / len(cluster_spins)
        certainty = (correlation ** 2).sum(axis=1)
        for trial in range(4):
            beta = [1.0, 1.1, 1.2, 1.05][trial]
            if trial < 2:
                order = np.argsort(-(certainty + random.random(16) * .3)).tolist()
            else:
                order = random.permutation(16).tolist()
            target = make_target(candidate, beta)
            weights = fit_target(target, order)
            witness = {'schema_version': 1, 'bonds': candidate['bonds'], 'beta': beta,
                       'order': order, 'weights': weights.tolist(), 'pattern': candidate['pattern'],
                       'radius': candidate['radius']}
            report = evaluate(witness)
            records.append((report['core_score'], witness, report))
            records.sort(key=lambda record: -record[0])
            records = records[:30]
            Path(prefix + '_best.json').write_text(json.dumps(records[0][1]))
            Path(prefix + '_records.json').write_text(json.dumps(records))
            print(len(seen), trial, round(time.time() - start, 1),
                  {key: round(report[key], 6) for key in ['core_score', 'reward_variance', 'gradient_infinity',
                   'entropy', 'energy_error_per_spin', 'target_sector_mass', 'proposal_sector_mass']}, flush=True)
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', default='survey.json')
    parser.add_argument('--count', type=int, default=50)
    parser.add_argument('--seed', type=int, default=121)
    parser.add_argument('--prefix', default='fit')
    arguments = parser.parse_args()
    search(json.loads(Path(arguments.source).read_text()), arguments.count, arguments.seed, arguments.prefix)
