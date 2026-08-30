import argparse
import itertools
import json
import math
import time
from pathlib import Path


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def is_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def load_and_validate(path):
    assert path.is_file() and not path.is_symlink()
    assert path.stat().st_size <= 131072
    witness = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_object)
    assert type(witness) is dict
    assert set(witness) == {'schema_version', 'bonds', 'beta', 'order', 'weights', 'pattern', 'radius'}
    assert type(witness['schema_version']) is int and witness['schema_version'] == 1
    assert type(witness['bonds']) is list and len(witness['bonds']) == 32
    assert all(type(value) is int and value in (-1, 1) for value in witness['bonds'])
    assert is_number(witness['beta']) and 1 <= witness['beta'] <= 3
    assert type(witness['order']) is list and len(witness['order']) == 16
    assert all(type(value) is int for value in witness['order'])
    assert sorted(witness['order']) == list(range(16))
    assert type(witness['weights']) is list and len(witness['weights']) == 16
    for position, row in enumerate(witness['weights']):
        assert type(row) is list and len(row) == 16
        assert all(is_number(value) for value in row)
        assert all(value == 0 for value in row[position:])
        assert math.fsum(abs(value) for value in row) <= math.log(9999)
    assert type(witness['pattern']) is list and len(witness['pattern']) == 16
    assert all(type(value) is int and value in (-1, 1) for value in witness['pattern'])
    assert type(witness['radius']) is int and witness['radius'] in (2, 3, 4)
    bonds = witness['bonds']
    frustration = []
    for row, column in itertools.product(range(4), repeat=2):
        site = 4 * row + column
        right = 4 * row + (column + 1) % 4
        down = 4 * ((row + 1) % 4) + column
        if bonds[2 * site] * bonds[2 * site + 1] * bonds[2 * right + 1] * bonds[2 * down] == -1:
            frustration.append(site)
    assert 4 <= len(frustration) <= 12
    return witness, frustration


def log_sigmoid(value):
    if value >= 0:
        return -math.log1p(math.exp(-value))
    return value - math.log1p(math.exp(value))


