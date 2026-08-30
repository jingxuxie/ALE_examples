import random
from collections import deque


def hardware(name):
    if name == "ring16":
        count = 16
        edges = [(node, (node + 1) % count) for node in range(count)]
    elif name == "grid16":
        count = 16
        edges = [(node, node + 1) for node in range(count) if node % 4 < 3]
        edges += [(node, node + 4) for node in range(12)]
    elif name == "ladder16":
        count = 16
        edges = [(node, node + 1) for node in range(count) if node % 8 < 7]
        edges += [(node, node + 8) for node in range(8)]
    else:
        raise ValueError("unknown hardware")
    return count, sorted({tuple(sorted(edge)) for edge in edges})


def graph_data(count, edges):
    neighbors = [[] for _ in range(count)]
    for left, right in edges:
        neighbors[left].append(right)
        neighbors[right].append(left)
    for adjacent in neighbors:
        adjacent.sort()
    distances = []
    for source in range(count):
        row = [count + 1] * count
        row[source] = 0
        pending = deque([source])
        while pending:
            current = pending.popleft()
            for neighbor in neighbors[current]:
                if row[neighbor] > row[current] + 1:
                    row[neighbor] = row[current] + 1
                    pending.append(neighbor)
        distances.append(row)
    return neighbors, distances


def dependencies(gates, count):
    previous = [-1] * count
    predecessors = []
    successors = [[] for _ in gates]
    for index, (left, right) in enumerate(gates):
        parents = sorted({previous[left], previous[right]} - {-1})
        predecessors.append(parents)
        for parent in parents:
            successors[parent].append(index)
        previous[left] = previous[right] = index
    return predecessors, successors


def settings():
    variants = []
    for horizon in (2, 4, 8, 16):
        for decay in (0.5, 0.9):
            for tie in ("ascending", "seeded"):
                variants.append({"name": f"weighted-{horizon}-{decay}-{tie}",
                                 "horizon": horizon, "decay": decay,
                                 "tie": tie, "mode": "weighted"})
    for tie in ("ascending", "descending"):
        variants.append({"name": f"lexicographic-8-{tie}", "horizon": 8,
                         "decay": 1.0, "tie": tie, "mode": "lexicographic"})
    return variants


def relabelings(count):
    identity = list(range(count))
    result = [("identity", identity[:], identity[:])]
    for name, seed, change_logical, change_physical in (
        ("physical-11", 11, False, True),
        ("physical-29", 29, False, True),
        ("logical-47", 47, True, False),
        ("joint-71", 71, True, True),
        ("joint-103", 103, True, True),
    ):
        generator = random.Random(seed)
        logical, physical = identity[:], identity[:]
        if change_logical:
            generator.shuffle(logical)
        if change_physical:
            generator.shuffle(physical)
        result.append((name, logical, physical))
    return result


def transform(gates, edges, logical, physical):
    initial = [0] * len(logical)
    for qubit in range(len(logical)):
        initial[logical[qubit]] = physical[qubit]
    mapped_gates = [(logical[left], logical[right]) for left, right in gates]
    mapped_edges = sorted(tuple(sorted((physical[left], physical[right])))
                          for left, right in edges)
    return mapped_gates, mapped_edges, initial


def route(gates, count, edges, initial, setting):
    neighbors, distances = graph_data(count, edges)
    predecessors, successors = dependencies(gates, count)
    remaining = [len(parents) for parents in predecessors]
    front = {index for index, parents in enumerate(predecessors) if not parents}
    pending = set(range(len(gates)))
    position = list(initial)
    occupants = [0] * count
    for qubit, node in enumerate(position):
        occupants[node] = qubit
    operations = []
    swaps = 0
    fallback_swaps = 0
    stalled = 0
    visited = {tuple(position)}
    ranked_edges = list(edges)
    if setting["tie"] == "descending":
        ranked_edges.reverse()
    elif setting["tie"] == "seeded":
        random.Random(1729).shuffle(ranked_edges)
    rank = {edge: index for index, edge in enumerate(ranked_edges)}

    def apply_swap(edge):
        nonlocal swaps
        left, right = edge
        first, second = occupants[left], occupants[right]
        occupants[left], occupants[right] = second, first
        position[first], position[second] = right, left
        operations.append(["swap", left, right])
        swaps += 1

    def execute(index):
        left, right = gates[index]
        operations.append(["gate", index, position[left], position[right]])
        front.remove(index)
        pending.remove(index)
        for child in successors[index]:
            remaining[child] -= 1
            if remaining[child] == 0:
                front.add(child)

    while pending:
        executable = sorted(index for index in front
                            if distances[position[gates[index][0]]][position[gates[index][1]]] == 1)
        if executable:
            for index in executable:
                execute(index)
            visited = {tuple(position)}
            stalled = 0
            continue
        depth = [0] * len(gates)
        slices = [[] for _ in range(setting["horizon"])]
        for index in sorted(pending):
            level = max((depth[parent] + 1 for parent in predecessors[index]
                         if parent in pending), default=0)
            depth[index] = level
            if level < len(slices):
                slices[level].append(gates[index])
        active = {position[qubit] for index in front for qubit in gates[index]}
        candidates = [edge for edge in edges if active.intersection(edge)]
        scored = []
        for edge in candidates:
            left, right = edge
            first, second = occupants[left], occupants[right]
            position[first], position[second] = right, left
            state = tuple(position)
            if state not in visited:
                values = [sum(distances[position[first_qubit]][position[second_qubit]] - 1
                              for first_qubit, second_qubit in layer) / max(1, len(layer))
                          for layer in slices]
                if setting["mode"] == "lexicographic":
                    score = tuple(values)
                else:
                    score = (sum(value * setting["decay"] ** level
                                 for level, value in enumerate(values)),)
                scored.append((score, rank[edge], edge))
            position[first], position[second] = left, right
        if scored and stalled < 2 * count:
            chosen = min(scored)[2]
            apply_swap(chosen)
            visited.add(tuple(position))
            stalled += 1
        else:
            index = min(front, key=lambda item: (
                distances[position[gates[item][0]]][position[gates[item][1]]], item))
            first, second = gates[index]
            current, destination = position[first], position[second]
            while distances[current][destination] > 1:
                next_node = min(node for node in neighbors[current]
                                if distances[node][destination] == distances[current][destination] - 1)
                apply_swap(tuple(sorted((current, next_node))))
                fallback_swaps += 1
                current = next_node
            execute(index)
            visited = {tuple(position)}
            stalled = 0
    return {"swaps": swaps, "native_2q": len(gates) + 3 * swaps,
            "route": operations, "final_mapping": position,
            "fallback_swaps": fallback_swaps}
