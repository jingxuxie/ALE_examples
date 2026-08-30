from router import dependencies, graph_data, route, settings


def route_beam(gates, count, edges, initial, width=64, max_swaps=None,
               objective="unique_pairs", progress_weight=0.0, max_expansions=200000):
    _, distances = graph_data(count, edges)
    predecessors, _ = dependencies(gates, count)
    parent_masks = [sum(1 << parent for parent in parents) for parents in predecessors]
    complete_mask = (1 << len(gates)) - 1
    pair_masks = {}
    for index, gate in enumerate(gates):
        pair = tuple(sorted(gate))
        pair_masks[pair] = pair_masks.get(pair, 0) | (1 << index)
    ordered_edges = sorted(edges)
    expanded = 0
    incumbent = route(gates, count, edges, initial, settings()[0])
    depth_limit = max(0, incumbent["swaps"] - 1) if max_swaps is None else max_swaps
    budget_exhausted = False

    def drain(position, completed):
        for index, (left, right) in enumerate(gates):
            bit = 1 << index
            if not completed & bit and completed & parent_masks[index] == parent_masks[index]:
                if distances[position[left]][position[right]] == 1:
                    completed |= bit
        return completed

    def value(position, completed):
        pending = complete_mask ^ completed
        total = 0
        for (left, right), mask in pair_masks.items():
            remaining = mask & pending
            if remaining:
                weight = 1 if objective == "unique_pairs" else remaining.bit_count()
                total += weight * (distances[position[left]][position[right]] - 1)
        return total + progress_weight * pending.bit_count()

    initial_position = tuple(initial)
    initial_completed = drain(initial_position, 0)
    beam = [(initial_position, initial_completed, ())]
    retained = {(initial_position, initial_completed)}
    solution = () if initial_completed == complete_mask else None
    last_width = 1
    for depth in range(1, depth_limit + 1):
        if solution is not None:
            break
        candidates = {}
        for position, completed, path in beam:
            occupants = [0] * count
            for qubit, node in enumerate(position):
                occupants[node] = qubit
            for left, right in ordered_edges:
                if expanded >= max_expansions:
                    budget_exhausted = True
                    break
                expanded += 1
                changed = list(position)
                first, second = occupants[left], occupants[right]
                changed[first], changed[second] = right, left
                changed = tuple(changed)
                advanced = drain(changed, completed)
                key = changed, advanced
                if key in retained or key in candidates:
                    continue
                changed_path = path + ((left, right),)
                if advanced == complete_mask:
                    solution = changed_path
                    break
                candidates[key] = (value(changed, advanced), -advanced.bit_count(),
                                   changed, advanced, changed_path)
            if solution is not None or budget_exhausted:
                break
        if solution is not None or budget_exhausted or not candidates:
            break
        selected = sorted(candidates.values())[:width]
        beam = [(position, completed, path) for _, _, position, completed, path in selected]
        retained.update((position, completed) for position, completed, _ in beam)
        last_width = len(beam)
    if solution is None:
        fallback = incumbent
        fallback.update({"beam_succeeded": False, "expanded_states": expanded,
                         "beam_width": width, "last_width": last_width,
                         "budget_exhausted": budget_exhausted, "depth_limit": depth_limit,
                         "incumbent_swaps": incumbent["swaps"]})
        return fallback
    position = list(initial)
    occupants = [0] * count
    for qubit, node in enumerate(position):
        occupants[node] = qubit
    operations = []
    completed = 0

    def emit_gates():
        nonlocal completed
        for index, (left, right) in enumerate(gates):
            bit = 1 << index
            if not completed & bit and completed & parent_masks[index] == parent_masks[index]:
                if distances[position[left]][position[right]] == 1:
                    operations.append(["gate", index, position[left], position[right]])
                    completed |= bit

    emit_gates()
    for left, right in solution:
        first, second = occupants[left], occupants[right]
        occupants[left], occupants[right] = second, first
        position[first], position[second] = right, left
        operations.append(["swap", left, right])
        emit_gates()
    assert completed == complete_mask
    return {"swaps": len(solution), "native_2q": len(gates) + 3 * len(solution),
            "route": operations, "final_mapping": position, "fallback_swaps": 0,
            "beam_succeeded": True, "expanded_states": expanded, "beam_width": width,
            "budget_exhausted": budget_exhausted, "depth_limit": depth_limit,
            "incumbent_swaps": incumbent["swaps"]}
