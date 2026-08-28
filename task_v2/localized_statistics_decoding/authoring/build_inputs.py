import importlib.util
import itertools
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def generate_case(seed, name, region_count, rank, excess, edges, mode_count=2,
                  shot_count=3, shifted=False, tiny=False):
    random = np.random.default_rng(seed)
    num_observables = 3
    region_rows = rank + (0 if tiny else 2)
    detector_regions = [region for region in range(region_count) for _ in range(region_rows)]
    faults = []
    internals = []
    crossing = []

    def probabilities(kind, region=0):
        base = random.uniform(0.035, 0.16) if tiny else random.uniform(0.025, 0.12)
        result = []
        for mode in range(mode_count):
            multiplier = (0.8, 1.5, 2.0)[(region + mode) % 3]
            value = min(0.43, base * multiplier)
            if shifted and mode == 2 and random.random() < 0.13:
                value = 1.0 - value
            result.append(round(value, 7))
        return result

    for region in range(region_count):
        matrix = np.eye(rank, dtype=np.uint8)
        for _ in range(rank * 2):
            target, source = random.choice(rank, 2, replace=False)
            matrix[target] ^= matrix[source]
        extra = np.zeros((rank, excess), dtype=np.uint8)
        for column in range(excess):
            if column < 2:
                extra[:, column] = matrix[:, column]
            else:
                selected = random.choice(rank, min(rank, int(random.integers(2, 5))), replace=False)
                extra[selected, column] = 1
        matrix = np.column_stack([matrix, extra])
        if not tiny:
            matrix = np.vstack([matrix, matrix[0] ^ matrix[1], matrix[2] ^ matrix[3]])
        indices = []
        for column in range(matrix.shape[1]):
            support = (np.flatnonzero(matrix[:, column]) + region * region_rows).tolist()
            logical = 0
            if region == 0 and column in (0, rank, rank + 1):
                logical = (1, 3, 2)[(0, rank, rank + 1).index(column)]
            if region == 1 and column in (1, rank):
                logical = 5
            indices.append(len(faults))
            faults.append({'detectors': support, 'logical_mask': logical,
                           'probabilities': probabilities('internal', region)})
        internals.append(indices)

    for edge_index, (left, right) in enumerate(edges):
        for parallel in range(1 if tiny else 2):
            support = []
            for region in (left, right):
                base_rows = random.choice(rank, min(rank, 2 + parallel), replace=False)
                bits = np.zeros(rank, dtype=np.uint8)
                bits[base_rows] = 1
                full = list(bits) if tiny else list(bits) + [bits[0] ^ bits[1], bits[2] ^ bits[3]]
                support += [region * region_rows + index for index, bit in enumerate(full) if bit]
            crossing.append(len(faults))
            faults.append({'detectors': support, 'logical_mask': 6 if edge_index == 0 else 0,
                           'probabilities': probabilities('crossing', edge_index)})
    silent = len(faults)
    faults.append({'detectors': [], 'logical_mask': 3, 'probabilities': [0.055, 0.18, 0.27][:mode_count]})
    if shifted:
        faults[internals[-1][0]]['probabilities'][0] = 0.0
        faults[internals[-2][1]]['probabilities'][-1] = 1.0
        faults[crossing[-1]]['probabilities'][0] = 0.0
        faults.append({'detectors': [], 'logical_mask': 4, 'probabilities': [0.0, 0.09, 0.0][:mode_count]})
    mode_prior = [0.55, 0.45] if mode_count == 2 else [0.42, 0.33, 0.25]
    if tiny:
        mode_prior = [0.6, 0.4]
    true_mode = int(random.choice(mode_count, p=mode_prior))
    if shifted:
        true_mode = mode_count - 1
    shots = []
    for shot_index in range(shot_count):
        syndrome = [0] * len(detector_regions)
        for fault in faults:
            if random.random() < fault['probabilities'][true_mode]:
                for detector in fault['detectors']:
                    syndrome[detector] ^= 1
        if shot_index > 0:
            for region in range(region_count):
                if random.random() < (0.6 if shifted else 0.35):
                    detector = region * region_rows + int(random.integers(rank))
                    syndrome[detector] = None
        queries = [
            {'id': 'local', 'faults': [internals[0][0]]},
            {'id': 'alternate', 'faults': [internals[1][rank]]},
            {'id': 'boundary', 'faults': [crossing[shot_index % len(crossing)]]},
            {'id': 'cross_region', 'faults': [internals[0][0], internals[-1][rank]]},
            {'id': 'silent', 'faults': [silent]},
            {'id': 'mixed', 'faults': [crossing[0], internals[1][rank], silent]},
        ]
        shots.append({'id': f'shot_{shot_index}', 'syndrome': syndrome, 'queries': queries})

    detector_permutation = random.permutation(len(detector_regions)).tolist()
    detector_inverse = {old: new for new, old in enumerate(detector_permutation)}
    fault_permutation = random.permutation(len(faults)).tolist()
    fault_inverse = {old: new for new, old in enumerate(fault_permutation)}
    permuted_faults = []
    for old in fault_permutation:
        fault = dict(faults[old])
        fault['detectors'] = sorted(detector_inverse[index] for index in fault['detectors'])
        permuted_faults.append(fault)
    for shot in shots:
        shot['syndrome'] = [shot['syndrome'][index] for index in detector_permutation]
        for query in shot['queries']:
            query['faults'] = sorted(fault_inverse[index] for index in query['faults'])
    return {'id': name, 'num_detectors': len(detector_regions), 'num_observables': num_observables,
            'detector_regions': [detector_regions[index] for index in detector_permutation],
            'faults': permuted_faults, 'mode_prior': mode_prior, 'shots': shots}


