import argparse
import json
import math
from pathlib import Path

import numpy as np


def parity_array(values):
    values = np.asarray(values, dtype=np.uint64).copy()
    values ^= values >> np.uint64(32)
    values ^= values >> np.uint64(16)
    values ^= values >> np.uint64(8)
    values ^= values >> np.uint64(4)
    values ^= values >> np.uint64(2)
    values ^= values >> np.uint64(1)
    return (values & np.uint64(1)).astype(np.int8)


def binary_space(columns):
    basis = {}
    kernel = [0]
    for index, column in enumerate(columns):
        vector = column
        combination = 1 << index
        while vector:
            pivot = vector.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = (vector, combination)
                break
            old_vector, old_combination = basis[pivot]
            vector ^= old_vector
            combination ^= old_combination
        if not vector:
            kernel += [entry ^ combination for entry in kernel]
    return basis, np.asarray(kernel, dtype=np.uint64)


def particular(basis, target):
    combination = 0
    while target:
        pivot = target.bit_length() - 1
        if pivot not in basis:
            return None
        vector, representation = basis[pivot]
        target ^= vector
        combination ^= representation
    return combination


def eliminate(factors):
    factors = [(tuple(scope), values) for scope, values in factors]
    remaining = set().union(*(set(scope) for scope, _ in factors))
    while remaining:
        def cost(variable):
            adjacent = [scope for scope, _ in factors if variable in scope]
            union = set().union(*(set(scope) for scope in adjacent))
            return len(union), sum(len(scope) for scope in adjacent), variable

        variable = min(remaining, key=cost)
        selected = [(scope, values) for scope, values in factors if variable in scope]
        factors = [(scope, values) for scope, values in factors if variable not in scope]
        union = sorted(set().union(*(set(scope) for scope, _ in selected)))
        product = None
        for scope, values in selected:
            shape = [values.shape[0]] + [2 if item in scope else 1 for item in union]
            reshaped = values.reshape(shape)
            product = reshaped if product is None else product * reshaped
        reduced = product.sum(axis=1 + union.index(variable))
        factors.append((tuple(item for item in union if item != variable), reduced))
        remaining.remove(variable)
    product = factors[0][1].copy()
    for _, values in factors[1:]:
        product *= values
    return product


def prepare_shot(case, shot):
    faults = case['faults']
    regions = case['detector_regions']
    region_ids = sorted(set(regions))
    memberships = [set(regions[detector] for detector in fault['detectors']) for fault in faults]
    boundary = [index for index, membership in enumerate(memberships) if len(membership) != 1]
    boundary_ids = {fault: index for index, fault in enumerate(boundary)}
    queries = [set(query['faults']) for query in shot['queries']]
    logical_size = 1 << case['num_observables']
    characters = [('logical', mask) for mask in range(logical_size)]
    characters += [('query', index) for index in range(len(queries))]

    def fault_sign(fault_index, character):
        category, index = character
        if category == 'logical':
            return (faults[fault_index]['logical_mask'] & index).bit_count() % 2
        return int(fault_index in queries[index])

    local_regions = []
    for region in region_ids:
        rows = [index for index, owner in enumerate(regions)
                if owner == region and shot['syndrome'][index] is not None]
        row_ids = {row: index for index, row in enumerate(rows)}
        internal = [index for index, membership in enumerate(memberships) if membership == {region}]
        crossing = [index for index in boundary if region in memberships[index]]
        crossing.sort(key=boundary_ids.get)

        def column_mask(fault_index):
            return sum(1 << row_ids[row] for row in faults[fault_index]['detectors'] if row in row_ids)

        columns = [column_mask(index) for index in internal]
        basis, kernel = binary_space(columns)
        target = sum(int(shot['syndrome'][row]) << row_ids[row] for row in rows)
        residuals = [target]
        for fault_index in crossing:
            column = column_mask(fault_index)
            residuals += [entry ^ column for entry in residuals]
        solutions = [particular(basis, residual) for residual in residuals]
        feasible = np.asarray([solution is not None for solution in solutions])
        offsets = np.asarray([0 if solution is None else solution for solution in solutions], dtype=np.uint64)
        states = offsets[:, None] ^ kernel[None, :]
        masks = [sum(fault_sign(fault_index, character) << index
                     for index, fault_index in enumerate(internal)) for character in characters]
        local_regions.append((internal, tuple(boundary_ids[index] for index in crossing),
                              states, feasible, masks))
    boundary_signs = [[fault_sign(fault_index, character) for character in characters]
                      for fault_index in boundary]
    return local_regions, boundary, boundary_signs, logical_size, len(characters)


