import itertools
import json
import os

from analyze import anf


class Network:
    def __init__(self, width):
        self.width = width
        self.gates = []
        self.cache = {}
        self.monomials = {0: 1, **{1 << bit: 1 << (bit + 1) for bit in range(width)}}

    def product(self, left, right):
        if not left or not right:
            return 0
        if left == 1:
            return right
        if right == 1 or left == right:
            return left
        key = tuple(sorted((left, right)))
        if key not in self.cache:
            self.cache[key] = 1 << (self.width + 1 + len(self.gates))
            self.gates.append({'left': unpack(left), 'right': unpack(right)})
        return self.cache[key]

    def monomial(self, mask):
        if mask not in self.monomials:
            bits = [1 << bit for bit in range(self.width) if mask >> bit & 1]
            left_mask = sum(bits[:len(bits) // 2])
            self.monomials[mask] = self.product(self.monomial(left_mask), self.monomial(mask ^ left_mask))
        return self.monomials[mask]


def unpack(mask):
    return [bit for bit in range(mask.bit_length()) if mask >> bit & 1]


def cheap_basis(polynomials):
    candidates = [(0, 0)]
    for bit, polynomial in enumerate(polynomials):
        candidates += [(value ^ polynomial, combination | (1 << bit)) for value, combination in candidates]
    candidates = sorted((value.bit_count(), value, combination) for value, combination in candidates if value)
    pivots = {}
    selected = []
    for weight, value, combination in candidates:
        reduced = value
        while reduced:
            pivot = reduced.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = reduced
                selected.append(value)
                break
            reduced ^= pivots[pivot]
    represented = {0: 0}
    for bit, value in enumerate(selected):
        represented.update({previous ^ value: combination ^ (1 << bit) for previous, combination in list(represented.items())})
    return selected, [represented[value] for value in polynomials]


def synthesize(instance, group_size=4, order=None):
    width, count = instance['n'], instance['m']
    order = order or list(range(width))
    right_bits, left_bits = order[:group_size], order[group_size:]
    left_masks = [sum(1 << bit for offset, bit in enumerate(left_bits) if mask >> offset & 1) for mask in range(1 << len(left_bits))]
    right_masks = [sum(1 << bit for offset, bit in enumerate(right_bits) if mask >> offset & 1) for mask in range(1 << len(right_bits))]
    coefficients = anf(instance['table'], width)
    network = Network(width)
    outputs = [0] * count
    for right_mask in right_masks:
        polynomials = [sum(1 << offset for offset, left_mask in enumerate(left_masks) if int(coefficients[left_mask | right_mask]) >> bit & 1) for bit in range(count)]
        selected, expressions = cheap_basis(polynomials)
        terms = []
        for polynomial in selected:
            operand = 0
            for offset in unpack(polynomial):
                operand ^= network.monomial(left_masks[offset])
            terms.append(network.product(operand, network.monomial(right_mask)))
        for bit, expression in enumerate(expressions):
            for term in unpack(expression):
                outputs[bit] ^= terms[term]
    return {'id': instance['id'], 'gates': network.gates, 'outputs': list(map(unpack, outputs))}


def usage(circuit, width):
    depth = [0] * (width + 1)
    affine = 0
    for gate in circuit['gates']:
        depth.append(1 + max((depth[reference] for operand in gate.values() for reference in operand), default=0))
        affine += sum(map(len, gate.values()))
    return len(circuit['gates']), max(depth), affine + sum(map(len, circuit['outputs']))


if __name__ == '__main__':
    suite = json.load(open(os.environ['PART'] + '/input/suite.json'))
    circuits = []
    for instance in suite['instances']:
        candidates = []
        for group_size in range(3, 7):
            circuit = synthesize(instance, group_size)
            resources = usage(circuit, instance['n'])
            candidates.append((resources, circuit))
            print(instance['id'], group_size, resources, flush=True)
        resources, circuit = min(candidates, key=lambda item: (item[0][1] > instance['caps']['depth'], item[0][0], item[0][2]))
        circuits.append(circuit)
    json.dump({'circuits': circuits}, open('compact_circuits.json', 'w'))
