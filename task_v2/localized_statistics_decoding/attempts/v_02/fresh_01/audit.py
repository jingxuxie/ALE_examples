import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
from scipy.special import expit

from inference import Network, decode_case, dynamic_table, enumeration_table, hadamard, reduce_internal
from train import Calibration
from validate import compare


def brute_case(case, model):
    fault_count = len(case['faults'])
    patterns = ((np.arange(1 << fault_count)[:, None] >> np.arange(fault_count)) & 1).astype(np.uint8)
    detector_matrix = np.array([[int(detector in fault['detectors']) for fault in case['faults']]
                                for detector in range(case['num_detectors'])], dtype=np.uint8)
    syndromes = (patterns @ detector_matrix.T) % 2
    labels = np.zeros(len(patterns), dtype=np.int64)
    for index, fault in enumerate(case['faults']):
        labels ^= patterns[:, index].astype(np.int64) * fault['logical_mask']
    emissions, logical, queries = [], [], []
    modes = len(model['initial'])
    for shot in case['shots']:
        selected = np.ones(len(patterns), dtype=bool)
        for detector, bit in enumerate(shot['syndrome']):
            if bit is not None:
                selected &= syndromes[:, detector] == bit
        probabilities = np.array([[expit(model['offsets'][mode][fault['rate_group']] + model['slopes'][fault['rate_group']] * shot['dose'] + fault['bias'])
                                   for fault in case['faults']] for mode in range(modes)])
        weights = np.exp(patterns[selected] @ (np.log(probabilities) - np.log1p(-probabilities)).T + np.log1p(-probabilities).sum(axis=1))
        emission = weights.sum(axis=0)
        emissions.append(emission)
        logical.append(np.stack([np.bincount(labels[selected], weights=weights[:, mode], minlength=1 << case['num_observables']) / emission[mode]
                                 for mode in range(modes)]))
        queries.append(np.stack([((patterns[selected][:, query['faults']].sum(axis=1) % 2) @ weights) / emission
                                 for query in shot['queries']], axis=1))
    posterior = np.zeros((len(case['shots']), modes))
    switches = np.zeros(len(case['shots']) - 1)
    evidence = 0.0
    for path in itertools.product(range(modes), repeat=len(case['shots'])):
        weight = model['initial'][path[0]] * emissions[0][path[0]]
        for shot in range(1, len(path)):
            weight *= model['transition'][path[shot - 1]][path[shot]] * emissions[shot][path[shot]]
        evidence += weight
        for shot, mode in enumerate(path):
            posterior[shot, mode] += weight
        for shot in range(len(path) - 1):
            switches[shot] += weight * (path[shot] != path[shot + 1])
    posterior /= evidence
    outputs = []
    for index, shot in enumerate(case['shots']):
        distribution = posterior[index] @ logical[index]
        probability = posterior[index] @ queries[index]
        outputs.append({'id': shot['id'], 'logical_posterior': distribution.tolist(),
                        'logical_decision': int(distribution.argmax()),
                        'query_probability': {query['id']: float(probability[query_index]) for query_index, query in enumerate(shot['queries'])}})
    return {'id': case['id'], 'log_evidence': float(np.log(evidence)), 'switch_probability': (switches / evidence).tolist(), 'shots': outputs}