def mode_shot(case, prepared, mode):
    local_regions, boundary, boundary_signs, logical_size, character_count = prepared
    factors = []
    log_scale = 0.0
    for internal, scope, states, feasible, masks in local_regions:
        weights = np.ones(states.shape, dtype=float)
        for index, fault_index in enumerate(internal):
            probability = case['faults'][fault_index]['probabilities'][mode]
            bits = (states >> np.uint64(index)) & np.uint64(1)
            weights *= np.where(bits, probability, 1.0 - probability)
        weights *= feasible[:, None]
        table = np.empty((character_count, states.shape[0]))
        for channel, mask in enumerate(masks):
            signs = 1 - 2 * parity_array(states & np.uint64(mask))
            table[channel] = (weights * signs).sum(axis=1)
        scale = float(table[0].max())
        if scale == 0:
            return -math.inf, np.zeros(logical_size), np.zeros(character_count - logical_size)
        table /= scale
        log_scale += math.log(scale)
        shaped = np.stack([row.reshape((2,) * len(scope), order='F') for row in table])
        factors.append((scope, shaped))
    for variable, fault_index in enumerate(boundary):
        probability = case['faults'][fault_index]['probabilities'][mode]
        signs = 1 - 2 * np.asarray(boundary_signs[variable])
        table = np.stack([np.full(character_count, 1.0 - probability), probability * signs], axis=1)
        factors.append(((variable,), table))
    contracted = eliminate(factors)
    evidence = float(contracted[0])
    if evidence <= 0:
        return -math.inf, np.zeros(logical_size), np.zeros(character_count - logical_size)
    characteristic = contracted / evidence
    walsh = np.asarray([[1 - 2 * ((frequency & label).bit_count() % 2)
                         for label in range(logical_size)] for frequency in range(logical_size)])
    logical = np.clip(characteristic[:logical_size] @ walsh / logical_size, 0.0, 1.0)
    logical /= logical.sum()
    query = np.clip((1.0 - characteristic[logical_size:]) / 2.0, 0.0, 1.0)
    return math.log(evidence) + log_scale, logical, query


def solve_case(case):
    prepared = [prepare_shot(case, shot) for shot in case['shots']]
    modes = len(case['mode_prior'])
    results = [[mode_shot(case, entry, mode) for entry in prepared] for mode in range(modes)]
    log_weights = np.asarray([math.log(case['mode_prior'][mode]) + sum(result[0] for result in results[mode])
                              if case['mode_prior'][mode] > 0 else -math.inf for mode in range(modes)])
    offset = float(log_weights.max())
    if not math.isfinite(offset):
        raise ValueError('The complete batch has zero probability')
    weights = np.exp(log_weights - offset)
    log_evidence = offset + math.log(float(weights.sum()))
    weights /= weights.sum()
    output_shots = []
    for shot_index, shot in enumerate(case['shots']):
        logical = sum(weights[mode] * results[mode][shot_index][1] for mode in range(modes))
        queries = sum(weights[mode] * results[mode][shot_index][2] for mode in range(modes))
        output_shots.append({'id': shot['id'], 'logical_posterior': logical.tolist(),
                             'logical_decision': int(np.argmax(logical)),
                             'query_probability': {query['id']: float(queries[index])
                                                   for index, query in enumerate(shot['queries'])}})
    return {'id': case['id'], 'log_evidence': log_evidence,
            'mode_posterior': weights.tolist(), 'shots': output_shots}


def solve_dataset(dataset):
    return {'cases': [solve_case(case) for case in dataset['cases']]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    dataset = json.loads(Path(arguments.input).read_text())
    output = solve_dataset(dataset)
    Path(arguments.output).write_text(json.dumps(output, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
