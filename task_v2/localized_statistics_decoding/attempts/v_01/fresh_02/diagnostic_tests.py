import argparse
import copy
import json
import math
import os
import time
from pathlib import Path

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'

import numpy as np

from inference import decode_case
from posterior import LocalModel
from validate import compare


def exhaustive(case):
    fault_count = len(case['faults'])
    configurations = np.arange(1 << fault_count, dtype=np.uint64)
    bits = ((configurations[:, None] >> np.arange(fault_count, dtype=np.uint64)) & 1).astype(np.uint8)
    records = np.zeros((len(bits), case['num_detectors']), dtype=np.uint8)
    labels = np.zeros(len(bits), dtype=np.int64)
    for index, fault in enumerate(case['faults']):
        records[:, fault['detectors']] ^= bits[:, index, None]
        labels ^= bits[:, index].astype(np.int64) * fault['logical_mask']
    modes = len(case['mode_prior'])
    rates = np.array([fault['probabilities'] for fault in case['faults']]).reshape(fault_count, modes)
    weights = np.prod(np.where(bits[:, :, None], rates[None, :, :], 1 - rates[None, :, :]), axis=1)
    evidence = np.empty((len(case['shots']), modes))
    logicals = []
    queries = []
    for shot_index, shot in enumerate(case['shots']):
        observed = [index for index, value in enumerate(shot['syndrome']) if value is not None]
        target = [shot['syndrome'][index] for index in observed]
        compatible = np.all(records[:, observed] == target, axis=1)
        conditional = weights * compatible[:, None]
        evidence[shot_index] = conditional.sum(axis=0)
        normalizer = np.where(evidence[shot_index] > 0, evidence[shot_index], 1)
        logicals.append(np.array([np.bincount(labels, weights=conditional[:, mode],
                                             minlength=1 << case['num_observables']) / normalizer[mode]
                                  for mode in range(modes)]))
        queries.append({query['id']: (((bits[:, query['faults']].sum(axis=1) % 2) @ conditional)
                                     / normalizer) for query in shot['queries']})
    mode_weights = np.asarray(case['mode_prior']) * evidence.prod(axis=0)
    total = mode_weights.sum()
    if total == 0:
        return None
    mode_weights /= total
    shots = []
    for index, shot in enumerate(case['shots']):
        logical = mode_weights @ logicals[index]
        shots.append({'id': shot['id'], 'logical_posterior': logical.tolist(),
                      'logical_decision': int(logical.argmax()),
                      'query_probability': {key: float(value @ mode_weights) for key, value in queries[index].items()}})
    return {'id': case['id'], 'log_evidence': math.log(total), 'mode_posterior': mode_weights.tolist(), 'shots': shots}


def random_case(random, index):
    detector_count = int(random.integers(1, 10))
    fault_count = int(random.integers(1, 16))
    region_count = int(random.integers(1, min(detector_count, 4) + 1))
    modes = int(random.integers(1, 4))
    observable_count = int(random.integers(0, 5))
    regions = (np.arange(detector_count) % region_count).tolist()
    random.shuffle(regions)
    prior = random.dirichlet(np.ones(modes))
    if modes > 1 and index % 7 == 0:
        prior[0] = 0
        prior /= prior.sum()
    faults = []
    for fault_index in range(fault_count):
        support_size = int(random.integers(0, min(detector_count, 4) + 1))
        detectors = random.choice(detector_count, support_size, replace=False).tolist()
        rates = random.uniform(0.005, 0.995, modes)
        if index % 3 == 0:
            rates[random.random(modes) < 0.3] = 0
            rates[random.random(modes) < 0.3] = 1
        if fault_index and index % 4 == 0:
            detectors = faults[0]['detectors'][:]
        faults.append({'detectors': detectors, 'logical_mask': int(random.integers(1 << observable_count)),
                       'probabilities': rates.tolist()})
    mode = int(random.choice(modes, p=prior))
    shots = []
    for shot_index in range(int(random.integers(1, 5))):
        record = [0] * detector_count
        for fault in faults:
            if random.random() < fault['probabilities'][mode]:
                for detector in fault['detectors']:
                    record[detector] ^= 1
        erased = random.random(detector_count) < (1.0 if index % 13 == 0 else 0.3)
        record = [None if erased[detector] else value for detector, value in enumerate(record)]
        queries = [{'id': 'query_' + str(query),
                    'faults': random.choice(fault_count, int(random.integers(0, fault_count + 1)), replace=False).tolist()}
                   for query in range(7)]
        shots.append({'id': 'shot_' + str(shot_index), 'syndrome': record, 'queries': queries})
    return {'id': 'random_' + str(index), 'num_detectors': detector_count, 'num_observables': observable_count,
            'detector_regions': regions, 'faults': faults, 'mode_prior': prior.tolist(), 'shots': shots}


