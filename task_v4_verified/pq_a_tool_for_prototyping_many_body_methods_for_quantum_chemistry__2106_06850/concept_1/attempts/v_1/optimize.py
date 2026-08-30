import time

from model import dynamic_program


def reachable(graph, choices, roots=None, stop=None):
    pending = list(graph.roots if roots is None else roots)
    used = set()
    while pending:
        number = pending.pop()
        if number in used or graph.nodes[number].source is not None:
            continue
        used.add(number)
        if number != stop:
            pending.extend(choices[number][:2])
    return used


def score(graph, choices):
    return sum(choices[number][5] for number in reachable(graph, choices))


def initial(graph, exponent):
    weights = [1.0 / max(1, node.potential) ** exponent for node in graph.nodes]
    table = dynamic_program(graph, set(), graph.cap, weights)
    choices = [records[0][3] if records else None for records in table]
    assigned = set()

    def assign(record):
        number = record[2]
        if number in assigned or record[3] is None:
            return
        assigned.add(number)
        choices[number] = record[3]
        assign(record[4])
        assign(record[5])

    for root in sorted(graph.roots, key=lambda root: -graph.nodes[root].base):
        assign(table[root][0])
    return choices


def incremental(graph, free, maximum=7):
    costs = [float('inf')] * len(graph.nodes)
    choices = [None] * len(graph.nodes)
    for number in graph.order:
        node = graph.nodes[number]
        if node.count > maximum:
            break
        if node.source is not None or number in free:
            costs[number] = 0
            continue
        best = float('inf')
        for op in node.ops:
            first, second = op[:2]
            allocation = node.size + sum(graph.nodes[child].size for child in set(op[:2]) if graph.nodes[child].source is None)
            if allocation > graph.cap:
                continue
            value = costs[first] + (costs[second] if first != second else 0) + op[5]
            if value < best:
                best = value
                choices[number] = op
        costs[number] = best
    return choices


def install(graph, choices, additions, number, free):
    pending = [number]
    installed = set()
    while pending:
        current = pending.pop()
        if current in free or current in installed or graph.nodes[current].source is not None:
            continue
        if additions[current] is None:
            return False
        installed.add(current)
        choices[current] = additions[current]
        pending.extend(additions[current][:2])
    return True


def improve(graph, choices, deadline, roots=None, passes=2):
    roots = graph.roots if roots is None else roots
    for iteration in range(passes):
        changed = False
        used = reachable(graph, choices, roots)
        for number in sorted(used, key=lambda number: (-graph.nodes[number].count, -graph.nodes[number].base)):
            if time.monotonic() >= deadline:
                return choices
            used = reachable(graph, choices, roots)
            if number not in used:
                continue
            outside = reachable(graph, choices, roots, stop=number)
            outside.discard(number)
            additions = incremental(graph, outside, graph.nodes[number].count)
            proposed = choices.copy()
            if not install(graph, proposed, additions, number, outside):
                continue
            old_cost = sum(choices[node][5] for node in used)
            new_cost = sum(proposed[node][5] for node in reachable(graph, proposed, roots))
            if new_cost < old_cost:
                choices = proposed
                changed = True
        if not changed:
            break
    return choices


def optimize(graph, deadline):
    candidates = []
    seen = set()
    for exponent in (0.0, 0.5, 1.0, 1.5, 2.0):
        choices = improve(graph, initial(graph, exponent), deadline)
        key = tuple((number, choices[number][:2]) for number in sorted(reachable(graph, choices)))
        if key not in seen:
            seen.add(key)
            candidates.append((score(graph, choices), choices))
        if time.monotonic() >= deadline:
            break
    candidates.sort(key=lambda pair: pair[0])
    best_score, best = candidates[0]
    attempted = set()
    while time.monotonic() < deadline:
        used = reachable(graph, best)
        additions = incremental(graph, used)
        optional = [number for number in graph.order if number not in used and number not in attempted
                    and graph.nodes[number].source is None and graph.nodes[number].potential > 1
                    and additions[number] is not None]
        if not optional:
            break
        optional.sort(key=lambda number: graph.nodes[number].base * (graph.nodes[number].potential - 1), reverse=True)
        number = optional[0]
        attempted.add(number)
        proposed = best.copy()
        if not install(graph, proposed, additions, number, used):
            continue
        proposed = improve(graph, proposed, deadline, roots=graph.roots + [number], passes=1)
        cost = score(graph, proposed)
        if cost < best_score:
            best_score, best = cost, proposed
            candidates.append((cost, proposed))
    candidates.sort(key=lambda pair: pair[0])
    return [choices for cost, choices in candidates[:3]]