def verify(path):
    start = time.perf_counter()
    witness, frustration = load_and_validate(path)
    order = witness['order']
    weights = witness['weights']
    bonds = witness['bonds']
    beta = witness['beta']
    ordered_states = []
    score_factors = []
    energies = []
    potentials = []
    log_proposals = []
    proposal = []
    in_sector = []
    for state in itertools.product((-1, 1), repeat=16):
        ordered = tuple(state[site] for site in order)
        logits = [math.fsum(weights[position][parent] * ordered[parent] for parent in range(position))
                  for position in range(16)]
        log_proposal = math.fsum(log_sigmoid(spin * logit) for spin, logit in zip(ordered, logits))
        energy = 0
        for row, column in itertools.product(range(4), repeat=2):
            site = 4 * row + column
            right = 4 * row + (column + 1) % 4
            down = 4 * ((row + 1) % 4) + column
            energy -= bonds[2 * site] * state[site] * state[right]
            energy -= bonds[2 * site + 1] * state[site] * state[down]
        distance = sum(spin != center for spin, center in zip(state, witness['pattern']))
        ordered_states.append(ordered)
        score_factors.append(tuple((spin + 1) / 2 - 1 / (1 + math.exp(-logit))
                                   for spin, logit in zip(ordered, logits)))
        energies.append(energy)
        potentials.append(beta * energy)
        log_proposals.append(log_proposal)
        proposal.append(math.exp(log_proposal))
        in_sector.append(min(distance, 16 - distance) <= witness['radius'])
    minimum_potential = min(potentials)
    log_partition = -minimum_potential + math.log(math.fsum(math.exp(minimum_potential - potential)
                                                          for potential in potentials))
    target = [math.exp(-potential - log_partition) for potential in potentials]
    rewards = [potential + log_proposal for potential, log_proposal in zip(potentials, log_proposals)]
    mean_reward = math.fsum(probability * reward for probability, reward in zip(proposal, rewards))
    centered = [reward - mean_reward for reward in rewards]
    weighted_centered = [probability * residual for probability, residual in zip(proposal, centered)]
    gradients = []
    for position in range(16):
        for parent in range(position):
            gradient = math.fsum(coefficient * factors[position] * state[parent]
                                 for coefficient, factors, state in zip(weighted_centered, score_factors, ordered_states))
            gradients.append(gradient)
    metrics = {
        'entropy': -math.fsum(probability * log_proposal for probability, log_proposal in zip(proposal, log_proposals)),
        'reverse_kl': math.fsum(probability * (log_proposal + potential + log_partition)
                                for probability, log_proposal, potential in zip(proposal, log_proposals, potentials)),
        'reward_variance': math.fsum(probability * residual ** 2 for probability, residual in zip(proposal, centered)),
        'gradient_infinity': max(abs(gradient) for gradient in gradients),
        'energy_error_per_spin': abs(math.fsum((probability - target_probability) * potential
                                              for probability, target_probability, potential in zip(proposal, target, potentials))) / 16,
        'target_sector_mass': math.fsum(probability for probability, inside in zip(target, in_sector) if inside),
        'proposal_sector_mass': math.fsum(probability for probability, inside in zip(proposal, in_sector) if inside),
    }
    bounds = {
        'entropy': ('lower', 3),
        'reverse_kl': ('lower', .4),
        'reward_variance': ('upper', .05),
        'gradient_infinity': ('upper', .003),
        'energy_error_per_spin': ('upper', .02),
        'target_sector_mass': ('lower', .35),
        'proposal_sector_mass': ('upper', .001),
    }
    gates = {name: metrics[name] >= limit - 1e-10 if direction == 'lower' else metrics[name] <= limit + 1e-10
             for name, (direction, limit) in bounds.items()}
    scores = {name: min(1, metrics[name] / limit) if direction == 'lower'
              else min(1, limit / metrics[name]) if metrics[name] else 1
              for name, (direction, limit) in bounds.items()}
    normalization = math.fsum(proposal)
    symmetry = max(abs(first - second) for first, second in zip(proposal, reversed(proposal)))
    assert abs(normalization - 1) <= 1e-10
    assert symmetry <= 1e-12
    assert min(proposal) > 0
    ground_energy = min(energies)
    ground_indices = [index for index, energy in enumerate(energies) if energy == ground_energy]
    report = {
        'method': 'Independent standard-library exhaustive enumeration; no clipping or renormalization',
        'states_enumerated': len(proposal),
        'structurally_valid': True,
        'metrics': metrics,
        'gates': gates,
        'scores': scores,
        'worst_score': min(scores.values()),
        'passed': all(gates.values()),
        'normalization': normalization,
        'symmetry_error': symmetry,
        'minimum_state_probability': min(proposal),
        'maximum_row_l1': max(math.fsum(abs(value) for value in row) for row in weights),
        'minimum_conditional_probability_bound': 1 / (1 + math.exp(max(math.fsum(abs(value) for value in row) for row in weights))),
        'frustrated_plaquette_count': len(frustration),
        'frustrated_plaquettes': frustration,
        'ground_energy': ground_energy,
        'ground_degeneracy': len(ground_indices),
        'ground_states_in_sector': sum(in_sector[index] for index in ground_indices),
        'mean_energy_q': math.fsum(probability * energy for probability, energy in zip(proposal, energies)),
        'mean_energy_p': math.fsum(probability * energy for probability, energy in zip(target, energies)),
        'wall_seconds': time.perf_counter() - start,
    }
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('witness', nargs='?', type=Path, default=Path(__file__).resolve().parent / 'witness.json')
    parser.add_argument('--output', type=Path)
    arguments = parser.parse_args()
    report = verify(arguments.witness)
    text = json.dumps(report, indent=2, allow_nan=False) + '\n'
    print(text, end='')
    if arguments.output:
        arguments.output.write_text(text)
    raise SystemExit(0 if report['passed'] else 1)
