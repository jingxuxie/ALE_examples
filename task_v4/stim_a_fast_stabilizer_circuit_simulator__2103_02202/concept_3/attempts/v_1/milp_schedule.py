import itertools
import json
import sys

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

import greedy
import synthesize as syn


def main():
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    data = json.loads((greedy.OUT / 'best_generalized.json').read_text())
    gates, frames = data['gates'], data['frames']
    groups = [[] for _ in range(36)]
    previous_groups = [[] for _ in range(36)]
    current_axes = [None] * 36
    precedences = set()
    conflicts = set()
    for index, (first, second, axis_first, axis_second) in enumerate(gates):
        for qubit, axis in ((first, axis_first), (second, axis_second)):
            if axis != current_axes[qubit]:
                previous_groups[qubit] = groups[qubit]
                groups[qubit] = []
                current_axes[qubit] = axis
            precedences.update((previous, index) for previous in previous_groups[qubit])
            conflicts.update((previous, index) for previous in groups[qubit])
            groups[qubit].append(index)
    upper = min(len(syn.schedule_generalized(gates, seed)) for seed in range(20))
    gate_count = len(gates)
    variable_count = gate_count + 1 + len(conflicts)
    objective = np.zeros(variable_count)
    objective[gate_count] = 1
    lower_bounds = np.zeros(variable_count)
    upper_bounds = np.ones(variable_count)
    upper_bounds[:gate_count] = upper - 1
    upper_bounds[gate_count] = upper
    lower_bounds[gate_count] = 1
    row_indices, column_indices, values = [], [], []
    row_lower, row_upper = [], []

    def constraint(terms, lower, high):
        row = len(row_lower)
        for column, value in terms:
            row_indices.append(row)
            column_indices.append(column)
            values.append(value)
        row_lower.append(lower)
        row_upper.append(high)

    for index in range(gate_count):
        constraint([(index, 1), (gate_count, -1)], -np.inf, -1)
    for first, second in precedences:
        constraint([(second, 1), (first, -1)], 1, np.inf)
    for offset, (first, second) in enumerate(sorted(conflicts)):
        binary = gate_count + 1 + offset
        constraint([(second, 1), (first, -1), (binary, upper)], 1, np.inf)
        constraint([(first, 1), (second, -1), (binary, -upper)], 1 - upper, np.inf)
    matrix = coo_matrix((values, (row_indices, column_indices)), shape=(len(row_lower), variable_count)).tocsc()
    print('problem', gate_count, 'conflicts', len(conflicts), 'precedences', len(precedences), 'upper', upper, flush=True)
    result = milp(objective, integrality=np.ones(variable_count), bounds=Bounds(lower_bounds, upper_bounds),
                  constraints=LinearConstraint(matrix, row_lower, row_upper),
                  options={'time_limit': seconds, 'mip_rel_gap': 0.0})
    print('solve', result.message, 'objective', result.fun, 'bound', getattr(result, 'mip_dual_bound', None), flush=True)
    if result.x is None:
        return
    times = np.rint(result.x[:gate_count]).astype(int)
    layers = []
    for level in range(int(times.max()) + 1):
        layer = [gate for index, gate in enumerate(gates) if times[index] == level]
        if layer:
            used = [qubit for gate in layer for qubit in gate[:2]]
            assert len(used) == len(set(used))
            layers.append(layer)
    native = syn.correct_signs(syn.realize(layers, frames))
    artifact = syn.schedule_native(native)
    instance = {name: json.loads((greedy.ROOT / 'input' / (name + '.json')).read_text()) for name in ('constraints', 'target')}
    checked = syn.check(artifact, instance)
    print(json.dumps(checked), flush=True)
    previous = json.loads((greedy.OUT / 'best_metrics.json').read_text())
    if checked['score'] > previous['score']:
        (greedy.OUT / 'circuit.json').write_text(json.dumps(artifact, separators=(',', ':')))
        (greedy.OUT / 'best_metrics.json').write_text(json.dumps(checked, indent=2))
        ordered = [gate for layer in layers for gate in layer]
        (greedy.OUT / 'best_generalized.json').write_text(json.dumps({'gates': ordered, 'frames': frames}))
        (greedy.OUT / 'best_layers.json').write_text(json.dumps(layers))


if __name__ == '__main__':
    main()
