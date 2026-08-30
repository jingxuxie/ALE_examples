import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.special import expit, logsumexp


LIMIT = math.log(99.0)
SITES = np.arange(16)
STATES = (2 * ((np.arange(65536)[:, None] >> SITES) & 1) - 1).astype(np.float64)
EDGES = [(site, 4 * (site // 4) + (site + 1) % 4) for site in range(16)]
EDGES = [edge for site in range(16) for edge in
         [(site, 4 * (site // 4) + (site + 1) % 4), (site, (site + 4) % 16)]]
FEATURES = np.column_stack([STATES[:, first] * STATES[:, second] for first, second in EDGES])
LOWER = np.tril_indices(16, -1)


def frustration(bonds):
    return sum(bonds[2 * site] * bonds[2 * (4 * (site // 4) + (site + 1) % 4) + 1]
               * bonds[2 * ((site + 4) % 16)] * bonds[2 * site + 1] < 0
               for site in range(16))


def evaluate(witness, details=False):
    bonds = np.asarray(witness['bonds'])
    weights = np.asarray(witness['weights'], dtype=np.float64)
    ordered = STATES[:, witness['order']]
    energy = -FEATURES @ bonds
    dimensionless = witness['beta'] * energy
    log_partition = logsumexp(-dimensionless)
    log_target = -dimensionless - log_partition
    target = np.exp(log_target)
    logits = ordered @ weights.T
    log_proposal = -np.logaddexp(0.0, -ordered * logits).sum(axis=1)
    proposal = np.exp(log_proposal)
    reward = dimensionless + log_proposal
    mean_reward = proposal @ reward
    centered = reward - mean_reward
    scores = ((ordered + 1.0) / 2.0 - expit(logits)) * (proposal * centered)[:, None]
    gradient = scores.T @ ordered
    distance = (STATES != witness['pattern']).sum(axis=1)
    sector = np.minimum(distance, 16 - distance) <= witness['radius']
    metrics = {
        'entropy': float(-proposal @ log_proposal),
        'reverse_kl': float(mean_reward + log_partition),
        'reward_variance': float(proposal @ (centered ** 2)),
        'gradient_infinity': float(np.max(np.abs(gradient[LOWER]))),
        'energy_error_per_spin': float(abs((proposal - target) @ dimensionless) / 16.0),
        'target_sector_mass': float(target @ sector),
        'proposal_sector_mass': float(proposal @ sector),
    }
    targets = [3.0, 0.4, 0.05, 0.003, 0.02, 0.35, 0.001]
    lower_bounds = [True, True, False, False, False, True, False]
    gate_scores = {key: min(1.0, value / threshold if lower else threshold / value if value else 1.0)
                   for (key, value), threshold, lower in zip(metrics.items(), targets, lower_bounds)}
    report = dict(metrics, gate_scores=gate_scores, core_score=min(gate_scores.values()),
                  frustrated=int(frustration(bonds)), row_l1_max=float(np.abs(weights).sum(axis=1).max()),
                  normalization=float(proposal.sum()),
                  symmetry_error=float(np.max(np.abs(proposal - proposal[::-1]))),
                  mean_energy_q=float(proposal @ energy), mean_energy_p=float(target @ energy),
                  ground_energy=float(energy.min()), ground_degeneracy=int((energy == energy.min()).sum()))
    report['passed'] = min(gate_scores.values()) >= 1.0 - 1e-10
    if details:
        return report, (energy, proposal, target, log_proposal, gradient)
    return report


if __name__ == '__main__':
    source = Path(sys.argv[1])
    report = evaluate(json.loads(source.read_text()))
    print(json.dumps(report, indent=2))