def stress_case(model, dense=False):
    generator = np.random.default_rng(82719)
    region_count = 10
    detectors_per_region = 22
    faults = []
    supports = []
    for region in range(region_count):
        core = np.concatenate([np.eye(20, dtype=np.uint8), generator.integers(0, 2, size=(20, 7), dtype=np.uint8)], axis=1)
        dependent = (generator.integers(0, 2, size=(2, 20), dtype=np.uint8) @ core) % 2
        matrix = np.concatenate([core, dependent], axis=0)
        supports.append(matrix)
        for column in range(27):
            faults.append({'detectors': (region * detectors_per_region + np.flatnonzero(matrix[:, column])).tolist(),
                           'logical_mask': int(generator.integers(0, 16)), 'rate_group': int(generator.integers(0, 3)),
                           'bias': float(generator.choice([-0.25, 0.0, 0.25]))})
    if dense:
        edges = [(left, right) for left in range(region_count) for right in range(left + 1, region_count)
                 if not (left % 2 == 0 and right == left + 1)]
    else:
        edges = [(region, (region + distance) % region_count) for region in range(region_count) for distance in (1, 2)] * 2
    for edge in edges:
        detectors = []
        for region in edge:
            support = np.bitwise_xor.reduce(supports[region][:, generator.choice(27, size=3, replace=False)], axis=1)
            detectors.extend((region * detectors_per_region + np.flatnonzero(support)).tolist())
        faults.append({'detectors': detectors, 'logical_mask': int(generator.integers(0, 16)),
                       'rate_group': int(generator.integers(0, 3)), 'bias': float(generator.choice([-0.25, 0.0, 0.25]))})
    faults.append({'detectors': [], 'logical_mask': 9, 'rate_group': 0, 'bias': 0.1})
    shots = []
    mode = int(generator.choice(len(model['initial']), p=model['initial']))
    for shot_index, dose in enumerate([-1.4, 1.4, 0.3, -0.6, 1.1, -1.2, 0.0, 1.4]):
        probability = np.array([expit(model['offsets'][mode][fault['rate_group']] + model['slopes'][fault['rate_group']] * dose + fault['bias'])
                                for fault in faults])
        errors = generator.random(len(faults)) < probability
        syndrome = np.zeros(region_count * detectors_per_region, dtype=np.uint8)
        for index in np.flatnonzero(errors):
            syndrome[faults[index]['detectors']] ^= 1
        syndrome = syndrome.tolist()
        if shot_index:
            for detector in generator.choice(len(syndrome), size=15, replace=False):
                syndrome[detector] = None
        queries = [{'id': 'local', 'faults': [0]}, {'id': 'alias', 'faults': [1, 3]},
                   {'id': 'boundary', 'faults': [271]}, {'id': 'mixed', 'faults': [23, 88, 200, 287, 310]},
                   {'id': 'silent', 'faults': [310]}, {'id': 'nonlocal', 'faults': [54, 136, 212, 309]}]
        shots.append({'id': 'shot_' + str(shot_index), 'dose': dose, 'syndrome': syndrome, 'queries': queries})
        mode = int(generator.choice(len(model['initial']), p=model['transition'][mode]))
    return {'id': 'synthetic_dense' if dense else 'synthetic_circulant', 'num_detectors': 220, 'num_observables': 4,
            'detector_regions': np.repeat(np.arange(10), 22).tolist(), 'faults': faults, 'shots': shots}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', required=True)
    parser.add_argument('--output-dir', default=str(Path(__file__).parent))
    arguments = parser.parse_args()
    source, destination = Path(arguments.input_dir), Path(arguments.output_dir)
    model = json.loads((destination / 'model.json').read_text())
    micro = json.loads((source / 'micro.json').read_text())
    brute = {'cases': [brute_case(case, model) for case in micro['cases']]}
    actual = {'cases': [decode_case(case, model) for case in micro['cases']]}
    report = {'brute_force_checks': compare(brute, actual, micro)}
    generator = np.random.default_rng(62104)
    maximum_error = 0.0
    for _ in range(40):
        internal_count = int(generator.integers(1, 14))
        rows = int(generator.integers(0, 9))
        boundary_count = int(generator.integers(0, 5))
        matrix = generator.integers(0, 2, (rows, internal_count), dtype=np.uint8)
        right = generator.integers(0, 2, (rows, boundary_count + 1), dtype=np.uint8)
        matrix, right, pivots = reduce_internal(matrix, right)
        bits = ((np.arange(1 << boundary_count)[:, None] >> np.arange(boundary_count - 1, -1, -1)) & 1).astype(np.uint8)
        probabilities = generator.uniform(0.01, 0.8, (3, internal_count))
        labels = generator.integers(0, 16, internal_count)
        membership = generator.integers(0, 2, (6, internal_count), dtype=np.uint8)
        table_arguments = (matrix, right, pivots, bits, probabilities, labels, membership, hadamard(16))
        maximum_error = max(maximum_error, float(np.max(np.abs(enumeration_table(*table_arguments) - dynamic_table(*table_arguments)))))
    report['local_enumeration_vs_dynamic_max_abs'] = maximum_error
    records = np.load(source / 'calibration_records.npz')
    metadata = json.loads((source / 'calibration.json').read_text())
    small = Calibration(metadata, records['setting'][:64].astype(int), records['syndrome'][:64].astype(int))
    chosen = next(item for item in json.loads((destination / 'calibration_comparison.json').read_text()) if item['modes'] == 3 and item['kind'] == 'hmm')
    parameters = np.array(chosen['parameters'])
    value, gradient = small.evaluate(parameters, 3, 'hmm')
    numeric = np.empty_like(gradient)
    for index in range(len(parameters)):
        shift = np.zeros_like(parameters)
        shift[index] = 1e-5
        numeric[index] = (small.evaluate(parameters + shift, 3, 'hmm')[0] - small.evaluate(parameters - shift, 3, 'hmm')[0]) / 2e-5
    report['calibration_gradient_max_abs'] = float(np.max(np.abs(numeric - gradient)))
    permutation = np.random.default_rng(7143).permutation(len(records['setting']))
    holdout_indices = permutation[int(0.8 * len(permutation)):]
    holdout = Calibration(metadata, records['setting'][holdout_indices].astype(int), records['syndrome'][holdout_indices].astype(int))
    selected_likelihood = holdout.evaluate(parameters, 3, 'hmm', gradient=False, per_sequence=True)
    comparisons = []
    complete = Calibration(metadata, records['setting'].astype(int), records['syndrome'].astype(int))
    validation = json.loads((source / 'validation.json').read_text())
    expected = json.loads((source / 'validation_expected.json').read_text())
    for candidate in json.loads((destination / 'calibration_comparison.json').read_text()):
        modes, kind = candidate['modes'], candidate['kind']
        likelihood = holdout.evaluate(np.array(candidate['parameters']), modes, kind, gradient=False, per_sequence=True)
        difference = selected_likelihood - likelihood
        comparisons.append({'modes': modes, 'kind': kind, 'selected_log_likelihood_gain_per_sequence': float(difference.mean()),
                            'paired_standard_error': float(difference.std(ddof=1) / np.sqrt(len(difference)))})
        if (modes, kind) in [(1, 'iid'), (3, 'iid'), (2, 'hmm')]:
            fit = complete.fit(modes, kind, 0, np.array(candidate['parameters']), iterations=300)
            offsets, slopes, initial, transition = complete.unpack(fit.x, modes, kind)
            alternative = {'offsets': offsets.tolist(), 'slopes': slopes.tolist(), 'initial': initial.tolist(), 'transition': transition.tolist()}
            name = str(modes) + '_' + kind
            (destination / ('alternative_model_' + name + '.json')).write_text(json.dumps(alternative, indent=2) + '\n')
            prediction = {'cases': [decode_case(case, alternative) for case in validation['cases']]}
            (destination / ('alternative_predictions_' + name + '.json')).write_text(json.dumps(prediction, indent=2) + '\n')
            report['deployment_' + name] = compare(expected, prediction, validation)
    report['paired_holdout_comparisons'] = comparisons
    stress = stress_case(model)
    (destination / 'synthetic_stress.json').write_text(json.dumps({'cases': [stress]}) + '\n')
    report['stress_network'] = {'faults': len(stress['faults']), 'detectors': stress['num_detectors'],
                               'observables': stress['num_observables'], 'shots': len(stress['shots']),
                               'boundary_elimination_width': Network(stress).width}
    (destination / 'audit_results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
