import json
import random
from pathlib import Path

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/stim_a_fast_stabilizer_circuit_simulator__2103_02202/concept_2')
model = json.loads((ROOT / 'participant/input/model.json').read_text())
columns = [int(value, 16) for value in model['columns']]
rows = [sum(((column >> row) & 1) << index for index, column in enumerate(columns)) for row in range(192)]

def untemper(value):
    result = value ^ (value >> 18)
    result ^= (result << 15) & 0xefc60000
    intermediate = result
    for iteration in range(5):
        result = intermediate ^ ((result << 7) & 0x9d2c5680)
    intermediate = result
    for iteration in range(3):
        result = intermediate ^ (result >> 11)
    return result

def inspect(values, width, label):
    for offset in (0, -1, 1):
        for reverse in (False, True):
            shifts = list(range(0, width, 32))
            if reverse:
                shifts.reverse()
            outputs = [((value + offset) >> shift) & 0xffffffff for value in values for shift in shifts]
            states = [untemper(value) for value in outputs]
            matches = []
            for position in range(624, len(states)):
                mixed = (states[position-624] & 0x80000000) | (states[position-623] & 0x7fffffff)
                predicted = states[position-227] ^ (mixed >> 1) ^ (0x9908b0df if mixed & 1 else 0)
                if predicted == states[position]:
                    matches.append(position)
            print(label, offset, reverse, 'matches', len(matches), 'positions', matches[:30])

inspect(columns, 192, 'columns')
inspect(rows, 512, 'rows')
print('max rows', sorted(((row.bit_count(), index) for index, row in enumerate(rows)), reverse=True)[:10])
