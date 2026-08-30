import json
import random
import sys
from pathlib import Path

import networkx as nx
import synthesis as syn
import optimize as opt

EDGES = {tuple(sorted(edge)) for edge in syn.CONSTRAINTS['edges']}

def local_update(state, gate):
    return tuple((((axis & 1) << 1) | (axis >> 1)) if gate == 'H' else axis ^ ((axis & 1) << 1) for axis in state)

def extract(gates):
    frames = [(1, 2)] * 36
    rotations = []
    for operation in gates:
        if operation[0] != 'CX':
            gate, qubit = operation
            frames[qubit] = local_update(frames[qubit], gate)
            continue
        first, second = operation[1:]
        axes = []
        for qubit, requested in ((first, 2), (second, 1)):
            images = {frames[qubit][0]: 1, frames[qubit][1]: 2, frames[qubit][0] ^ frames[qubit][1]: 3}
            axes.append(images[requested])
        xmask = sum(1 << qubit for qubit, axis in zip((first, second), axes) if axis & 1)
        zmask = sum(1 << qubit for qubit, axis in zip((first, second), axes) if axis & 2)
        rotations.append((xmask, zmask))
        frames[first] = local_update(frames[first], 'S')
        for gate in 'HSH':
            frames[second] = local_update(frames[second], gate)
    return rotations, frames

def native(rotations, frames):
    gates = []
    for xmask, zmask in rotations:
        support = [qubit for qubit in range(36) if (xmask | zmask) >> qubit & 1]
        axes = [(xmask >> qubit & 1) + 2 * (zmask >> qubit & 1) for qubit in support]
        if len(support) == 1:
            word = {1: 'HSH', 2: 'S', 3: 'H'}[axes[0]]
            gates.extend((gate, support[0]) for gate in word)
        else:
            assert len(support) == 2 and tuple(support) in EDGES
            gates.extend(syn.ppr(*support, *axes))
    for qubit, state in enumerate(frames):
        gates.extend((gate, qubit) for gate in syn.WORDS[state])
    return gates

def anticommute(first, second):
    return ((first[0] & second[1]).bit_count() + (first[1] & second[0]).bit_count()) & 1

def cancel(rotations):
    changed = True
    while changed:
        changed = False
        for first in range(len(rotations)):
            propagated = rotations[first]
            for second in range(first + 1, len(rotations)):
                other = rotations[second]
                if propagated == other:
                    rotations = rotations[:first] + rotations[first + 1:second] + rotations[second + 1:]
                    changed = True
                    break
                if anticommute(propagated, other):
                    propagated = (propagated[0] ^ other[0], propagated[1] ^ other[1])
            if changed:
                break
    return rotations

def conjugate_reduce(rotations):
    changed = True
    while changed:
        changed = False
        for first in range(len(rotations)):
            conjugator = rotations[first]
            middle = []
            saving = 2 * int((conjugator[0] | conjugator[1]).bit_count() == 2)
            for second in range(first + 1, len(rotations)):
                other = rotations[second]
                if other == conjugator and saving > 0:
                    rotations = rotations[:first] + middle + rotations[second + 1:]
                    changed = True
                    break
                updated = other
                if anticommute(conjugator, other):
                    updated = (other[0] ^ conjugator[0], other[1] ^ conjugator[1])
                    support = updated[0] | updated[1]
                    if support.bit_count() > 2:
                        break
                    if support.bit_count() == 2:
                        qubits = tuple(qubit for qubit in range(36) if support >> qubit & 1)
                        if qubits not in EDGES:
                            break
                    saving += int((other[0] | other[1]).bit_count() == 2) - int(support.bit_count() == 2)
                middle.append(updated)
            if changed:
                break
    return rotations

def reorder(rotations, seed):
    rng = random.Random(seed)
    supports = [[qubit for qubit in range(36) if (first | second) >> qubit & 1] for first, second in rotations]
    predecessors = [set() for _ in rotations]
    successors = [set() for _ in rotations]
    history = [[] for _ in range(36)]
    for index, rotation in enumerate(rotations):
        for previous in {previous for qubit in supports[index] for previous in history[qubit]}:
            if anticommute(rotations[previous], rotation):
                predecessors[index].add(previous)
                successors[previous].add(index)
        for qubit in supports[index]:
            history[qubit].append(index)
    critical = [0] * len(rotations)
    for index in range(len(rotations) - 1, -1, -1):
        critical[index] = int(len(supports[index]) == 2) + max((critical[other] for other in successors[index]), default=0)
    ready = {index for index in range(len(rotations)) if not predecessors[index]}
    result = []
    while ready:
        selected = [index for index in ready if len(supports[index]) == 1]
        if not selected:
            graph = nx.Graph()
            for index in ready:
                first, second = supports[index]
                weight = critical[index] ** (1 + seed % 3) * (1 + rng.random() * (seed // 3 % 3) * 0.3) + rng.random() * 0.01
                if not graph.has_edge(first, second) or graph[first][second]['weight'] < weight:
                    graph.add_edge(first, second, weight=weight, index=index)
            matching = nx.max_weight_matching(graph, maxcardinality=bool(seed % 2))
            selected = [graph[first][second]['index'] for first, second in matching]
        for index in selected:
            result.append(rotations[index])
            ready.remove(index)
            for other in successors[index]:
                predecessors[other].remove(index)
                if not predecessors[other]:
                    ready.add(other)
    return result

def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('best_gates.json')
    iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    gates = [tuple(operation) for operation in json.loads(source.read_text())]
    rotations, frames = extract(gates)
    syn.save(native(rotations, frames), f'ppr_initial:{source}')
    rng = random.Random(7361)
    for iteration in range(iterations):
        rotations = cancel(rotations)
        rotations = conjugate_reduce(rotations)
        rotations = reorder(rotations, iteration)
        gates = syn.simplify(native(rotations, frames))
        edges = list(EDGES)
        rng.shuffle(edges)
        for edge in edges:
            gates = opt.pair_reduce(gates, edge)
        rotations, frames = extract(gates)
        syn.save(native(rotations, frames), f'ppr_optimized:{source}:{iteration}')
        Path('ppr_latest.json').write_text(json.dumps(gates) + '\n')

if __name__ == '__main__':
    main()
