import json
import random
import time
from pathlib import Path
from analyze import SUITE, anf
from relations import columns, truth_bits
from multipliers import mobius_bits
from compact import Circuit, usage

class Basis:
    def __init__(self):
        self.pivots = {}

    def reduce(self, value):
        while value:
            pivot = value.bit_length() - 1
            if pivot not in self.pivots:
                return value
            value ^= self.pivots[pivot][0]
        return 0

    def residue(self, value):
        for pivot, (vector, _) in sorted(self.pivots.items(), reverse=True):
            if (value >> pivot) & 1:
                value ^= vector
        return value

    def expression(self, value):
        result = 0
        while value:
            pivot = value.bit_length() - 1
            vector, expression = self.pivots[pivot]
            value ^= vector
            result ^= expression
        return result

    def add(self, value, expression=0):
        while value:
            pivot = value.bit_length() - 1
            if pivot not in self.pivots:
                self.pivots[pivot] = value, expression
                return True
            vector, previous = self.pivots[pivot]
            value ^= vector
            expression ^= previous
        return False

def bit_indices(expression):
    while expression:
        low = expression & -expression
        yield low.bit_length() - 1
        expression ^= low

def synthesize_space(width, targets, seed, seconds=60):
    randomizer = random.Random(seed)
    cols = columns(width)
    values = [cols[0]] + [cols[1 << bit] for bit in range(width)]
    depths = [0] * len(values)
    monomials = [0] + [1 << bit for bit in range(width)]
    available = Basis()
    depth_bases = [Basis() for _ in range(4)]
    target_space = Basis()
    for reference, value in enumerate(values):
        available.add(value, 1 << reference)
        for basis in depth_bases:
            basis.add(value)
        target_space.add(value)
    for value in targets:
        target_space.add(value)
    gates = []
    extra = 0
    residue_cache = {}
    started = time.monotonic()
    def add_gate(value, left, right, depth, monomial=None):
        reference = len(values)
        values.append(value)
        depths.append(depth)
        monomials.append(monomial)
        independent = available.add(value, 1 << reference)
        for level in range(depth, 4):
            depth_bases[level].add(value)
        if not independent:
            available.pivots.clear()
            for previous in sorted(range(len(values)), key=lambda index: (depths[index], index)):
                available.add(values[previous], 1 << previous)
        gates.append((left, right))
    while any(available.reduce(target) for target in targets):
        if time.monotonic() - started > seconds:
            return None
        lower = [reference for reference, depth in enumerate(depths) if depth <= 2]
        left_choices = [(values[reference], 1 << reference, depths[reference]) for reference in lower if reference]
        for _ in range(8):
            first, second = randomizer.sample(lower, 2)
            left_choices.append((values[first] ^ values[second], (1 << first) ^ (1 << second), max(depths[first], depths[second])))
        randomizer.shuffle(left_choices)
        candidates = []
        ordered_pivots = sorted(target_space.pivots.items(), reverse=True)
        for left_value, left_expression, left_depth in left_choices:
            pivots = {}
            for reference in lower:
                product = left_value & values[reference]
                if product not in residue_cache:
                    remainder = product
                    for pivot, (vector, _) in ordered_pivots:
                        if (remainder >> pivot) & 1:
                            remainder ^= vector
                    residue_cache[product] = remainder
                remainder = residue_cache[product]
                expression = 1 << reference
                actual = product
                while remainder:
                    pivot = remainder.bit_length() - 1
                    if pivot not in pivots:
                        pivots[pivot] = remainder, expression, actual
                        break
                    prior, previous_expression, previous_actual = pivots[pivot]
                    remainder ^= prior
                    expression ^= previous_expression
                    actual ^= previous_actual
                if not remainder and actual and available.reduce(actual):
                    depth = 1 + max(left_depth, max(depths[reference] for reference in bit_indices(expression)))
                    candidates.append((left_expression.bit_count() + expression.bit_count(), depth, randomizer.random(), actual, left_expression, expression))
        if candidates:
            candidates.sort(key=lambda candidate: (candidate[1], candidate[0], candidate[2]))
            added = 0
            for cost, depth, _, value, left, right in candidates:
                if available.reduce(value):
                    add_gate(value, left, right, depth)
                    added += 1
            if added:
                continue
        auxiliary = []
        shallow = [reference for reference, depth in enumerate(depths) if depth <= 1]
        for first_index, first in enumerate(shallow):
            for second in shallow[first_index + 1:]:
                value = values[first] & values[second]
                product_depth = 1 + max(depths[first], depths[second])
                if not depth_bases[product_depth].reduce(value):
                    continue
                mask = None if monomials[first] is None or monomials[second] is None else monomials[first] | monomials[second]
                degree = mask.bit_count() if mask is not None else 2 + depths[first] + depths[second]
                preference = (4 - degree) if randomizer.random() < 0.65 else degree
                auxiliary.append((preference, randomizer.random(), value, first, second, mask))
        if not auxiliary:
            return None
        _, _, value, first, second, mask = min(auxiliary)
        if target_space.add(value):
            extra += 1
            residue_cache.clear()
        add_gate(value, 1 << first, 1 << second, 1 + max(depths[first], depths[second]), mask)
    expressions = [available.expression(target) for target in targets]
    print('space', width, 'seed', seed, 'gates', len(gates), 'extra', extra, 'seconds', round(time.monotonic() - started, 2), flush=True)
    return gates, expressions

def synthesize(instance, split, seed, seconds):
    width = instance['n']
    right_width = width - split
    coefficients = anf(instance['table'])
    cols = columns(right_width)
    targets = []
    for left_mask in range(1 << split):
        for bit in range(instance['m']):
            coefficient = sum(((int(coefficients[left_mask | (right_mask << split)]) >> bit) & 1) << right_mask for right_mask in range(1 << right_width))
            targets.append(mobius_bits(coefficient, cols, right_width))
    result = synthesize_space(right_width, targets, seed, seconds)
    if result is None:
        return None
    gates, expressions = result
    circuit = Circuit(instance)
    left_references = [circuit.monomial(mask) for mask in range(1 << split)]
    references = {0: 0, **{bit + 1: split + bit + 1 for bit in range(right_width)}}
    for index, (left, right) in enumerate(gates):
        product = circuit.product([references[reference] for reference in bit_indices(left)], [references[reference] for reference in bit_indices(right)])
        references[right_width + 1 + index] = next(iter(product))
    outputs = [set() for _ in range(instance['m'])]
    for index, expression in enumerate(expressions):
        left_mask, bit = divmod(index, instance['m'])
        right = {references[reference] for reference in bit_indices(expression)}
        outputs[bit] ^= circuit.product([left_references[left_mask]], right)
    return circuit.finish(outputs)

if __name__ == '__main__':
    data = json.loads(Path('circuits.json').read_text())
    for instance_index in [1, 2, 4, 5]:
        instance = SUITE[instance_index]
        for seed in range(3):
            candidate = synthesize(instance, 4, seed, 60)
            if candidate:
                resources = usage(candidate, instance['n'])
                print(instance['id'], resources, flush=True)
                if resources['and'] < usage(data['circuits'][instance_index], instance['n'])['and']:
                    data['circuits'][instance_index] = candidate
                    Path('circuits.json').write_text(json.dumps(data, separators=(',', ':')))
