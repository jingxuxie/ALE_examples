import json
import time
from pathlib import Path

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/stim_a_fast_stabilizer_circuit_simulator__2103_02202/concept_2')
model = json.loads((ROOT / 'participant/input/model.json').read_text())
columns = [int(value, 16) for value in model['columns']]

def complexity(sequence):
    current = 1
    previous = 1
    length = 0
    age = 1
    history = 0
    discrepancies = 0
    for position, value in enumerate(sequence):
        history = (history << 1) | value
        discrepancy = (current & history).bit_count() & 1
        if discrepancy:
            discrepancies += 1
            saved = current
            current ^= previous << age
            if 2 * length <= position:
                length = position + 1 - length
                previous = saved
                age = 1
            else:
                age += 1
        else:
            age += 1
    return length, discrepancies

started = time.monotonic()
for layout in range(6):
    if layout < 4:
        sequence = []
        for fault, column in enumerate(columns):
            bits = range(192) if layout % 2 == 0 else range(191, -1, -1)
            sequence.extend((column >> bit) & 1 for bit in bits)
            if layout >= 2:
                sequence.append(model['observable'][fault])
    else:
        sequence = [(columns[fault] >> row) & 1 for row in range(192) for fault in (range(512) if layout == 4 else range(511, -1, -1))]
    for side, window in (('first', sequence[:49000]), ('last', sequence[-49000:])):
        result = complexity(window)
        print(layout, side, result, 'seconds', time.monotonic()-started, flush=True)
