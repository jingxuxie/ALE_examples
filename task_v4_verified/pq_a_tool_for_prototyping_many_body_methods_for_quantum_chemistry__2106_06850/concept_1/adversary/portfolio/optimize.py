import heapq
import math
import random
import time


def feasible_edges(graph):
    available = set()
    allowed = {}
    for node_id in graph.topological:
        node = graph.nodes[node_id]
        if node.tensor:
            available.add(node_id)
            continue
        allowed[node_id] = []
        for edge_id in node.edges:
            edge = graph.edges[edge_id]
            allocation = node.size + sum(graph.nodes[child].size for child in set(edge.children))
            if all(child in available for child in edge.children) and allocation <= graph.case['memory_cap']:
                allowed[node_id].append(edge_id)
        if allowed[node_id]:
            available.add(node_id)
    return allowed


def weighted_choices(graph, allowed, weights=None, cached=(), seed=0, noise=0):
    rng = random.Random(seed)
    costs = [math.inf] * len(graph.nodes)
    choices = dict(graph.base_choices)
    cached = set(cached)
    for node_id in graph.topological:
        node = graph.nodes[node_id]
        if node.tensor or node_id in cached:
            costs[node_id] = 0
            continue
        for edge_id in allowed[node_id]:
            edge = graph.edges[edge_id]
            factor = 1 if weights is None else weights.get(node_id, 1)
            cost = edge.cost * factor * math.exp(rng.uniform(-noise, noise)) + sum(costs[child] for child in edge.children)
            if cost < costs[node_id]:
                costs[node_id] = cost
                choices[node_id] = edge_id
    return choices


def coordinate_search(graph, allowed, choices, seed=0, sweeps=5, group_size=1):
    rng = random.Random(seed)
    choices = dict(choices)
    roots = sorted({root[0] for root in graph.roots})
    best_cost = graph.cost(choices)
    for sweep in range(sweeps):
        improved = False
        rng.shuffle(roots)
        for offset in range(0, len(roots), group_size):
            selected = roots[offset:offset + group_size]
            other = set(roots) - set(selected)
            active = graph.reachable(choices, other)
            candidate = dict(choices)
            for root in selected:
                local = weighted_choices(graph, allowed, cached=active)
                stack = [root]
                while stack:
                    node_id = stack.pop()
                    if node_id in active or graph.nodes[node_id].tensor:
                        continue
                    candidate[node_id] = local[node_id]
                    active.add(node_id)
                    stack.extend(graph.edges[local[node_id]].children)
            cost = graph.cost(candidate)
            if cost < best_cost:
                choices, best_cost = candidate, cost
                improved = True
        if not improved:
            break
    return choices


