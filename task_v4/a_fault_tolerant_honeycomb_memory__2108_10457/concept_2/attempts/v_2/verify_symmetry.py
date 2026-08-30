import gzip
import json
import os
from pathlib import Path


def preserves_relations(pairs):
    basis = {}
    for source, target in pairs:
        while source:
            pivot = source.bit_length()
            if pivot not in basis:
                basis[pivot] = source, target
                break
            previous_source, previous_target = basis[pivot]
            source ^= previous_source
            target ^= previous_target
        if not source and target:
            return False
    return True


for scale in range(1, 4):
    with gzip.open(Path(os.environ['P']) / f'input/scale_{scale}.json.gz', 'rt') as stream:
        case = json.load(stream)
    coordinates = {tuple(coordinate): index for index, coordinate in enumerate(case['data_coordinates'])}
    width = case['coordinate_period'][0]
    height = case['coordinate_period'][1]
    transformations = {
        'reflection': lambda horizontal, vertical: ((width - horizontal) % width, vertical),
        'translation_4': lambda horizontal, vertical: ((horizontal + 4) % width, vertical),
        'translation_2_3': lambda horizontal, vertical: ((horizontal + 2) % width, (vertical + 3) % height),
    }
    qubits = len(coordinates)
    columns = [[int(value, 16) for value in triple] for triple in case['columns']]
    for name, transformation in transformations.items():
        permutation = [coordinates[transformation(horizontal, vertical)] for horizontal, vertical in case['data_coordinates']]
        pairs = [(columns[phase * qubits + qubit][axis], columns[phase * qubits + permutation[qubit]][axis]) for phase in range(6) for qubit in range(qubits) for axis in range(3)]
        joint = preserves_relations(pairs)
        syndrome = preserves_relations([(source >> 4, target >> 4) for source, target in pairs])
        print(scale, name, 'joint', joint, 'syndrome', syndrome, flush=True)
        assert joint and syndrome
