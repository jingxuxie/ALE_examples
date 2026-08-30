import json
import math
from pathlib import Path

import numpy as np
from scipy.special import expit, logsumexp


BOUND = math.log(9999)
EDGES = [edge for site in range(16) for edge in
         [(site, 4 * (site // 4) + (site + 1) % 4), (site, (site + 4) % 16)]]
STATES = (1 - 2 * ((np.arange(65536)[:, None] >> np.arange(16)) & 1)).astype(np.float64)
PRODUCTS = np.array([STATES[:, first] * STATES[:, second] for first, second in EDGES]).T
LOWER = np.tril_indices(16, -1)


def frustrated_count(bonds):
    count = 0
    for site in range(16):
        right = 4 * (site // 4) + (site + 1) % 4
        down = (site + 4) % 16
        count += bonds[2 * site] * bonds[2 * right + 1] * bonds[2 * down] * bonds[2 * site + 1] < 0
    return int(count)


def evaluate(witness, details=False):
    weights = np.asarray(witness['weights'], dtype=np.float64)
    ordered = STATES[:, witness['order']]
    logits = ordered @ weights.T
    logq = -np.logaddexp(0, -ordered * logits).sum(axis=1)
    proposal = np.exp(logq)
    energy = -PRODUCTS @ np.asarray(witness['bonds'], dtype=np.float64)
    potential = witness['beta'] * energy
    log_partition = logsumexp(-potential)
    target = np.exp(-potential - log_partition)
    reward = potential + logq
    reward_mean = proposal @ reward
    centered = reward - reward_mean
    gradient = ((proposal * centered)[:, None] * ((ordered + 1) / 2 - expit(logits))).T @ ordered
    distance = (16 - STATES @ np.asarray(witness['pattern'])) / 2
    sector = np.minimum(distance, 16 - distance) <= witness['radius']
    metrics = {
        'entropy': float(-proposal @ logq),
        'reverse_kl': float(reward_mean + log_partition),
        'reward_variance': float(proposal @ centered ** 2),
        'gradient_infinity': float(np.max(np.abs(gradient[LOWER]))),
        'energy_error_per_spin': float(abs((proposal - target) @ potential) / 16),
        'target_sector_mass': float(target @ sector),
        'proposal_sector_mass': float(proposal @ sector),
        'normalization': float(proposal.sum()),
        'symmetry_error': float(np.max(np.abs(proposal - proposal[::-1]))),
        'max_row_l1': float(np.max(np.abs(weights).sum(axis=1))),
        'frustrated_plaquettes': frustrated_count(witness['bonds']),
        'ground_energy': float(energy.min()),
        'ground_degeneracy': int(np.sum(energy == energy.min())),
        'mean_energy_q': float(proposal @ energy),
        'mean_energy_p': float(target @ energy),
    }
    scores = {
        'entropy': min(1, metrics['entropy'] / 3),
        'reverse_kl': min(1, metrics['reverse_kl'] / .4),
        'reward_variance': min(1, .05 / max(metrics['reward_variance'], 1e-300)),
        'gradient_infinity': min(1, .003 / max(metrics['gradient_infinity'], 1e-300)),
        'energy_error_per_spin': min(1, .02 / max(metrics['energy_error_per_spin'], 1e-300)),
        'target_sector_mass': min(1, metrics['target_sector_mass'] / .35),
        'proposal_sector_mass': min(1, .001 / max(metrics['proposal_sector_mass'], 1e-300)),
    }
    metrics['scores'] = scores
    metrics['worst_score'] = min(scores.values())
    metrics['passed'] = all(value >= 1 - 1e-10 for value in scores.values())
    if details:
        return metrics, proposal, target, gradient
    return metrics


def write_witness(path, bonds, beta, order, weights, pattern, radius):
    witness = {'schema_version': 1, 'bonds': list(map(int, bonds)), 'beta': float(beta),
               'order': list(map(int, order)), 'weights': np.asarray(weights).tolist(),
               'pattern': list(map(int, pattern)), 'radius': int(radius)}
    Path(path).write_text(json.dumps(witness, indent=2, allow_nan=False) + '\n')
    return witness


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('witness')
    arguments = parser.parse_args()
    print(json.dumps(evaluate(json.loads(Path(arguments.witness).read_text())), indent=2))
