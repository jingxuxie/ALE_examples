import json
import random
import time
from pathlib import Path

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/stim_a_fast_stabilizer_circuit_simulator__2103_02202/concept_2')
model = json.loads((ROOT / 'participant/input/model.json').read_text())
columns = [int(value, 16) for value in model['columns']]
rows = [sum(((column >> row) & 1) << index for index, column in enumerate(columns)) for row in range(192)]
pair_map = {}
quadruples = []
for first in range(512):
    for second in range(first):
        value = columns[first] ^ columns[second]
        if value in pair_map:
            quadruples.append((first, second, *pair_map[value]))
        pair_map[value] = (first, second)
print('zero quadruples', quadruples[:30], 'count', len(quadruples), flush=True)

def basis_reduce(values):
    basis = {}
    for value in values:
        while value:
            pivot = value.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = value
                break
            value ^= basis[pivot]
    return basis

basis = basis_reduce(rows)
for shift in (1, 2, 4, 8, 16, 32, 64, 128, 256):
    mask = (1 << 512) - 1
    shifted = [((row << shift) | (row >> (512-shift))) & mask for row in rows]
    print('rotation union rank', shift, len(basis_reduce(rows + shifted)), flush=True)

randomizer = random.Random(120451)
minimum = 512
started = time.monotonic()
for iteration in range(300):
    reduced = rows.copy()
    order = list(range(512))
    randomizer.shuffle(order)
    pivot = 0
    for column in order:
        position = next((index for index in range(pivot, 192) if (reduced[index] >> column) & 1), None)
        if position is None:
            continue
        reduced[pivot], reduced[position] = reduced[position], reduced[pivot]
        value = reduced[pivot]
        for index in range(192):
            if index != pivot and (reduced[index] >> column) & 1:
                reduced[index] ^= value
        pivot += 1
        if pivot == 192:
            break
    for value in reduced:
        if value.bit_count() < minimum:
            minimum = value.bit_count()
            print('dual best', minimum, 'iteration', iteration, 'support', [index for index in range(512) if (value >> index) & 1], flush=True)
    if iteration % 100 == 0:
        print('dual progress', iteration, time.monotonic()-started, flush=True)
print('done', time.monotonic()-started)
