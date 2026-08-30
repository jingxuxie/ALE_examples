import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/stim_a_fast_stabilizer_circuit_simulator__2103_02202/concept_2')
OUT = ROOT / 'attempts/v_6'
model = json.loads((ROOT / 'participant/input/model.json').read_text())
columns = [int(value, 16) for value in model['columns']]
observable = model['observable']

def rank(values):
    basis = {}
    for value in values:
        while value:
            pivot = value.bit_length()
            if pivot not in basis:
                basis[pivot] = value
                break
            value ^= basis[pivot]
    return len(basis)

with (OUT / 'columns.txt').open('w') as stream:
    for column, logical in zip(columns, observable):
        words = [(column >> shift) & ((1 << 64) - 1) for shift in (0, 64, 128)]
        stream.write(' '.join(f'{word:016x}' for word in words) + f' {logical}\n')
print('metadata', {key: value for key, value in model.items() if key not in ('columns', 'observable')})
print('column weights', sorted(Counter(value.bit_count() for value in columns).items()))
print('observable', sum(observable))
for size in (32, 64, 96, 128, 160, 192, 256):
    print('block ranks', size, [rank(columns[start:start+size]) for start in range(0, 512, size)])
pairs = sorted(((columns[first] ^ columns[second]).bit_count(), first, second) for first in range(512) for second in range(first))
print('light pairs', pairs[:20])
print('heavy pairs', pairs[-10:])
for weight in (20, 32, 36, 38, 40):
    expected = math.log2(math.comb(512, weight)) - 192
    stern = math.log2(math.comb(176, weight-4)) + 2*math.log2(math.comb(168, 2)) - math.log2(math.comb(512, weight))
    print('weight', weight, 'log2_expected', expected, 'stern_log2_probability', stern)
rows = [sum(((column >> row) & 1) << index for index, column in enumerate(columns)) for row in range(192)]
print('row weights', sorted(Counter(value.bit_count() for value in rows).items()))
print('row xor minimum', min((rows[first] ^ rows[second]).bit_count() for first in range(192) for second in range(first)))
