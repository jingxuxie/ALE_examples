import collections
import json
import math
import random
from pathlib import Path

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/stim_a_fast_stabilizer_circuit_simulator__2103_02202/concept_2/participant')
MODEL = json.loads((ROOT / 'input/model.json').read_text())
COLUMNS = [int(value, 16) for value in MODEL['columns']]
MASK = (1 << 32) - 1


def untemper(value):
    value ^= value >> 18
    value ^= (value << 15) & 0xefc60000
    intermediate = value
    for iteration in range(5):
        value = intermediate ^ ((value << 7) & 0x9d2c5680)
    intermediate = value
    for iteration in range(3):
        value = intermediate ^ (value >> 11)
    return value & MASK


def recurrence(values):
    matches = []
    differences = []
    for index in range(len(values) - 624):
        if any(values[position] is None for position in (index, index + 1, index + 397, index + 624)):
            continue
        joined = (values[index] & 0x80000000) | (values[index + 1] & 0x7fffffff)
        predicted = values[index + 397] ^ (joined >> 1) ^ (0x9908b0df if joined & 1 else 0)
        difference = predicted ^ values[index + 624]
        if not difference:
            matches.append(index)
        else:
            differences.append(index)
    return matches, differences


def main():
    print('metadata', {key: value for key, value in MODEL.items() if key not in ['columns', 'observable']})
    for reverse in [False, True]:
        for gap in range(5):
            raw = []
            for column in COLUMNS:
                words = [(column >> shift) & MASK for shift in range(0, 192, 32)]
                if reverse:
                    words.reverse()
                raw.extend(untemper(word) for word in words)
                raw.extend([None] * gap)
            matches, differences = recurrence(raw)
            print('MT', reverse, gap, 'match', len(matches), 'mismatch', len(differences), 'first', matches[:20])
            if len(matches) > 50:
                Path('mt_stream.json').write_text(json.dumps(raw))
                print('mismatch positions', differences[:120])
    for column in COLUMNS:
        words = [(column >> shift) & ((1 << 64) - 1) for shift in (0, 64, 128)]
        with Path('columns.txt').open('a') as stream:
            stream.write(' '.join(f'{word:016x}' for word in words) + ' ' + str(MODEL['observable'][COLUMNS.index(column)]) + '\n')
    for weight in [20, 24, 28, 32, 36]:
        total = math.log2(math.comb(512, weight))
        print('Stern probability log2', weight, math.log2(math.comb(176, weight - 4)) + 2 * math.log2(math.comb(168, 2)) - total)
    print('column weights', collections.Counter(column.bit_count() for column in COLUMNS))


if __name__ == '__main__':
    main()
