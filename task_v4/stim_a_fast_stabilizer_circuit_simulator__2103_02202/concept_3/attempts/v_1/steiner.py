import collections
import json
import random
import sys

import networkx as nx
from networkx.algorithms.approximation.steinertree import steiner_tree

import greedy
import synthesize


def eliminate(input_rows, seed=0):
    randomizer = random.Random(seed)
    columns = greedy.transpose(input_rows)
    graph = nx.Graph()
    for first, second in greedy.EDGES:
        graph.add_edge(first, second, weight=1 + randomizer.random() * 0.01)
    remaining = set(range(36))
    history = []
    depths = [0] * 36
    mode = seed % 5

    def pauli(row, qubit):
        return ((columns[qubit][0] >> row) & 1, (columns[qubit][1] >> row) & 1)

    def weight(pair, qubit):
        if mode == 0:
            return greedy.weight(pair)
        xlow, xhigh = pair[0] & greedy.MASK, pair[0] >> 36
        zlow, zhigh = pair[1] & greedy.MASK, pair[1] >> 36
        support = xlow | xhigh | zlow | zhigh
        determinants = (xlow & zhigh) ^ (xhigh & zlow)
        total = 0
        while support:
            bit = support & -support
            other = bit.bit_length() - 1
            distance = abs(qubit // 6 - other // 6) + abs(qubit % 6 - other % 6)
            coefficient = distance + 1 if mode == 1 else distance * distance + 1 if mode == 2 else 1.5 ** distance if mode == 3 else 1
            total += coefficient * (2 + int(bool(determinants & bit)))
            support ^= bit
        return total

    def operate(move):
        first, second, axis_first, axis_second = move
        columns[first], columns[second] = greedy.entangle(columns[first], columns[second], axis_first, axis_second)
        history.append(move)
        depths[first] = depths[second] = max(depths[first], depths[second]) + 1

    while remaining:
        candidates = []
        for qubit in remaining:
            if synthesize.connected(remaining - {qubit}):
                counts = [sum(pauli(row, other) != (0, 0) for other in remaining) for row in (qubit, qubit + 36)]
                candidates.append((sum(counts) + randomizer.random() * (4 if seed >= 10 else 0.2), qubit))
        pivot = min(candidates)[1]
        for stage in range(2):
            row = pivot + 36 * stage
            terminals = {qubit for qubit in remaining if pauli(row, qubit) != (0, 0)} | {pivot}
            if len(terminals) == 1:
                continue
            subtree = steiner_tree(graph, terminals)
            parents = {pivot: None}
            order = [pivot]
            for node in order:
                for neighbor in subtree.neighbors(node):
                    if neighbor not in parents:
                        parents[neighbor] = node
                        order.append(neighbor)
            children = {node: 0 for node in order}
            for node, parent in parents.items():
                if parent is not None:
                    children[parent] += 1
            leaves = {node for node in order if node != pivot and children[node] == 0}
            while leaves:
                proposals = []
                for child in leaves:
                    parent = parents[child]
                    child_pauli = pauli(row, child)
                    if child_pauli == (0, 0):
                        proposals.append((-1e50, child, []))
                        continue
                    child_axis = greedy.AXES.index(child_pauli)
                    parent_pauli = pauli(row, parent)
                    old = weight(columns[child], child) + weight(columns[parent], parent)
                    if parent_pauli != (0, 0):
                        parent_axes = [axis for axis in range(3) if greedy.AXES[axis] != parent_pauli]
                        if stage == 1 and parent == pivot:
                            parent_axes = [greedy.AXES.index(pauli(pivot, pivot))]
                        for parent_axis in parent_axes:
                            updated = greedy.entangle(columns[child], columns[parent], child_axis, parent_axis)
                            delta = weight(updated[0], child) + weight(updated[1], parent) - old
                            proposals.append((delta + randomizer.random() * 0.02, child, [(child, parent, child_axis, parent_axis)]))
                    else:
                        for first_child_axis in range(3):
                            if first_child_axis == child_axis:
                                continue
                            for first_parent_axis in range(3):
                                interim = greedy.entangle(columns[child], columns[parent], first_child_axis, first_parent_axis)
                                for last_parent_axis in range(3):
                                    if last_parent_axis == first_parent_axis:
                                        continue
                                    updated = greedy.entangle(*interim, child_axis, last_parent_axis)
                                    delta = weight(updated[0], child) + weight(updated[1], parent) - old
                                    moves = [(child, parent, first_child_axis, first_parent_axis), (child, parent, child_axis, last_parent_axis)]
                                    proposals.append((delta / 2 + randomizer.random() * 0.02, child, moves))
                _, child, moves = min(proposals)
                for move in moves:
                    operate(move)
                assert pauli(row, child) == (0, 0)
                leaves.remove(child)
                parent = parents[child]
                children[parent] -= 1
                if children[parent] == 0 and parent != pivot:
                    leaves.add(parent)
        for other in remaining - {pivot}:
            assert pauli(pivot, other) == (0, 0)
            assert pauli(pivot + 36, other) == (0, 0)
        remaining.remove(pivot)
        graph.remove_node(pivot)
    result = []
    for qubit in range(36):
        ximage, zimage = pauli(qubit, qubit), pauli(qubit + 36, qubit)
        frame = (*ximage, 0, *zimage, 0)
        result.extend((name, (qubit,)) for name in synthesize.FRAME_WORDS[frame])
    for move in reversed(history):
        result.extend(synthesize.generalized(*move))
    return result


if __name__ == '__main__':
    synthesize.eliminate = eliminate
    path = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != '-' else None
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    for seed in range(start, start + count):
        synthesize.build(path, seed)
