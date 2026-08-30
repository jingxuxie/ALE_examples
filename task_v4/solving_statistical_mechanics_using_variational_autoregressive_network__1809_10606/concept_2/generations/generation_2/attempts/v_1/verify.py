import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
import json
import math
import resource
import time
from pathlib import Path
import numpy as np
from scipy.special import expit, log_expit, logsumexp

def verify(path):
    started = time.perf_counter()
    raw = path.read_bytes()
    assert len(raw) <= 131072 and path.is_file() and not path.is_symlink()
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            assert key not in result
            result[key] = value
        return result
    witness = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object)
    assert set(witness) == {'schema_version', 'bonds', 'beta', 'order', 'weights', 'pattern', 'radius'}
    assert type(witness['schema_version']) is int and witness['schema_version'] == 1
    assert type(witness['bonds']) is list and len(witness['bonds']) == 32
    assert all(type(value) is int and value in (-1, 1) for value in witness['bonds'])
    assert type(witness['order']) is list and len(witness['order']) == 16
    assert all(type(value) is int for value in witness['order'])
    assert sorted(witness['order']) == list(range(16))
    assert type(witness['pattern']) is list and len(witness['pattern']) == 16
    assert all(type(value) is int and value in (-1, 1) for value in witness['pattern'])
    assert type(witness['radius']) is int and witness['radius'] in (2, 3, 4)
    assert type(witness['beta']) in (int, float) and math.isfinite(witness['beta'])
    assert 1 <= witness['beta'] <= 3
    assert type(witness['weights']) is list and len(witness['weights']) == 16
    for row in witness['weights']:
        assert type(row) is list and len(row) == 16
        assert all(type(value) in (int, float) and math.isfinite(value) for value in row)
    weights = np.asarray(witness['weights'], dtype=np.float64)
    assert np.all(np.triu(weights) == 0)
    row_norms = np.abs(weights).sum(axis=1)
    assert np.max(row_norms) <= math.log(999)
    frustrated = 0
    bonds = witness['bonds']
    for row in range(4):
        for column in range(4):
            site = 4*row+column
            right = 4*row+(column+1)%4
            below = 4*((row+1)%4)+column
            product = bonds[2*site]*bonds[2*right+1]*bonds[2*below]*bonds[2*site+1]
            frustrated += product == -1
    assert 4 <= frustrated <= 12

    states = np.arange(65536, dtype=np.uint16)
    bits = np.unpackbits(states.astype('<u2').view(np.uint8).reshape(-1, 2), axis=1, bitorder='little')
    spins = 2*bits.astype(np.float64)-1
    energy = np.zeros(65536, dtype=np.float64)
    for row in range(4):
        for column in range(4):
            site = 4*row+column
            energy -= bonds[2*site]*spins[:, site]*spins[:, 4*row+(column+1)%4]
            energy -= bonds[2*site+1]*spins[:, site]*spins[:, 4*((row+1)%4)+column]
    potential = witness['beta']*energy
    logz = logsumexp(-potential)
    target = np.exp(-potential-logz)
    ordered = spins[:, witness['order']]
    logits = np.zeros_like(ordered)
    logq = np.zeros(65536, dtype=np.float64)
    for position in range(16):
        logits[:, position] = ordered[:, :position] @ weights[position, :position]
        logq += log_expit(ordered[:, position]*logits[:, position])
    proposal = np.exp(logq)
    normalization = math.fsum(proposal)
    symmetry = float(np.max(np.abs(proposal-proposal[::-1])))
    assert abs(normalization-1) <= 1e-10
    assert symmetry <= 1e-12
    minimum_conditional = float(np.min(expit(-np.abs(logits))))
    assert minimum_conditional >= .001
    reward = potential+logq
    mean_reward = math.fsum(proposal*reward)
    centered = reward-mean_reward
    gradient = np.zeros((16, 16), dtype=np.float64)
    for position in range(1, 16):
        residual = np.where(ordered[:, position] == 1,
                            expit(-logits[:, position]), -expit(logits[:, position]))
        for previous in range(position):
            gradient[position, previous] = math.fsum(proposal*centered*residual*ordered[:, previous])
    distance = np.count_nonzero(spins != np.asarray(witness['pattern']), axis=1)
    sector = np.minimum(distance, 16-distance) <= witness['radius']
    measured = {
        'entropy': -math.fsum(proposal*logq),
        'reverse_kl': math.fsum(proposal*(logq+potential+logz)),
        'reward_variance': math.fsum(proposal*centered**2),
        'gradient_infinity': float(np.max(np.abs(gradient))),
        'energy_error_per_spin': abs(math.fsum((proposal-target)*potential))/16,
        'target_sector_mass': math.fsum(target[sector]),
        'proposal_sector_mass': math.fsum(proposal[sector]),
    }
    targets = {'entropy': ('min', 3.), 'reverse_kl': ('min', .4),
               'reward_variance': ('max', .05), 'gradient_infinity': ('max', .003),
               'energy_error_per_spin': ('max', .02), 'target_sector_mass': ('min', .35),
               'proposal_sector_mass': ('max', .001)}
    gates = {name: {'value': measured[name], 'direction': direction, 'threshold': threshold,
                   'passed': measured[name] >= threshold-1e-10 if direction == 'min'
                             else measured[name] <= threshold+1e-10}
             for name, (direction, threshold) in targets.items()}

    strongest = np.unravel_index(np.argmax(np.abs(gradient)), gradient.shape)
    step = 1e-5
    finite_differences = {}
    for coordinate in [tuple(int(value) for value in strongest), (1, 0), (15, 5)]:
        position, previous = coordinate
        old_terms = log_expit(ordered[:, position]*logits[:, position])
        values = []
        for sign in (1, -1):
            perturbed_logit = logits[:, position]+sign*step*ordered[:, previous]
            perturbed_logq = logq-old_terms+log_expit(ordered[:, position]*perturbed_logit)
            perturbed_q = np.exp(perturbed_logq)
            values.append(math.fsum(perturbed_q*(potential+perturbed_logq+logz)))
        numerical = (values[0]-values[1])/(2*step)
        exact = float(gradient[coordinate])
        assert abs(numerical-exact) < 1e-7
        finite_differences[str(coordinate)] = {'analytic': exact, 'central_difference': numerical}
    report = {
        'valid': True,
        'passed': all(gate['passed'] for gate in gates.values()),
        'enumerated_configurations': len(states),
        'gates': gates,
        'validation': {'frustrated_plaquettes': frustrated,
                       'beta': witness['beta'], 'row_l1_max': float(np.max(row_norms)),
                       'row_l1_bound': math.log(999), 'minimum_conditional_probability': minimum_conditional,
                       'proposal_normalization': normalization, 'spin_flip_symmetry_error': symmetry,
                       'minimum_configuration_probability': float(np.min(proposal)),
                       'sector_configuration_count': int(sector.sum()),
                       'json_bytes': len(raw), 'gradient_finite_differences': finite_differences},
        'wall_seconds': time.perf_counter()-started,
        'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    assert report['passed'], report
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('witness', nargs='?', default='witness.json', type=Path)
    parser.add_argument('--report', default='verification.json', type=Path)
    arguments = parser.parse_args()
    result = verify(arguments.witness)
    text = json.dumps(result, indent=2, allow_nan=False)+'\n'
    arguments.report.write_text(text)
    print(text, end='')
