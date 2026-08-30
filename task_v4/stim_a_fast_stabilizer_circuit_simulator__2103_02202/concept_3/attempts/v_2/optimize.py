import collections
import heapq
import json
import random
import sys
from pathlib import Path

import networkx as nx
import synthesis as syn

def twoqubit_words():
    initial = (1, 4, 2, 8)
    distances = {initial: 0}
    paths = {initial: ()}
    queue = [(0, initial)]
    options = [('H', 0), ('S', 0), ('H', 1), ('S', 1), ('CX', 0, 1), ('CX', 1, 0)]
    while queue:
        distance, state = heapq.heappop(queue)
        if distance != distances[state]:
            continue
        for operation in options:
            updated = list(state)
            gate, first = operation[:2]
            if gate == 'H':
                updated[2 * first], updated[2 * first + 1] = updated[2 * first + 1], updated[2 * first]
            elif gate == 'S':
                updated[2 * first + 1] ^= updated[2 * first]
            else:
                second = operation[2]
                updated[2 * second] ^= updated[2 * first]
                updated[2 * first + 1] ^= updated[2 * second + 1]
            updated = tuple(updated)
            candidate = distance + (1000 if gate == 'CX' else 1)
            if candidate < distances.get(updated, 1000000):
                distances[updated] = candidate
                paths[updated] = paths[state] + (operation,)
                heapq.heappush(queue, (candidate, updated))
    assert len(paths) == 720
    return paths

PAIRS = twoqubit_words()

def pair_reduce(gates, edge):
    positions = []
    replacements = {}
    removed = set()
    mapping = {edge[0]: 0, edge[1]: 1}
    def flush():
        if not positions:
            return
        state = [1, 4, 2, 8]
        count = 0
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
                count += 1
        word = PAIRS[tuple(state)]
        newcount = sum(operation[0] == 'CX' for operation in word)
        if (newcount, len(word)) < (count, len(positions)):
            replacements[positions[0]] = [(operation[0], *(edge[qubit] for qubit in operation[1:])) for operation in word]
            removed.update(positions)
        positions.clear()
    for index, operation in enumerate(gates):
        overlap = any(qubit in mapping for qubit in operation[1:])
        if not overlap:
            continue
        if all(qubit in mapping for qubit in operation[1:]):
            positions.append(index)
        else:
            flush()
    flush()
    return [operation for index, original in enumerate(gates) for operation in (replacements.get(index, []) if index in removed else [original])]

def commute(first, second):
    if not any(qubit in second[1:] for qubit in first[1:]):
        return True
    if first == second:
        return True
    if first[0] == second[0] == 'CX':
        return first[1] != second[2] and first[2] != second[1]
    if first[0] == 'CX':
        first, second = second, first
    return first[0] == 'S' and second[0] == 'CX' and first[1] == second[1]

def cancel(gates):
    result = []
    for operation in gates:
        for index in range(len(result) - 1, -1, -1):
            previous = result[index]
            if previous is None:
                continue
            if previous == operation:
                result[index] = None
                break
            if not commute(operation, previous):
                result.append(operation)
                break
        else:
            result.append(operation)
    return [operation for operation in result if operation is not None]

def reorder(gates, seed):
    rng = random.Random(seed)
    count = len(gates)
    predecessors = [set() for _ in gates]
    successors = [set() for _ in gates]
    wire_history = [[] for _ in range(36)]
    for index, operation in enumerate(gates):
        previous = set(previous for qubit in operation[1:] for previous in wire_history[qubit])
        for other in previous:
            if not commute(gates[other], operation):
                predecessors[index].add(other)
                successors[other].add(index)
        for qubit in operation[1:]:
            wire_history[qubit].append(index)
    critical = [0] * count
    for index in range(count - 1, -1, -1):
        critical[index] = int(gates[index][0] == 'CX') + max((critical[other] for other in successors[index]), default=0)
    ready = {index for index in range(count) if not predecessors[index]}
    result = []
    while ready:
        singles = [index for index in ready if gates[index][0] != 'CX']
        if singles:
            selected = singles
        else:
            graph = nx.Graph()
            for index in ready:
                first, second = gates[index][1:]
                weight = critical[index] ** (1 + seed % 3) * (1 + rng.random() * (seed // 3 % 3) * 0.25)
                weight += rng.random() * 0.01
                if not graph.has_edge(first, second) or weight > graph[first][second]['weight']:
                    graph.add_edge(first, second, weight=weight, index=index)
            matching = nx.max_weight_matching(graph, maxcardinality=bool(seed % 2))
            selected = [graph[first][second]['index'] for first, second in matching]
        for index in selected:
            result.append(gates[index])
            ready.remove(index)
            for other in successors[index]:
                predecessors[other].remove(index)
                if not predecessors[other]:
                    ready.add(other)
    assert len(result) == len(gates)
    return result

def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('best_gates.json')
    iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    gates = [tuple(operation) for operation in json.loads(source.read_text())]
    rng = random.Random(6487)
    for iteration in range(iterations):
        gates = cancel(syn.simplify(gates))
        edges = CONSTRAINT_EDGES[:]
        rng.shuffle(edges)
        for edge in edges:
            gates = pair_reduce(gates, edge)
        gates = cancel(syn.simplify(gates))
        gates = reorder(gates, iteration)
        result = syn.save(gates[:], f'optimized:{source}:{iteration}')
        Path('optimized_latest.json').write_text(json.dumps(gates) + '\n')

CONSTRAINT_EDGES = [tuple(edge) for edge in syn.CONSTRAINTS['edges']]

if __name__ == '__main__':
    main()
