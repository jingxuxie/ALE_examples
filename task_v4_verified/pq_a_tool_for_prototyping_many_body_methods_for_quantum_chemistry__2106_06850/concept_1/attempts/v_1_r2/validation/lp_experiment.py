import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import json
import time

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

from benchmark import PARTICIPANT
from solve import Graph, Tree, simulate


def relaxation(graph):
    baseline = graph.plan_trees(0)
    bound = sum(tree.cost for tree in baseline.values())
    internal = [number for number in graph.order if graph.nodes[number].source is None]
    node_variables = dict(zip(internal, range(len(internal))))
    costs = [0.0] * len(internal)
    options = {}
    equal_rows = []
    equal_columns = []
    equal_data = []
    rows = []
    columns = []
    data = []
    row_number = 0
    for number in internal:
        equal_rows.append(node_variables[number])
        equal_columns.append(node_variables[number])
        equal_data.append(1)
        for option in graph.nodes[number].options:
            if option[2] > bound:
                continue
            variable = len(costs)
            options[variable] = (number, option)
            costs.append(option[2])
            equal_rows.append(node_variables[number])
            equal_columns.append(variable)
            equal_data.append(-1)
            for child in set(option[:2]):
                if child in node_variables:
                    rows.extend((row_number, row_number))
                    columns.extend((variable, node_variables[child]))
                    data.extend((1, -1))
                    row_number += 1
    equality = coo_matrix((equal_data, (equal_rows, equal_columns)), shape=(len(internal), len(costs))).tocsc()
    inequality = coo_matrix((data, (rows, columns)), shape=(row_number, len(costs))).tocsc()
    bounds = [(0, 1)] * len(costs)
    for root in graph.roots:
        bounds[node_variables[root]] = (1, 1)
    scale = max(costs) / 100000
    result = linprog(np.array(costs) / scale, inequality, np.zeros(row_number), equality,
                     np.zeros(len(internal)), bounds=bounds, method='highs',
                     options={'time_limit': 5, 'dual_feasibility_tolerance': 1e-9})
    if not result.success:
        return result, None, None
    choices = {}
    for variable, (number, option) in options.items():
        previous = choices.get(number)
        value = result.x[variable]
        if previous is None or value > previous[0]:
            choices[number] = (value, option)
    selected = {}
    for number in graph.order:
        node = graph.nodes[number]
        if node.source is not None:
            selected[number] = Tree(number)
            continue
        if number not in choices:
            continue
        option = choices[number][1]
        if any(child not in selected for child in option[:2]):
            continue
        left, right = (selected[child] for child in option[:2])
        left_size, right_size = (graph.nodes[child].size for child in option[:2])
        allocation = left_size + right_size + node.size
        peak_left = max(left.peak, left_size + right.peak, allocation)
        peak_right = max(right.peak, right_size + left.peak, allocation)
        cost = left.cost + right.cost + option[2]
        if left.node == right.node:
            peak_left = peak_right = max(left.peak, left_size + node.size)
            cost = left.cost + option[2]
        selected[number] = Tree(number, option, left, right, peak_right < peak_left,
                                cost, min(peak_left, peak_right), cost)
    roots = {root: selected[root] if root in selected and selected[root].peak <= graph.cap else baseline[root]
             for root in graph.roots}
    best = min((simulate(graph, roots, policy, eviction) for policy in range(4) for eviction in (0.65, 1)),
               key=lambda item: item[:2])
    return result, result.fun * scale, best


if __name__ == '__main__':
    for path in sorted((PARTICIPANT / 'input').glob('*.json')):
        if 'baseline' in path.name:
            continue
        graph = Graph(json.loads(path.read_text()))
        started = time.monotonic()
        result, bound, best = relaxation(graph)
        fractional = np.sum(np.abs(result.x - np.round(result.x)) > 1e-5) if result.x is not None else None
        print(path.stem, bound, best[:2] if best else result.message,
              'fractional', fractional, 'seconds', time.monotonic() - started, flush=True)
