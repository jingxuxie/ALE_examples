import collections
import json
import math
import random
import sys


def route(instance, lookahead, future_weight, decay_weight, seed):
    generator = random.Random(seed)
    count = instance["n"]
    gates = instance["gates"]
    adjacency = [[] for _ in range(count)]
    weights = {}
    for first, second, weight in instance["edges"]:
        adjacency[first].append(second)
        adjacency[second].append(first)
        weights[tuple(sorted((first, second)))] = weight
    distance = [[math.inf] * count for _ in range(count)]
    for first in range(count):
        distance[first][first] = 0
        for second in adjacency[first]:
            distance[first][second] = 1 + 0.15 * weights[tuple(sorted((first, second)))]
    for middle in range(count):
        for first in range(count):
            for second in range(count):
                distance[first][second] = min(distance[first][second], distance[first][middle] + distance[middle][second])
    predecessors = [set() for _ in gates]
    successors = [[] for _ in gates]
    latest = [-1] * count
    for gate_index, pair in enumerate(gates):
        for logical in pair:
            if latest[logical] >= 0:
                predecessors[gate_index].add(latest[logical])
            latest[logical] = gate_index
        for previous in predecessors[gate_index]:
            successors[previous].append(gate_index)
    remaining = [len(values) for values in predecessors]
    ready = {index for index, value in enumerate(remaining) if value == 0}
    done = [False] * len(gates)
    positions = instance["initial"][:]
    occupants = [0] * count
    for logical, physical in enumerate(positions):
        occupants[physical] = logical
    depths = [0] * count
    touched = [0] * count
    operations = []
    work = 0.0
    stalled = 0
    step = 0
    previous_swap = None

    def emit_swap(first, second):
        nonlocal work, step, previous_swap
        edge = tuple(sorted((first, second)))
        work += 3 * weights[edge]
        finish = max(depths[first], depths[second]) + 3
        depths[first] = finish
        depths[second] = finish
        occupants[first], occupants[second] = occupants[second], occupants[first]
        positions[occupants[first]] = first
        positions[occupants[second]] = second
        operations.append(["swap", first, second])
        step += 1
        touched[first] = step
        touched[second] = step
        previous_swap = edge

    while ready:
        executable = [index for index in sorted(ready) if tuple(sorted((positions[gates[index][0]], positions[gates[index][1]]))) in weights]
        if executable:
            for gate_index in executable:
                logical_first, logical_second = gates[gate_index]
                first, second = positions[logical_first], positions[logical_second]
                work += weights[tuple(sorted((first, second)))]
                finish = max(depths[first], depths[second]) + 1
                depths[first] = finish
                depths[second] = finish
                operations.append(["gate", gate_index])
                ready.remove(gate_index)
                done[gate_index] = True
                for following in successors[gate_index]:
                    remaining[following] -= 1
                    if remaining[following] == 0:
                        ready.add(following)
            stalled = 0
            previous_swap = None
            continue
        stalled += 1
        if stalled > count * 2:
            gate_index = min(ready)
            source, target = [positions[logical] for logical in gates[gate_index]]
            queue = collections.deque([source])
            parents = {source: None}
            while target not in parents:
                current = queue.popleft()
                for neighbor in adjacency[current]:
                    if neighbor not in parents:
                        parents[neighbor] = current
                        queue.append(neighbor)
            path = [target]
            while parents[path[-1]] is not None:
                path.append(parents[path[-1]])
            path.reverse()
            for first, second in zip(path[:-2], path[1:-1]):
                emit_swap(first, second)
            stalled = 0
            continue
        frontier = sorted(ready)
        future = []
        pending = collections.deque(frontier)
        visited = set(frontier)
        while pending and len(future) < lookahead:
            gate_index = pending.popleft()
            for following in successors[gate_index]:
                if following not in visited and not done[following]:
                    visited.add(following)
                    future.append(following)
                    pending.append(following)
                    if len(future) >= lookahead:
                        break
        candidates = set()
        for gate_index in frontier:
            for logical in gates[gate_index]:
                first = positions[logical]
                for second in adjacency[first]:
                    candidates.add(tuple(sorted((first, second))))
        best = None
        for first, second in sorted(candidates):
            logical_first, logical_second = occupants[first], occupants[second]
            positions[logical_first], positions[logical_second] = second, first
            front_score = sum(distance[positions[gates[index][0]]][positions[gates[index][1]]] for index in frontier) / len(frontier)
            future_score = sum(distance[positions[gates[index][0]]][positions[gates[index][1]]] for index in future) / max(1, len(future))
            recency = max(0, 5 - min(step - touched[first], step - touched[second]))
            score = front_score + future_weight * future_score + decay_weight * recency + 0.025 * weights[(first, second)]
            if (first, second) == previous_swap:
                score += 0.6
            score += generator.random() * 0.00001
            positions[logical_first], positions[logical_second] = first, second
            candidate = (score, first, second)
            if best is None or candidate < best:
                best = candidate
        emit_swap(best[1], best[2])
    return {"operations": operations}, work + 0.05 * max(depths)


def solve(instance):
    configurations = [(12, 0.35, 0.0, 10), (24, 0.55, 0.015, 20),
                      (40, 0.75, 0.025, 30), (64, 1.0, 0.01, 40)]
    results = [route(instance, *configuration) for configuration in configurations]
    return min(results, key=lambda result: result[1])[0]


if __name__ == "__main__":
    print(json.dumps(solve(json.load(sys.stdin))))
