import random

from router import dependencies, graph_data


def general_settings():
    result = []
    for horizon in (8, 32):
        for decay in (0.5, 0.9, 1.0):
            for objective in ("layer_mean", "layer_sum", "unique_pairs"):
                for candidate_scope in ("front", "all"):
                    for front_weight in (1.0, 4.0):
                        for tie in ("ascending", "descending", "seeded"):
                            result.append({"name": f"general-{horizon}-{decay}-{objective}-{candidate_scope}-{front_weight}-{tie}",
                                "implementation": "general", "horizon": horizon, "decay": decay,
                                "objective": objective, "candidate_scope": candidate_scope,
                                "front_weight": front_weight, "tie": tie, "seed": 1729})
    return result


def route_general(gates, count, edges, initial, setting):
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
        random.Random(setting.get("seed", 1729)).shuffle(ranked_edges)
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
        weighted_pairs = {}
        layer_counts = [0] * setting["horizon"]
        for index in sorted(pending):
            level = max((depth[parent] + 1 for parent in predecessors[index] if parent in pending), default=0)
            depth[index] = level
            if level < setting["horizon"]:
                layer_counts[level] += 1
        for index in sorted(pending):
            level = depth[index]
            if level >= setting["horizon"]:
                continue
            pair = tuple(sorted(gates[index]))
            weight = setting["decay"] ** level
            if level == 0:
                weight *= setting["front_weight"]
            if setting["objective"] == "layer_mean":
                weight /= layer_counts[level]
            if setting["objective"] == "unique_pairs":
                weighted_pairs[pair] = max(weighted_pairs.get(pair, 0), weight)
            else:
                weighted_pairs[pair] = weighted_pairs.get(pair, 0) + weight
        active = {position[qubit] for index in front for qubit in gates[index]}
        candidates = edges if setting["candidate_scope"] == "all" else [
            edge for edge in edges if active.intersection(edge)]
        scored = []
        for edge in candidates:
            left, right = edge
            first, second = occupants[left], occupants[right]
            position[first], position[second] = right, left
            state = tuple(position)
            if state not in visited:
                score = sum(weight * (distances[position[first_qubit]][position[second_qubit]] - 1)
                            for (first_qubit, second_qubit), weight in weighted_pairs.items())
                scored.append((score, rank[edge], edge))
            position[first], position[second] = left, right
        if scored and stalled < 2 * count:
            apply_swap(min(scored)[2])
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
            "route": operations, "final_mapping": position, "fallback_swaps": fallback_swaps}