def joint_lp_search(graph, allowed, incumbent, seconds=30, node_limit=2000):
    import numpy as np
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix
    from certificate import from_duals, integer_lower_bound

    started = time.monotonic()
    incumbent = coordinate_search(graph, allowed, incumbent, sweeps=10)
    upper = graph.cost(incumbent)
    edge_ids = [edge_id for node_id in graph.topological for edge_id in allowed.get(node_id, []) if graph.edges[edge_id].cost <= upper]
    edge_position = {edge_id: position for position, edge_id in enumerate(edge_ids)}
    node_edges = {node_id: [edge_position[edge_id] for edge_id in allowed.get(node_id, []) if edge_id in edge_position] for node_id in range(len(graph.nodes))}
    roots = {root[0] for root in graph.roots}
    rows, columns, values, rhs = [], [], [], []
    equal_rows, equal_columns, equal_values, equal_rhs = [], [], [], []
    inequalities, equalities = [], []
    for node_id, positions in node_edges.items():
        if graph.nodes[node_id].tensor:
            continue
        if node_id in roots:
            equal_rows.extend([len(equal_rhs)] * len(positions))
            equal_columns.extend(positions)
            equal_values.extend([1] * len(positions))
            equal_rhs.append(1)
            equalities.append(node_id)
        else:
            rows.extend([len(rhs)] * len(positions))
            columns.extend(positions)
            values.extend([1] * len(positions))
            rhs.append(1)
            inequalities.append(('node', node_id))
    for position, edge_id in enumerate(edge_ids):
        for child in set(graph.edges[edge_id].children):
            if graph.nodes[child].tensor:
                continue
            rows.extend([len(rhs)] * (1 + len(node_edges[child])))
            columns.extend([position] + node_edges[child])
            values.extend([1] + [-1] * len(node_edges[child]))
            rhs.append(0)
            inequalities.append(('dependency', edge_id, child))
    matrix = coo_matrix((values, (rows, columns)), shape=(len(rhs), len(edge_ids))).tocsc()
    equal_matrix = coo_matrix((equal_values, (equal_rows, equal_columns)), shape=(len(equal_rhs), len(edge_ids))).tocsc()
    scale = max(1, upper / 1e8)
    objective = np.array([graph.edges[edge_id].cost / scale for edge_id in edge_ids])
    initial_bounds = np.array([[0.0, 1.0]] * len(edge_ids))
    queue = [(0.0, 0, initial_bounds)]
    serial = 1
    explored = 0
    root_lower = None
    root_certificate = None
    cutoff = upper
    tolerance = max(0.01, upper * 1e-10)
    statuses = []
    while queue and time.monotonic() - started < seconds and explored < node_limit:
        lower, _, bounds = heapq.heappop(queue)
        if lower >= upper - tolerance:
            continue
        result = linprog(objective, A_ub=matrix, b_ub=np.array(rhs), A_eq=equal_matrix,
                         b_eq=np.array(equal_rhs), bounds=bounds, method='highs',
                         options={'time_limit': max(0.01, seconds - (time.monotonic() - started)),
                                  'dual_feasibility_tolerance': 1e-9, 'primal_feasibility_tolerance': 1e-9})
        explored += 1
        if result.status == 2:
            continue
        if not result.success:
            statuses.append({'status': int(result.status), 'message': str(result.message)})
            heapq.heappush(queue, (lower, serial, bounds))
            break
        lower = float(result.fun * scale)
        if root_lower is None:
            root_lower = lower
            root_certificate = from_duals(graph, edge_ids, cutoff, inequalities, equalities, result, scale)
            integer_lower_bound(graph, allowed, root_certificate)
        if lower >= upper - tolerance:
            continue
        solution = result.x
        fractional = [position for position, value in enumerate(solution) if 1e-7 < value < 1 - 1e-7]
        rounded = dict(incumbent)
        for node_id, positions in node_edges.items():
            if positions:
                rounded[node_id] = edge_ids[max(positions, key=lambda position: (solution[position], -objective[position]))]
        rounded = coordinate_search(graph, allowed, rounded, sweeps=2)
        rounded_cost = graph.cost(rounded)
        if rounded_cost < upper:
            incumbent, upper = rounded, rounded_cost
        if not fractional:
            continue
        position = max(fractional, key=lambda index: (min(solution[index], 1 - solution[index]), objective[index]))
        for value in (0, 1):
            child_bounds = bounds.copy()
            child_bounds[position] = (value, value)
            heapq.heappush(queue, (lower, serial, child_bounds))
            serial += 1
    certified = not queue and not statuses
    bound = min([entry[0] for entry in queue] + [upper])
    return incumbent, {'method': 'global AND/OR LP branch-and-bound', 'lp_root_lower_flops': root_lower,
                       'joint_lower_flops': bound, 'joint_incumbent_flops': upper,
                       'numerically_closed': certified, 'lp_nodes': explored,
                       'seconds': time.monotonic() - started, 'remaining_nodes': len(queue),
                       'objective_tolerance_flops': tolerance, 'statuses': statuses,
                       'root_certificate': root_certificate,
                       'scope': 'all enumerated binary trees and global subnetwork reuse; local allocation caps, relaxed scheduling; floating-point branch-and-bound and independently checked integer root LP certificate; not a universal impossibility proof'}
