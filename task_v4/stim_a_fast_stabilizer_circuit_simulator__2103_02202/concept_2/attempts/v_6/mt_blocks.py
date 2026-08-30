import json
from collections import defaultdict
from pathlib import Path

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/stim_a_fast_stabilizer_circuit_simulator__2103_02202/concept_2')
model = json.loads((ROOT / 'participant/input/model.json').read_text())
columns = [int(value, 16) for value in model['columns']]

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

def twist(first, second):
    mixed = (first & 0x80000000) | (second & 0x7fffffff)
    return (mixed >> 1) ^ (0x9908b0df if mixed & 1 else 0)

def pack(values):
    result = 0
    for value in values:
        result = (result << 32) | value
    return result

for adjustment in (0, -1):
    for reverse in (False, True):
        blocks = [[untemper(((value + adjustment) >> shift) & 0xffffffff) for shift in range(0, 192, 32)] for value in columns]
        if reverse:
            blocks = [block[::-1] for block in blocks]
        for stride in range(6, 21):
            groups = defaultdict(list)
            for position in range(6):
                first_delta, first_pos = divmod(position-624, stride)
                next_delta, next_pos = divmod(position-623, stride)
                third_delta, third_pos = divmod(position-227, stride)
                if first_delta == next_delta and max(first_pos, next_pos, third_pos) < 6:
                    groups[first_delta, third_delta].append((position, first_pos, next_pos, third_pos))
            for deltas, positions in groups.items():
                if len(positions) < 2:
                    continue
                current = [pack(block[position] for position, _, _, _ in positions) for block in blocks]
                past = [pack(twist(block[first_pos], block[next_pos]) for _, first_pos, next_pos, _ in positions) for block in blocks]
                middle = {pack(block[third_pos] for _, _, _, third_pos in positions): index for index, block in enumerate(blocks)}
                matches = []
                for current_id, current_value in enumerate(current):
                    for past_id, past_value in enumerate(past):
                        middle_id = middle.get(current_value ^ past_value)
                        if middle_id is not None:
                            matches.append((current_id, past_id, middle_id))
                if matches:
                    print('MATCH', adjustment, reverse, stride, deltas, positions, len(matches), matches[:30], flush=True)
                    path = ROOT / f'attempts/v_6/mt_matches_{adjustment}_{reverse}_{stride}.json'
                    path.write_text(json.dumps({'deltas': deltas, 'matches': matches}))
        print('completed', adjustment, reverse, flush=True)
