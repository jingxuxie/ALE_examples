import heapq
from collections import deque

from router import graph_data, route


def embeddings(gates, count, neighbors, distances, initial, limit=16, budget=12000):
    logical_neighbors = [set() for _ in range(count)]
    for first, second in gates:
        logical_neighbors[first].add(second)
        logical_neighbors[second].add(first)
    if max(map(len, logical_neighbors)) > max(map(len, neighbors)):
        return []
    physical_neighbors = [set(values) for values in neighbors]
    mapping = [-1] * count
    unused = set(range(count))
    results = []
    visited = 0

    def search():
        nonlocal visited
        visited += 1
        if visited > budget or len(results) >= limit:
            return
        if not unused:
            results.append(mapping[:])
            return
        logical = max((wire for wire in range(count) if mapping[wire] < 0),
                      key=lambda wire: (sum(mapping[other] >= 0 for other in logical_neighbors[wire]),
                                        len(logical_neighbors[wire]), -wire))
        candidates = [node for node in unused if len(neighbors[node]) >= len(logical_neighbors[logical])
                      and all(mapping[other] < 0 or mapping[other] in physical_neighbors[node]
                              for other in logical_neighbors[logical])]
        candidates.sort(key=lambda node: (distances[initial[logical]][node], node))
        for node in candidates:
            mapping[logical] = node
            unused.remove(node)
            possible = True
            for other in logical_neighbors[logical]:
                if mapping[other] >= 0:
                    continue
                options = unused.intersection(physical_neighbors[node])
                if not any(len(neighbors[value]) >= len(logical_neighbors[other])
                           and all(mapping[linked] < 0 or mapping[linked] in physical_neighbors[value]
                                   for linked in logical_neighbors[other]) for value in options):
                    possible = False
                    break
            if possible:
                search()
            unused.add(node)
            mapping[logical] = -1
            if visited > budget or len(results) >= limit:
                break

    search()
    results.sort(key=lambda result: sum(distances[initial[wire]][result[wire]] for wire in range(count)))
    return results[:4]


def tree_plan(initial_state, neighbors, distances, root):
    count = len(initial_state)
    state = list(initial_state)
    tree = [set() for _ in range(count)]
    reached = {root}
    queue = deque([root])
    while queue:
        current = queue.popleft()
        for neighbor in neighbors[current]:
            if neighbor not in reached:
                reached.add(neighbor)
                queue.append(neighbor)
                tree[current].add(neighbor)
                tree[neighbor].add(current)
    active = set(range(count))
    operations = []
    while len(active) > 1:
        leaves = [node for node in active if len(tree[node].intersection(active)) == 1]
        leaf = min(leaves, key=lambda node: (distances[state.index(node)][node], node))
        source = state.index(leaf)
        parents = {source: None}
        queue = deque([source])
        while leaf not in parents:
            current = queue.popleft()
            for neighbor in neighbors[current]:
                if neighbor in active and neighbor not in parents:
                    parents[neighbor] = current
                    queue.append(neighbor)
        path = [leaf]
        while parents[path[-1]] is not None:
            path.append(parents[path[-1]])
        path.reverse()
        for first, second in zip(path, path[1:]):
            state[first], state[second] = state[second], state[first]
            operations.append((first, second))
        active.remove(leaf)
    if state != list(range(count)):
        raise RuntimeError("token tree plan failed")
    return operations


def token_plan(initial, target, neighbors, distances, edges, budget=2500):
    count = len(initial)
    state_list = [0] * count
    for logical, physical in enumerate(initial):
        state_list[physical] = target[logical]
    initial_state = tuple(state_list)
    roots = {0, count - 1, max(range(count), key=lambda node: len(neighbors[node]))}
    best = min((tree_plan(initial_state, neighbors, distances, root) for root in sorted(roots)), key=len)
    distance = sum(distances[node][destination] for node, destination in enumerate(initial_state))
    if len(best) <= (distance + 1) // 2:
        return best
    queue = [(0.75 * distance, distance, 0, initial_state)]
    costs = {initial_state: 0}
    parents = {}
    expanded = 0
    while queue and expanded < budget:
        priority, distance, cost, state = heapq.heappop(queue)
        if cost != costs[state] or cost + (distance + 1) // 2 >= len(best):
            continue
        expanded += 1
        for first, second in edges:
            if state[first] == first and state[second] == second:
                continue
            next_distance = distance - distances[first][state[first]] - distances[second][state[second]]
            next_distance += distances[first][state[second]] + distances[second][state[first]]
            next_cost = cost + 1
            if next_cost + (next_distance + 1) // 2 >= len(best):
                continue
            changed = list(state)
            changed[first], changed[second] = changed[second], changed[first]
            next_state = tuple(changed)
            if costs.get(next_state, count * count) <= next_cost:
                continue
            costs[next_state] = next_cost
            parents[next_state] = (state, (first, second))
            if next_distance == 0:
                candidate = []
                current = next_state
                while current != initial_state:
                    previous, edge = parents[current]
                    candidate.append(edge)
                    current = previous
                best = list(reversed(candidate))
            else:
                heapq.heappush(queue, (next_cost + 0.75 * next_distance, next_distance, next_cost, next_state))
    return best


def suffix_route(gates, count, edges, initial, cutoffs=(0, 4, 8, 12, 16, 24)):
    setting = {"name": "embedding-prefix", "horizon": 16, "decay": 0.9,
               "tie": "ascending", "mode": "weighted"}
    best = route(gates, count, edges, initial, setting)
    neighbors, distances = graph_data(count, edges)
    for cutoff in cutoffs:
        if cutoff >= len(gates):
            continue
        prefix = route(gates[:cutoff], count, edges, initial, setting)
        candidates = embeddings(gates[cutoff:], count, neighbors, distances, prefix["final_mapping"])
        for target in candidates:
            planned = token_plan(prefix["final_mapping"], target, neighbors, distances, edges)
            swaps = prefix["swaps"] + len(planned)
            if swaps >= best["swaps"]:
                continue
            operations = prefix["route"] + [["swap", first, second] for first, second in planned]
            operations += [["gate", index, target[gates[index][0]], target[gates[index][1]]]
                           for index in range(cutoff, len(gates))]
            best = {"swaps": swaps, "native_2q": len(gates) + 3 * swaps, "route": operations,
                    "final_mapping": target, "fallback_swaps": prefix["fallback_swaps"],
                    "embedding_cutoff": cutoff}
    return best
