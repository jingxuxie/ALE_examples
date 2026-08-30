import json
import os
from pathlib import Path
from analyze import SUITE, anf

class Circuit:
    def __init__(self, instance):
        self.instance = instance
        self.width = instance['n']
        self.gates = []
        self.cache = {}
        self.monomials = {0: 0, **{1 << bit: bit + 1 for bit in range(self.width)}}

    def product(self, left, right):
        left, right = tuple(sorted(left)), tuple(sorted(right))
        if not left or not right:
            return set()
        if left == (0,):
            return set(right)
        if right == (0,) or left == right:
            return set(left)
        key = tuple(sorted((left, right)))
        if key not in self.cache:
            reference = self.width + 1 + len(self.gates)
            self.gates.append({'left': list(key[0]), 'right': list(key[1])})
            self.cache[key] = reference
        return {self.cache[key]}

    def monomial(self, mask):
        if mask not in self.monomials:
            bits = [1 << bit for bit in range(self.width) if mask >> bit & 1]
            split = len(bits) // 2
            left = self.monomial(sum(bits[:split]))
            right = self.monomial(sum(bits[split:]))
            self.monomials[mask] = next(iter(self.product([left], [right])))
        return self.monomials[mask]

    def finish(self, outputs):
        used = set().union(*outputs)
        for index in reversed(range(len(self.gates))):
            if self.width + 1 + index in used:
                used.update(self.gates[index]['left'])
                used.update(self.gates[index]['right'])
        references = {reference: reference for reference in range(self.width + 1)}
        gates = []
        for index, gate in enumerate(self.gates):
            if self.width + 1 + index in used:
                references[self.width + 1 + index] = self.width + 1 + len(gates)
                gates.append({side: sorted(references[reference] for reference in gate[side]) for side in ('left', 'right')})
        return {'id': self.instance['id'], 'gates': gates, 'outputs': [sorted(references[reference] for reference in output) for output in outputs]}

def synthesize(instance, split):
    width = instance['n']
    circuit = Circuit(instance)
    coefficients = anf(instance['table'])
    outputs = [set() for _ in range(instance['m'])]
    for left_mask in range(1 << split):
        left_reference = circuit.monomial(left_mask)
        for output_bit in range(instance['m']):
            right_expression = set()
            for right_mask in range(1 << (width - split)):
                if int(coefficients[left_mask | (right_mask << split)]) >> output_bit & 1:
                    right_expression.add(circuit.monomial(right_mask << split))
            if right_expression:
                outputs[output_bit] ^= circuit.product([left_reference], right_expression)
    return circuit.finish(outputs)

def usage(circuit, width):
    depths = [0] * (width + 1)
    affine = sum(map(len, circuit['outputs']))
    for gate in circuit['gates']:
        depths.append(1 + max((depths[reference] for side in ('left', 'right') for reference in gate[side]), default=0))
        affine += len(gate['left']) + len(gate['right'])
    return {'and': len(circuit['gates']), 'depth': max(depths), 'affine': affine, 'ancilla': len(circuit['gates']) + 2 if circuit['gates'] else 0}

if __name__ == '__main__':
    circuits = []
    for instance in SUITE:
        candidates = [synthesize(instance, split) for split in range(max(2, instance['n'] - 8), min(8, instance['n'] - 2) + 1)]
        best = min(candidates, key=lambda circuit: (usage(circuit, instance['n'])['and'], usage(circuit, instance['n'])['affine']))
        print(instance['id'], usage(best, instance['n']), flush=True)
        circuits.append(best)
    Path('circuits.json').write_text(json.dumps({'circuits': circuits}, separators=(',', ':')))
