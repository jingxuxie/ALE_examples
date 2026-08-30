import json
import sys
import time

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

from model import Graph


def relax(graph):
    groups = [[] for node in graph.nodes]
    operations = []
    for number in graph.order:
        node = graph.nodes[number]
        for op in node.ops:
            allocation = node.size + sum(graph.nodes[child].size for child in op[:2] if graph.nodes[child].source is None)
            if allocation > graph.cap:
                continue
            groups[number].append(len(operations))
            operations.append((number, op))
    coefficients = []
    rows = []
    columns = []
    bounds = []

    def constraint(entries, bound):
        row = len(bounds)
        for column, value in entries:
            rows.append(row)
            columns.append(column)
            coefficients.append(value)
        bounds.append(bound)

    for root in graph.roots:
        constraint([(column, -1) for column in groups[root]], -1)
    for number, group in enumerate(groups):
        if group:
            constraint([(column, 1) for column in group], 1)
    for column, (number, op) in enumerate(operations):
        for child in set(op[:2]):
            if graph.nodes[child].source is None:
                constraint([(column, 1)] + [(child_column, -1) for child_column in groups[child]], 0)
    matrix = coo_matrix((coefficients, (rows, columns)), shape=(len(bounds), len(operations))).tocsr()
    costs = np.array([op[5] for number, op in operations], dtype=float)
    scale = max(costs) / 100000
    result = linprog(costs / scale, A_ub=matrix, b_ub=np.array(bounds), bounds=(0, 1), method='highs')
    if result.success:
        fractional = sum(1e-5 < value < 1 - 1e-5 for value in result.x)
        return result.fun * scale, fractional, result.x, operations
    print(result)
    return None


def main():
    participant = '/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/pq_a_tool_for_prototyping_many_body_methods_for_quantum_chemistry__2106_06850/concept_1/participant'
    for family in ('right_triples', 'left_density', 'linear_response', 'quadruples'):
        case = json.load(open(participant + '/input/' + family + '.json'))
        base = json.load(open(participant + '/input/' + family + '.baseline.json'))['flops']
        graph = Graph(case)
        result = relax(graph)
        print(family, 'lower bound', result[0], 'speedup bound', base / result[0], 'fractional', result[1], flush=True)


if __name__ == '__main__':
    main()