def brute_case(case):
    count = len(case['faults'])
    states = np.asarray(list(itertools.product((0, 1), repeat=count)), dtype=np.uint8)
    detectors = np.zeros((states.shape[0], case['num_detectors']), dtype=np.uint8)
    logical = np.zeros(states.shape[0], dtype=np.int64)
    for index, fault in enumerate(case['faults']):
        detectors[:, fault['detectors']] ^= states[:, index, None]
        logical ^= states[:, index].astype(np.int64) * fault['logical_mask']
    mode_results = []
    for mode in range(len(case['mode_prior'])):
        probabilities = np.asarray([fault['probabilities'][mode] for fault in case['faults']])
        weights = np.where(states, probabilities, 1.0 - probabilities).prod(axis=1)
        results = []
        for shot in case['shots']:
            observed = [index for index, value in enumerate(shot['syndrome']) if value is not None]
            syndrome = np.asarray([shot['syndrome'][index] for index in observed])
            selected = weights * (detectors[:, observed] == syndrome).all(axis=1)
            evidence = float(selected.sum())
            if evidence:
                posterior = np.bincount(logical, weights=selected, minlength=1 << case['num_observables']) / evidence
                queries = [float(selected @ (states[:, query['faults']].sum(axis=1) % 2) / evidence)
                           for query in shot['queries']]
            else:
                posterior = np.zeros(1 << case['num_observables'])
                queries = [0.0] * len(shot['queries'])
            results.append((evidence, posterior, np.asarray(queries)))
        mode_results.append(results)
    weights = np.asarray([case['mode_prior'][mode] * math.prod(result[0] for result in results)
                          for mode, results in enumerate(mode_results)])
    log_evidence = math.log(float(weights.sum()))
    weights /= weights.sum()
    shots = []
    for shot_index, shot in enumerate(case['shots']):
        logical_posterior = sum(weights[mode] * mode_results[mode][shot_index][1] for mode in range(len(weights)))
        query_probability = sum(weights[mode] * mode_results[mode][shot_index][2] for mode in range(len(weights)))
        shots.append({'id': shot['id'], 'logical_posterior': logical_posterior.tolist(),
                      'logical_decision': int(np.argmax(logical_posterior)),
                      'query_probability': {query['id']: float(query_probability[index])
                                            for index, query in enumerate(shot['queries'])}})
    return {'id': case['id'], 'log_evidence': log_evidence, 'mode_posterior': weights.tolist(), 'shots': shots}


def main():
    tiny = [generate_case(91 + index, f'micro_{index}', 3, 2, 1,
                          [(0, 1), (1, 2), (2, 0)], shot_count=2, shifted=index == 2, tiny=True)
            for index in range(3)]
    public = [
        generate_case(308, 'regional_ring', 4, 12, 6, [(0, 1), (1, 2), (2, 3), (3, 0)]),
        generate_case(612, 'masked_ladder', 6, 16, 7,
                      [(0, 1), (1, 2), (3, 4), (4, 5), (0, 3), (1, 4), (2, 5)], mode_count=3),
    ]
    hidden = [
        generate_case(202608271, 'h_ring', 7, 16, 7,
                      [(index, (index + 1) % 7) for index in range(7)] + [(1, 4)]),
        generate_case(202608272, 'h_junction', 9, 17, 7,
                      [(row * 3 + column, row * 3 + column + 1) for row in range(3) for column in range(2)]
                      + [(row * 3 + column, (row + 1) * 3 + column) for row in range(2) for column in range(3)],
                      mode_count=3),
        generate_case(202608273, 'h_support', 8, 19, 8,
                      [(row * 4 + column, row * 4 + column + 1) for row in range(2) for column in range(3)]
                      + [(column, 4 + column) for column in range(4)],
                      mode_count=3, shot_count=4, shifted=True),
    ]
    public_dir = ROOT / 'participant/v_01/input'
    save(public_dir / 'micro.json', {'cases': tiny})
    save(public_dir / 'micro_expected.json', {'cases': [brute_case(case) for case in tiny]})
    save(public_dir / 'validation.json', {'cases': public})
    for index, case in enumerate(hidden, 1):
        save(ROOT / f'evaluator/v_01/hidden/case_{index:02d}.json', {'cases': [case]})
    save(ROOT / 'authoring/reference_input.json', {'cases': tiny + public + hidden})
    print(json.dumps({'micro_faults': [len(case['faults']) for case in tiny],
                      'public_faults': [len(case['faults']) for case in public],
                      'hidden_faults': [len(case['faults']) for case in hidden]}))


if __name__ == '__main__':
    main()