def permute_case(case, random):
    permuted = copy.deepcopy(case)
    detector_order = random.permutation(case['num_detectors'])
    fault_order = random.permutation(len(case['faults']))
    inverse_detectors = np.argsort(detector_order)
    inverse_faults = np.argsort(fault_order)
    labels = list(set(case['detector_regions']))
    relabel = dict(zip(labels, random.choice(10000, len(labels), replace=False).tolist()))
    permuted['detector_regions'] = [relabel[case['detector_regions'][index]] for index in detector_order]
    permuted['faults'] = [copy.deepcopy(case['faults'][index]) for index in fault_order]
    for fault in permuted['faults']:
        fault['detectors'] = [int(inverse_detectors[index]) for index in fault['detectors']]
    for shot in permuted['shots']:
        shot['syndrome'] = [shot['syndrome'][index] for index in detector_order]
        for query in shot['queries']:
            query['faults'] = [int(inverse_faults[index]) for index in query['faults']]
    return permuted


def local_method_checks(random):
    maximum = 0.0
    for trial in range(20):
        fault_count = 14
        detector_count = 6
        faults = [{'detectors': np.flatnonzero(random.random(detector_count) < 0.45).tolist(),
                   'logical_mask': 0, 'probabilities': [float(random.random())]} for _ in range(fault_count)]
        signs = random.choice([-1.0, 1.0], (12, fault_count))
        signs[0] = 1
        model = LocalModel(faults, list(range(fault_count)), [], [], tuple(range(detector_count)), signs)
        rates = np.array([fault['probabilities'][0] for fault in faults])
        if trial % 2 == 0:
            rates[:3] = [0, 1, 0]
        offsets = np.array([sum(((target >> position) & 1) << pivot
                                for position, pivot in enumerate(model.pivots))
                            for target in range(1 << model.rank)], dtype=np.uint64)
        primal, primal_scale = model.enumerate(offsets, rates)
        dual, dual_scale = model.dynamic(rates)
        error = np.max(np.abs(primal * math.exp(primal_scale) - dual * math.exp(dual_scale)))
        maximum = max(maximum, float(error))
    return maximum


