import heapq
import os
import time
import warnings

from optimize import reachable, score


def optimize_lp(graph, initial, deadline, with_bound=False):
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['OMP_NUM_THREADS'] = '1'
    os.environ['MKL_NUM_THREADS'] = '1'
    import numpy as np
    from scipy.optimize import OptimizeWarning, linprog
    from scipy.sparse import coo_matrix

    best = initial
    best_cost = score(graph, best)
    groups = [[] for node in graph.nodes]
    operations = []
    for number in graph.order:
        node = graph.nodes[number]
        for op in node.ops:
            allocation = node.size + sum(graph.nodes[child].size for child in set(op[:2])
                                         if graph.nodes[child].source is None)
            if op[5] > best_cost or allocation > graph.cap:
                continue
            groups[number].append(len(operations))
            operations.append((number, op))
    coefficients = []
    rows = []
    columns = []
    upper = []

    def constraint(entries, bound):
        row = len(upper)
        for column, value in entries:
            rows.append(row)
            columns.append(column)
            coefficients.append(value)
        upper.append(bound)

    for root in graph.roots:
        constraint([(column, -1) for column in groups[root]], -1)
    for group in groups:
        if group:
            constraint([(column, 1) for column in group], 1)
    for column, (number, op) in enumerate(operations):
        for child in set(op[:2]):
            if graph.nodes[child].source is None:
                constraint([(column, 1)] + [(child_column, -1) for child_column in groups[child]], 0)
    matrix = coo_matrix((coefficients, (rows, columns)), shape=(len(upper), len(operations))).tocsr()
    costs = np.array([op[5] for number, op in operations], dtype=float)
    scale = max(1.0, best_cost / 1000000)
    objective = costs / scale
    upper = np.asarray(upper, dtype=float)
    variable_bounds = np.tile(np.array([0.0, 1.0]), (len(operations), 1))
    queue = [(0.0, 0, variable_bounds)]
    serial = 1
    iterations = 0
    tolerance = max(1e-5, best_cost * 1e-10)
    unresolved = float('inf')
    while queue and time.monotonic() < deadline and iterations < 160:
        bound, unused, bounds = heapq.heappop(queue)
        if bound >= best_cost - tolerance:
            continue
        iterations += 1
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', OptimizeWarning)
            result = linprog(objective, A_ub=matrix, b_ub=upper, bounds=bounds, method='highs',
                             options={'time_limit': max(0.01, deadline - time.monotonic()), 'threads': 1})
        if not result.success:
            if result.status != 2:
                unresolved = min(unresolved, bound)
            continue
        bound = result.fun * scale
        if bound >= best_cost - tolerance:
            continue
        values = result.x
        choices = best.copy()
        for number, group in enumerate(groups):
            if group:
                column = max(group, key=lambda column: (values[column], -operations[column][1][5]))
                choices[number] = operations[column][1]
        cost = score(graph, choices)
        if cost < best_cost:
            best = choices
            best_cost = cost
        fractional = [column for column, value in enumerate(values) if 1e-6 < value < 1 - 1e-6]
        if not fractional or bound >= best_cost - tolerance:
            continue
        branch = max(fractional, key=lambda column: (min(values[column], 1 - values[column]),
                                                     costs[column]))
        for value in (1, 0):
            child_bounds = bounds.copy()
            child_bounds[branch] = value
            heapq.heappush(queue, (bound, serial, child_bounds))
            serial += 1
    lower_bound = min(best_cost, unresolved, min((entry[0] for entry in queue), default=float('inf')))
    return (best, lower_bound) if with_bound else best
