import collections
import gzip
import itertools
import json
import os
from pathlib import Path


with gzip.open(Path(os.environ['P']) / 'input/scale_1.json.gz', 'rt') as stream:
    case = json.load(stream)
vectors = []
for slot, (cell, triple) in enumerate(zip(case['slot_cells'], case['columns'])):
    for axis, value in enumerate(triple):
        vectors.append((int(value, 16), cell, axis))
pairs = collections.defaultdict(list)
for first, second in itertools.combinations(range(len(vectors)), 2):
    first_vector, first_cell, first_axis = vectors[first]
    second_vector, second_cell, second_axis = vectors[second]
    if first_cell == second_cell and first_axis != second_axis:
        continue
    value = first_vector ^ second_vector
    assignment = tuple(sorted(set(((first_cell, first_axis), (second_cell, second_axis)))))
    pairs[value >> 4].append((value & 15, assignment))
clauses = set()
for key, entries in pairs.items():
    entries = sorted(set(entries))
    if key == 0:
        clauses.update(assignment for action, assignment in entries if action)
    for (action, first), (other, second) in itertools.combinations(entries, 2):
        if action == other:
            continue
        assignment = tuple(sorted(set(first + second)))
        if len({cell for cell, axis in assignment}) == len(assignment):
            clauses.add(assignment)
for vector, cell, axis in vectors:
    for action, assignment in pairs.get(vector >> 4, []):
        if action == (vector & 15):
            continue
        assignment = tuple(sorted(set(assignment + ((cell, axis),))))
        if len({cell for cell, axis in assignment}) == len(assignment):
            clauses.add(assignment)
print('raw clauses', len(clauses), collections.Counter(map(len, clauses)), flush=True)
minimal = []
for clause in sorted(clauses, key=len):
    if not any(subset in clauses for size in range(1, len(clause)) for subset in itertools.combinations(clause, size)):
        minimal.append(clause)
print('minimal clauses', len(minimal), collections.Counter(map(len, minimal)), flush=True)
Path('clauses.json').write_text(json.dumps(minimal))
with open('clauses.txt', 'w') as stream:
    print(len(minimal), file=stream)
    for clause in minimal:
        print(len(clause), *(3 * cell + axis for cell, axis in clause), file=stream)