def edge_checks():
    cases = [
        {'id': 'empty_network', 'num_detectors': 0, 'num_observables': 3,
         'detector_regions': [], 'faults': [], 'mode_prior': [0.6, 0.4],
         'shots': [{'id': 'empty_shot', 'syndrome': [], 'queries': [{'id': 'empty_query', 'faults': []}]}]},
        {'id': 'no_faults', 'num_detectors': 3, 'num_observables': 0,
         'detector_regions': [100, 201, 900], 'faults': [], 'mode_prior': [0, 1],
         'shots': [{'id': 'empty_shot', 'syndrome': [0, None, 0], 'queries': [{'id': 'empty_query', 'faults': []}]}]},
        {'id': 'shared_support', 'num_detectors': 1, 'num_observables': 1,
         'detector_regions': [12], 'mode_prior': [0.2, 0.3, 0.5],
         'faults': [{'detectors': [0], 'logical_mask': 1, 'probabilities': [0, 1, 0.3]}],
         'shots': [{'id': str(index), 'syndrome': [value], 'queries': [{'id': 'fault', 'faults': [0]}]}
                   for index, value in enumerate([0, 1, None])]},
        {'id': 'silent_network', 'num_detectors': 0, 'num_observables': 3,
         'detector_regions': [], 'mode_prior': [0.2, 0.8],
         'faults': [{'detectors': [], 'logical_mask': mask, 'probabilities': rates}
                    for mask, rates in [(1, [0, 0.2]), (3, [1, 0.7]), (7, [0.5, 0.1])]],
         'shots': [{'id': 'silent_shot', 'syndrome': [], 'queries': [{'id': 'parity', 'faults': [0, 2]}]}]}
    ]
    errors = compare({'cases': [exhaustive(case) for case in cases]},
                     {'cases': [decode_case(case) for case in cases]})
    rate = 1e-30
    rare = {'id': 'underflow', 'num_detectors': 60, 'num_observables': 1,
            'detector_regions': [index // 20 for index in range(60)], 'mode_prior': [0.5, 0.5],
            'faults': [{'detectors': [index], 'logical_mask': 1, 'probabilities': [0, rate]}
                       for index in range(60)],
            'shots': [{'id': str(index), 'syndrome': [1] * 60,
                       'queries': [{'id': 'fault', 'faults': [0]}]} for index in range(4)]}
    actual = decode_case(rare)
    expected_log = math.log(0.5) + 240 * math.log(rate)
    assert abs(actual['log_evidence'] - expected_log) < 1e-9
    assert actual['mode_posterior'] == [0.0, 1.0]
    assert all(shot['logical_decision'] == 0 and shot['query_probability']['fault'] == 1
               for shot in actual['shots'])
    return {'exhaustive': errors, 'rare_log_evidence': actual['log_evidence'],
            'rare_log_evidence_abs_error': abs(actual['log_evidence'] - expected_log)}


def stress_case(seed, topology='dense', local_rank=22):
    random = np.random.default_rng(seed)
    region_count = 10
    detector_count = region_count * local_rank
    internal_count = 28
    edges = []
    if topology == 'dense':
        edges = [(left, right) for left in range(region_count) for right in range(left + 1, region_count)
                 if (left ^ 1) != right]
    elif topology == 'hyper':
        edges = [tuple(sorted({region, (region + 1) % region_count, (region + 3) % region_count}))
                 for region in range(region_count)]
        edges += edges.copy()
    else:
        edges = [(region, (region + 1) % region_count) for region in range(region_count) for _ in range(4)]
    faults = []
    for region in range(region_count):
        for column in range(internal_count):
            support = [column] if column < local_rank else random.choice(local_rank, min(local_rank, 4), replace=False).tolist()
            faults.append({'detectors': [region * local_rank + detector for detector in support],
                           'logical_mask': int(random.integers(16)),
                           'probabilities': random.uniform(0.01, 0.19, 3).tolist()})
    for edge in edges:
        faults.append({'detectors': [region * local_rank + int(random.integers(local_rank)) for region in edge],
                       'logical_mask': int(random.integers(16)),
                       'probabilities': random.uniform(0.01, 0.2, 3).tolist()})
    shots = []
    for shot_index in range(4):
        record = [0] * detector_count
        for fault in faults:
            if random.random() < fault['probabilities'][1]:
                for detector in fault['detectors']:
                    record[detector] ^= 1
        for detector in random.choice(detector_count, shot_index * 3, replace=False):
            record[detector] = None
        shots.append({'id': 'shot_' + str(shot_index), 'syndrome': record,
                      'queries': [{'id': 'query_' + str(query), 'faults': random.choice(len(faults), 3, replace=False).tolist()}
                                  for query in range(6)]})
    return {'id': 'stress_' + topology + '_' + str(local_rank), 'num_detectors': detector_count,
            'num_observables': 4, 'detector_regions': [region for region in range(region_count) for _ in range(local_rank)],
            'faults': faults, 'mode_prior': [0.4, 0.35, 0.25], 'shots': shots}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--random-cases', type=int, default=80)
    parser.add_argument('--public-input')
    parser.add_argument('--report', required=True)
    parser.add_argument('--stress-output')
    arguments = parser.parse_args()
    random = np.random.default_rng(812721)
    started = time.perf_counter()
    measurements = []
    for index in range(arguments.random_cases):
        case = random_case(random, index)
        expected = exhaustive(case)
        actual = decode_case(case)
        measurements.extend(compare({'cases': [expected]}, {'cases': [actual]}))
    report = {'random_cases': arguments.random_cases,
              'max_errors': {key: max((result[key] for result in measurements), default=0.0)
                             for key in ['logical_tv_max', 'query_abs_max', 'log_evidence_abs', 'mode_tv']},
              'local_primal_dynamic_max_abs': local_method_checks(random),
              'edge_cases': edge_checks()}
    if arguments.public_input:
        public = json.loads(Path(arguments.public_input).read_text())
        expected = {'cases': [decode_case(case) for case in public['cases']]}
        actual = {'cases': [decode_case(permute_case(case, random)) for case in public['cases']]}
        report['permutation_checks'] = compare(expected, actual)
    report['elapsed_seconds'] = time.perf_counter() - started
    if arguments.stress_output:
        Path(arguments.stress_output).write_text(json.dumps({'cases': [stress_case(129)]}))
    Path(arguments.report).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    assert max(report['max_errors'].values()) < 1e-9
    assert report['local_primal_dynamic_max_abs'] < 1e-10


if __name__ == '__main__':
    main()
