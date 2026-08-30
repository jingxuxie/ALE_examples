import argparse
import json
from pathlib import Path

import numpy as np
from scipy.special import expit, logsumexp


BOUND = float(np.log(99.0))
EDGES = np.array([(site, neighbor) for site in range(16) for neighbor in
                  (4 * (site // 4) + (site + 1) % 4, (site + 4) % 16)])
STATES = (2 * ((np.arange(65536)[:, None] >> np.arange(16)) & 1) - 1).astype(float)
PRODUCTS = STATES[:, EDGES[:, 0]] * STATES[:, EDGES[:, 1]]
LOWER = np.tril_indices(16, -1)


def frustrated(bonds):
    result = []
    for site in range(16):
        right = 4 * (site // 4) + (site + 1) % 4
        down = (site + 4) % 16
        result.append(int(bonds[2 * site] * bonds[2 * right + 1] *
                          bonds[2 * down] * bonds[2 * site + 1]) == -1)
    return int(sum(result))


def evaluate(witness, return_arrays=False):
    assert set(witness) == {'schema_version', 'bonds', 'beta', 'order', 'weights', 'pattern', 'radius'}
    assert type(witness['schema_version']) is int and witness['schema_version'] == 1
    assert type(witness['radius']) is int and witness['radius'] in (2, 3, 4)
    assert len(witness['bonds']) == 32 and all(type(value) is int and value in (-1, 1) for value in witness['bonds'])
    assert len(witness['pattern']) == 16 and all(type(value) is int and value in (-1, 1) for value in witness['pattern'])
    assert all(type(value) is int for value in witness['order']) and sorted(witness['order']) == list(range(16))
    assert type(witness['beta']) in (int, float) and 1 <= witness['beta'] <= 3
    assert len(witness['weights']) == 16 and all(len(row) == 16 for row in witness['weights'])
    assert all(type(value) in (int, float) for row in witness['weights'] for value in row)
    weights = np.array(witness['weights'], dtype=float)
    assert weights.shape == (16, 16) and np.isfinite(weights).all()
    assert (np.triu(weights) == 0).all()
    row_l1 = np.abs(weights).sum(axis=1)
    assert row_l1.max() <= BOUND, (row_l1.max(), BOUND)
    frustration = frustrated(witness['bonds'])
    assert 4 <= frustration <= 12
    energy = -PRODUCTS @ witness['bonds']
    potential = witness['beta'] * energy
    log_partition = float(logsumexp(-potential))
    log_target = -potential - log_partition
    target = np.exp(log_target)
    spins = STATES[:, witness['order']]
    logits = spins @ weights.T
    log_proposal = -np.logaddexp(0, -spins * logits).sum(axis=1)
    proposal = np.exp(log_proposal)
    reward = potential + log_proposal
    centered = reward - proposal @ reward
    residual = (spins + 1) / 2 - expit(logits)
    gradients = (residual.T * (proposal * centered)) @ spins
    distance = np.count_nonzero(STATES != witness['pattern'], axis=1)
    sector = np.minimum(distance, 16 - distance) <= witness['radius']
    metrics = {
        'entropy': float(-proposal @ log_proposal),
        'reverse_kl': float(proposal @ (log_proposal - log_target)),
        'reward_variance': float(proposal @ centered ** 2),
        'gradient_infinity': float(np.max(np.abs(gradients[LOWER]))),
        'energy_error_per_spin': float(abs((proposal - target) @ potential) / 16),
        'target_sector_mass': float(target[sector].sum()),
        'proposal_sector_mass': float(proposal[sector].sum()),
    }
    thresholds = {'entropy': (3, True), 'reverse_kl': (0.4, True),
                  'reward_variance': (0.05, False), 'gradient_infinity': (0.003, False),
                  'energy_error_per_spin': (0.02, False), 'target_sector_mass': (0.35, True),
                  'proposal_sector_mass': (0.001, False)}
    scores = {name: min(1.0, metrics[name] / threshold if lower else
                       threshold / metrics[name] if metrics[name] > 0 else 1.0)
              for name, (threshold, lower) in thresholds.items()}
    failing = [name for name, (threshold, lower) in thresholds.items()
               if (metrics[name] < threshold - 1e-10 if lower else metrics[name] > threshold + 1e-10)]
    normalization = float(proposal.sum())
    symmetry = float(np.max(np.abs(proposal - proposal[::-1])))
    result = {'metrics': metrics, 'scores': scores, 'core_score': min(scores.values()),
              'failing_gates': failing, 'passed': not failing and abs(normalization - 1) <= 1e-10 and symmetry <= 1e-12,
              'validation': {'frustrated_plaquettes': frustration, 'max_row_l1': float(row_l1.max()),
                             'normalization': normalization, 'symmetry_error': symmetry,
                             'minimum_conditional': float(expit(-np.max(np.abs(logits)))),
                             'target_entropy': float(-target @ log_target),
                             'ground_energy': float(energy.min()),
                             'ground_degeneracy': int(np.count_nonzero(energy == energy.min())),
                             'proposal_mean_energy': float(proposal @ energy),
                             'target_mean_energy': float(target @ energy)}}
    if return_arrays:
        return result, target, proposal, energy, gradients
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('witness', type=Path)
    parser.add_argument('--output', type=Path)
    arguments = parser.parse_args()
    result = evaluate(json.loads(arguments.witness.read_text()))
    text = json.dumps(result, indent=2, allow_nan=False)
    print(text)
    if arguments.output:
        arguments.output.write_text(text + '\n')


if __name__ == '__main__':
    main()
