import json
import random
import sys
from pathlib import Path

import synthesis as syn
import ppr_optimize as ppr

LIBRARY = {}
for line in Path('threeq_library.txt').read_text().splitlines():
    key, encoded = line.split('|')
    gates = []
    for item in encoded.split(';'):
        if not item:
            continue
        fields = item.split(',')
        arguments = list(map(int, fields[1:]))
        if fields[0] == 'R':
            gates.extend(syn.ppr(*arguments))
        else:
            gates.append((fields[0], *arguments))
    LIBRARY[int(key)] = syn.simplify(gates)

def reduce_block(gates, qubits):
    positions = []
    replacements = {}
    removed = set()
    mapping = {qubit: index for index, qubit in enumerate(qubits)}
    def flush():
        if not positions:
            return
        count = sum(gates[index][0] == 'CX' for index in positions)
        if count < 2:
            positions.clear()
            return
        state = [1, 8, 2, 16, 4, 32]
        for index in positions:
            operation = gates[index]
            gate, first = operation[0], mapping[operation[1]]
            if gate == 'H':
                state[2 * first], state[2 * first + 1] = state[2 * first + 1], state[2 * first]
            elif gate == 'S':
                state[2 * first + 1] ^= state[2 * first]
            else:
                second = mapping[operation[2]]
                state[2 * second] ^= state[2 * first]
                state[2 * first + 1] ^= state[2 * second + 1]
        tail = []
        for qubit in range(3):
            original = state[2 * qubit:2 * qubit + 2]
            canonical = sorted([*original, original[0] ^ original[1]])[:2]
            for word in ('', 'H', 'S', 'HS', 'SH', 'HSH'):
                trial = original[:]
                for gate in word:
                    if gate == 'H':
                        trial.reverse()
                    else:
                        trial[1] ^= trial[0]
                if trial == canonical:
                    tail.extend((gate, qubit) for gate in word[::-1])
                    break
            state[2 * qubit:2 * qubit + 2] = canonical
        key = sum(column << (6 * index) for index, column in enumerate(state))
        word = syn.simplify(LIBRARY[key] + tail)
        newcount = sum(operation[0] == 'CX' for operation in word)
        if (newcount, len(word)) < (count, len(positions)):
            replacements[positions[0]] = [(operation[0], *(qubits[qubit] for qubit in operation[1:])) for operation in word]
            removed.update(positions)
        positions.clear()
    for index, operation in enumerate(gates):
        if not any(qubit in mapping for qubit in operation[1:]):
            continue
        if all(qubit in mapping for qubit in operation[1:]):
            positions.append(index)
        else:
            flush()
    flush()
    return [operation for index, original in enumerate(gates) for operation in (replacements.get(index, []) if index in removed else [original])]

def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('best_gates.json')
    iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    gates = [tuple(operation) for operation in json.loads(source.read_text())]
    triples = []
    for center, neighbors in enumerate(syn.NEIGHBORS):
        for first_index, first in enumerate(neighbors):
            for second in neighbors[first_index + 1:]:
                triples.append((first, center, second))
    rng = random.Random(8678)
    for iteration in range(iterations):
        rotations, frames = ppr.extract(gates)
        rotations = ppr.cancel(rotations)
        rotations = ppr.conjugate_reduce(rotations)
        rotations = ppr.reorder(rotations, iteration)
        gates = syn.simplify(ppr.native(rotations, frames))
        rng.shuffle(triples)
        for qubits in triples:
            gates = reduce_block(gates, qubits)
        syn.save(gates[:], f'peephole3:{source}:{iteration}')
        Path('peephole3_latest.json').write_text(json.dumps(gates) + '\n')

if __name__ == '__main__':
    main()
