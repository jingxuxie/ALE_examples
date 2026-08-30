import argparse
import itertools
import json
import time
from pathlib import Path

import numpy as np
from scipy.special import expit, logsumexp

from exact import STATES, FEATURES, LOWER, evaluate, frustration
from sectors import ball_masses


def search(source, prefix, maximum=4):
    witness = json.loads(Path(source).read_text())
    report, (energy, proposal, target, logq, gradient) = evaluate(witness, True)
    start = time.time()
    features = FEATURES[32768:]
    probability = 2 * proposal[32768:]
    reward = witness['beta'] * energy[32768:] + logq[32768:]
    centered = reward - probability @ reward
    feature_mean = probability @ features
    features_centered = features - feature_mean
    covariance = features_centered.T @ (probability[:, None] * features_centered)
    reward_covariance = features_centered.T @ (probability * centered)
    spins = STATES[32768:, witness['order']]
    residual = (spins + 1) / 2 - expit(spins @ np.array(witness['weights']).T)
    scores = residual[:, LOWER[0]] * spins[:, LOWER[1]]
    gradient_features = scores.T @ (probability[:, None] * features_centered)
    original_gradient = gradient[LOWER]
    original_bonds = np.asarray(witness['bonds'])
    ranked = []
    for size in range(1, maximum + 1):
        combinations = list(itertools.combinations(range(32), size))
        for start_index in range(0, len(combinations), 2048):
            subset = combinations[start_index:start_index + 2048]
            changes = np.zeros((len(subset), 32))
            for index, combination in enumerate(subset):
                changes[index, list(combination)] = 2 * witness['beta'] * original_bonds[list(combination)]
            variances = report['reward_variance'] + 2 * changes @ reward_covariance + np.sum((changes @ covariance) * changes, axis=1)
            gradients = np.max(np.abs(original_gradient + changes @ gradient_features.T), axis=1)
            ratios = np.maximum(variances / .05, gradients / .003)
            for index in np.argsort(ratios)[:100]:
                ranked.append((float(ratios[index]), subset[index], float(variances[index]), float(gradients[index])))
    ranked.sort()
    print('ranked',time.time()-start,ranked[:10],flush=True)
    proposal_masses = ball_masses(proposal)
    records = []
    for ratio, combination, variance, grad in ranked[:500]:
        bonds = original_bonds.copy()
        bonds[list(combination)] *= -1
        if not 4 <= frustration(bonds) <= 12:
            continue
        energies = -FEATURES @ bonds
        beta = witness['beta']
        logz = logsumexp(-beta * energies)
        target = np.exp(-beta * energies - logz)
        energy_error = abs(beta * ((proposal - target) @ energies)) / 16
        reverse_kl = beta * proposal @ energies - report['entropy'] + logz
        if energy_error > .08 or reverse_kl < .2:
            continue
        target_masses = ball_masses(target)
        sector_scores = np.minimum(target_masses / .35, .001 / np.maximum(proposal_masses, 1e-100))
        choice = np.unravel_index(sector_scores.argmax(), sector_scores.shape)
        current = dict(witness, bonds=bonds.tolist(), radius=int(choice[0] + 2), pattern=STATES[choice[1]].astype(int).tolist())
        current_report = evaluate(current)
        records.append((current_report['core_score'], current, current_report))
    records.sort(key=lambda record: -record[0])
    Path(prefix + '_records.json').write_text(json.dumps(records))
    if records:
        Path(prefix + '_best.json').write_text(json.dumps(records[0][1]))
    print('finished',len(records),time.time()-start,flush=True)
    for record in records[:12]:
        print(record[2],flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('--prefix', default='bonds')
    parser.add_argument('--maximum', type=int, default=4)
    arguments = parser.parse_args()
    search(arguments.source, arguments.prefix, arguments.maximum)
