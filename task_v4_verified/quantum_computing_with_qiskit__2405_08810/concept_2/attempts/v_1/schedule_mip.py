import json
import os
from pathlib import Path
import sys
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

target_index = int(sys.argv[1])
source = Path(sys.argv[2])
seconds = float(sys.argv[3]) if len(sys.argv) > 3 else 120
target = json.load(open(Path(os.environ['P']) / 'input/instances.json'))['targets'][target_index]
gates = [tuple(map(int, line.split())) for line in source.read_text().splitlines()[1:]]
durations = {(control, destination): ticks for control, destination, ticks in target['native_cx']}
ticks = [durations[gate] for gate in gates]
length = len(gates)
cap = target['max_weighted_depth']
predecessors = [set() for gate in gates]
successors = [set() for gate in gates]
for first, (control, destination) in enumerate(gates):
    for second in range(first+1, length):
        next_control, next_destination = gates[second]
        if control == next_destination or destination == next_control:
            predecessors[second].add(first)
            successors[first].add(second)
earliest = [0] * length
for position in range(length):
    earliest[position] = max((earliest[previous] + ticks[previous] for previous in predecessors[position]), default=0)
tail = [0] * length
reach = [set() for gate in gates]
for position in reversed(range(length)):
    tail[position] = max((tail[following] + ticks[following] for following in successors[position]), default=0)
    for following in successors[position]:
        reach[position].add(following)
        reach[position].update(reach[following])
lower_bound = max(earliest[position] + ticks[position] + tail[position] for position in range(length))
print('source', source, 'count', length, 'lower bound', lower_bound, 'cap', cap, flush=True)
if lower_bound > cap:
    raise SystemExit(1)
conflicts = []
for first in range(length):
    for second in range(first+1, length):
        if set(gates[first]).intersection(gates[second]) and second not in reach[first]:
            conflicts.append((first, second))
variables = length + 1 + len(conflicts)
objective = np.zeros(variables)
objective[length] = 1
integrality = np.zeros(variables)
integrality[length+1:] = 1
lower = np.zeros(variables)
upper = np.ones(variables)
lower[:length] = earliest
upper[:length] = [cap - ticks[position] - tail[position] for position in range(length)]
lower[length] = lower_bound
upper[length] = cap
row_indices, col_indices, entries, lows, highs = [], [], [], [], []

def constraint(coefficients, low, high=np.inf):
    row = len(lows)
    for column, value in coefficients.items():
        row_indices.append(row)
        col_indices.append(column)
        entries.append(value)
    lows.append(low)
    highs.append(high)

for position in range(length):
    constraint({length: 1, position: -1}, ticks[position])
    for previous in predecessors[position]:
        constraint({position: 1, previous: -1}, ticks[previous])
for offset, (first, second) in enumerate(conflicts):
    variable = length + 1 + offset
    bound_forward = upper[first] + ticks[first] - lower[second]
    bound_reverse = upper[second] + ticks[second] - lower[first]
    constraint({second: 1, first: -1, variable: -bound_forward}, ticks[first] - bound_forward)
    constraint({first: 1, second: -1, variable: bound_reverse}, ticks[second])
matrix = coo_matrix((entries, (row_indices, col_indices)), shape=(len(lows), variables)).tocsc()
print('variables', variables, 'conflicts', len(conflicts), 'constraints', len(lows), flush=True)
result = milp(objective, integrality=integrality, bounds=Bounds(lower, upper), constraints=LinearConstraint(matrix, lows, highs), options={'time_limit': seconds, 'mip_rel_gap': 0, 'disp': True})
print(result.message, flush=True)
if result.x is None:
    raise SystemExit(1)
order = sorted(range(length), key=lambda position: (round(result.x[position], 6), position))
scheduled = [gates[position] for position in order]
ready = [0] * target['n_qubits']
rows = [1 << vertex for vertex in range(target['n_qubits'])]
for control, destination in scheduled:
    rows[destination] ^= rows[control]
    ready[control] = ready[destination] = max(ready[control], ready[destination]) + durations[control, destination]
expected = [sum(value << column for column, value in enumerate(row)) for row in target['matrix']]
assert rows == expected
print('RESULT', len(scheduled), max(ready), flush=True)
Path(target['name'] + '_mip.txt').write_text(f'{len(scheduled)} {max(ready)}\n' + ''.join(f'{control} {destination}\n' for control, destination in scheduled))
