import json
import os
import random
import time

import numpy as np

from analyze import anf
from compact import Network, cheap_basis, unpack, usage
from relations import kernel


def add_basis(basis, value, expression=0):
    while value:
        pivot = value.bit_length() - 1
        if pivot not in basis:
            basis[pivot] = value, expression
            return True
        other, other_expression = basis[pivot]
        value ^= other
        expression ^= other_expression
    return False


def reduce_basis(basis, value):
    expression = 0
    while value:
        pivot = value.bit_length() - 1
        if pivot not in basis:
            break
        other, other_expression = basis[pivot]
        value ^= other
        expression ^= other_expression
    return value, expression


def remainder(basis, value):
    for pivot in sorted(basis, reverse=True):
        if value >> pivot & 1:
            value ^= basis[pivot][0]
    return value


def polynomial_truth(value, width):
    for bit in range(width):
        upper = sum(1 << address for address in range(1 << width) if address >> bit & 1)
        value ^= (value << (1 << bit)) & upper
    return value


def combine(values, expression):
    result = 0
    while expression:
        bit = (expression & -expression).bit_length() - 1
        result ^= values[bit]
        expression &= expression - 1
    return result


def optimize_basis(values, targets, pool, iterations=35):
    entries = sorted(pool.items(), key=lambda item: item[1][0])
    chosen, selected = {}, []
    for index, (projection, entry) in enumerate(entries):
        if add_basis(chosen, projection):
            selected.append(index)
    initial = len(values)
    dimension = initial + len(selected)
    coordinates = {}
    for index, value in enumerate(values):
        add_basis(coordinates, value, 1 << index)
    for index, candidate in enumerate(selected):
        add_basis(coordinates, entries[candidate][1][3], 1 << (initial + index))

    def matrix(functions):
        row_bytes = (dimension + 7) // 8
        encoded = b''.join(reduce_basis(coordinates, value)[1].to_bytes(row_bytes, 'little') for value in functions)
        return np.unpackbits(np.frombuffer(encoded, dtype=np.uint8).reshape(-1, row_bytes), axis=1, bitorder='little')[:, :dimension].copy()

    candidates = matrix([entry[1][3] for entry in entries])
    target_matrix = matrix(targets)
    costs = np.array([entry[1][0] for entry in entries], dtype=np.float32)
    original_cost = int(target_matrix.sum() + costs[selected].sum())
    for iteration in range(iterations):
        targets_float = target_matrix.astype(np.float32)
        weights = targets_float.sum(axis=0)
        overlap = targets_float.T @ targets_float
        changes = weights[initial:, None] - 2 * overlap[initial:, :]
        differences = candidates.astype(np.float32) @ changes.T
        differences += weights[initial:][None, :]
        differences += costs[:, None] - costs[selected][None, :]
        differences[candidates[:, initial:] == 0] = 1e9
        best = np.unravel_index(np.argmin(differences), differences.shape)
        if differences[best] >= -0.5:
            break
        candidate, replaced = map(int, best)
        pivot = initial + replaced
        row = candidates[candidate].copy()
        row[pivot] = 0
        candidates[candidates[:, pivot] == 1] ^= row
        target_matrix[target_matrix[:, pivot] == 1] ^= row
        selected[replaced] = candidate
    final_cost = int(target_matrix.sum() + costs[selected].sum())
    print('basis cost', original_cost, final_cost, 'exchanges', iteration, flush=True)
    return [entries[index][1] for index in selected]


