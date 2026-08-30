import json
import os
import sys
from pathlib import Path

participant = Path(os.environ['P'])
sys.path.insert(0, str(participant / 'workspace'))
from design_common import load_case, read_design, selected_columns

def rank(vectors):
    pivots = {}
    for vector in vectors:
        while vector:
            pivot = vector.bit_length()
            if pivot in pivots:
                vector ^= pivots[pivot]
            else:
                pivots[pivot] = vector
                break
    return len(pivots)

baseline = read_design(participant / 'baseline/design.json')
design = read_design('design.json')
results = []
for scale in range(1, 4):
    case = load_case(participant / f'input/scale_{scale}.json.gz')
    coordinates = case['data_coordinates']
    width, height = case['coordinate_period']
    indices = {tuple(coordinate): index for index, coordinate in enumerate(coordinates)}
    qubits = len(coordinates)
    reference = selected_columns(case, baseline)
    candidate = selected_columns(case, design)
    reflection = [indices[((width - horizontal) % width, vertical)]
                  for horizontal, vertical in coordinates]
    reflected = [candidate[time * qubits + reflection[qubit]]
                 for time in range(6) for qubit in range(qubits)]
    offset = max(vector.bit_length() for vector in reference + reflected)
    for shifted in [False, True]:
        first = [vector >> (4 if shifted else 0) for vector in reference]
        second = [vector >> (4 if shifted else 0) for vector in reflected]
        combined = rank(left | (right << offset) for left, right in zip(first, second))
        assert rank(first) == rank(second) == combined
        results.append({'scale': scale, 'matrix': 'H' if shifted else 'HL',
                        'individual_and_combined_rank': combined})
Path('symmetry_verification.json').write_text(json.dumps(results, indent=2) + '\n')
print('Reflection equivalence verified for H and HL on all three scales.')