def synthesize(instance, seed=17, initial_count=None):
    width, count = instance['n'], instance['m']
    right_width = 4 if width == 12 else 3
    left_width = width - right_width
    initial_count = initial_count or {10: 52, 11: 108, 12: 72}[width]
    generator = random.Random(seed)
    coefficients = anf(instance['table'], width)
    targets = []
    for right in range(1 << right_width):
        for bit in range(count):
            polynomial = sum(((int(coefficients[(left << right_width) | right]) >> bit) & 1) << left for left in range(1 << left_width))
            targets.append(polynomial_truth(polynomial, left_width))
    split = left_width // 2
    lower = (1 << split) - 1
    upper = ((1 << left_width) - 1) ^ lower
    monomials = [mask for mask in range(1 << left_width) if mask.bit_count() <= 2 or not mask & lower or not mask & upper]
    extra = [mask for mask in range(1 << left_width) if 3 <= mask.bit_count() <= 4 and mask not in monomials]
    generator.shuffle(extra)
    monomials += extra[:initial_count - len(monomials)]
    monomials.sort(key=lambda mask: (mask.bit_count(), mask))
    values = [sum(1 << address for address in range(1 << left_width) if address & mask == mask) for mask in monomials]
    initial_basis = {}
    for value in values:
        add_basis(initial_basis, value)
    combined_basis = initial_basis.copy()
    for value in targets:
        add_basis(combined_basis, value)
    target_rank = len(combined_basis) - len(initial_basis)
    pool, pool_basis = {}, {}
    full_rank_at = None
    started = time.time()
    for trial in range(400):
        amount = generator.choice([4, 6, 8, 12, 16, 24, 32])
        indices = generator.sample(range(left_width + 1, len(values)), min(amount - 1, len(values) - left_width - 1))
        indices.append(generator.randrange(1, left_width + 1))
        left = sum(1 << index for index in indices)
        left_value = combine(values, left)
        products = [left_value & value for value in values]
        dependencies = kernel([remainder(combined_basis, value) for value in products])
        dependency_values = [combine(products, expression) for expression in dependencies]
        projections = [remainder(initial_basis, value) for value in dependency_values]
        for first in range(len(dependencies)):
            for second in range(-1, first):
                right = dependencies[first] ^ (dependencies[second] if second >= 0 else 0)
                projection = projections[first] ^ (projections[second] if second >= 0 else 0)
                if not projection:
                    continue
                cost = left.bit_count() + right.bit_count()
                if projection not in pool or cost < pool[projection][0]:
                    product = dependency_values[first] ^ (dependency_values[second] if second >= 0 else 0)
                    pool[projection] = cost, left, right, product
                    add_basis(pool_basis, projection)
        if len(pool_basis) == target_rank and full_rank_at is None:
            full_rank_at = trial
        if full_rank_at is not None and trial >= full_rank_at + 15:
            break
    print(instance['id'], seed, 'pool', len(pool), 'rank', len(pool_basis), target_rank, 'trials', trial + 1, 'seconds', time.time() - started, flush=True)
    if len(pool_basis) != target_rank:
        return None
    selected_products = optimize_basis(values, targets, pool)
    network = Network(width)
    references = [network.monomial(mask << right_width) for mask in monomials]
    function_basis = {}
    for value, reference in zip(values, references):
        add_basis(function_basis, value, reference)
    for cost, left, right, product in selected_products:
        reference = network.product(combine(references, left), combine(references, right))
        add_basis(function_basis, product, reference)
    expressions = []
    for target in targets:
        residual, expression = reduce_basis(function_basis, target)
        if residual:
            raise RuntimeError('target outside synthesized span')
        expressions.append(expression)
    outputs = [0] * count
    for right in range(1 << right_width):
        selected, combinations = cheap_basis(expressions[right * count:(right + 1) * count])
        terms = [network.product(expression, network.monomial(right)) for expression in selected]
        for bit, combination in enumerate(combinations):
            outputs[bit] ^= combine(terms, combination)
    circuit = {'id': instance['id'], 'gates': network.gates, 'outputs': list(map(unpack, outputs))}
    print('usage', usage(circuit, width), flush=True)
    return circuit


if __name__ == '__main__':
    suite = json.load(open(os.environ['PART'] + '/input/suite.json'))
    circuits = []
    for instance in suite['instances']:
        circuit = synthesize(instance)
        if circuit is None:
            raise RuntimeError('subspace search incomplete')
        circuits.append(circuit)
    json.dump({'circuits': circuits}, open('subspace_circuits.json', 'w'))
