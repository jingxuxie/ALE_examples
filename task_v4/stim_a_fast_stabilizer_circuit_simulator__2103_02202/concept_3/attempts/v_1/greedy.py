import json
import random
import time
from pathlib import Path

ROOT = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/stim_a_fast_stabilizer_circuit_simulator__2103_02202/concept_3/participant')
OUT = Path(__file__).resolve().parent
WIDTH = 36
MASK = (1 << WIDTH) - 1
EDGES = json.loads((ROOT / 'input/constraints.json').read_text())['edges']
AXES = [(1, 0), (0, 1), (1, 1)]


def initial():
    target = json.loads((ROOT / 'input/target.json').read_text())
    rows = []
    for text in target['x_outputs'] + target['z_outputs']:
        rows.append([sum(1 << qubit for qubit, char in enumerate(text[1:]) if char in 'XY'),
                     sum(1 << qubit for qubit, char in enumerate(text[1:]) if char in 'ZY')])
    return rows


def transpose(rows):
    return [[sum(((rows[row][component] >> qubit) & 1) << row for row in range(72)) for component in range(2)] for qubit in range(36)]


def from_columns(columns):
    return [[sum(((columns[qubit][component] >> row) & 1) << qubit for qubit in range(36)) for component in range(2)] for row in range(72)]


def weight(pair):
    first, second = pair
    return (first | second).bit_count() + (((first & MASK) ^ (first >> 36)) | ((second & MASK) ^ (second >> 36))).bit_count()


def entangle(first, second, axis_first, axis_second):
    xfirst, zfirst = first
    xsecond, zsecond = second
    pfirst, qfirst = AXES[axis_first]
    psecond, qsecond = AXES[axis_second]
    anti_first = (zfirst if pfirst else 0) ^ (xfirst if qfirst else 0)
    anti_second = (zsecond if psecond else 0) ^ (xsecond if qsecond else 0)
    return ((xfirst ^ (anti_second if pfirst else 0), zfirst ^ (anti_second if qfirst else 0)),
            (xsecond ^ (anti_first if psecond else 0), zsecond ^ (anti_first if qsecond else 0)))


def run(seed):
    random.seed(seed)
    rows = initial()
    columns = transpose(rows)
    cost = sum(map(weight, columns))
    history = []
    for step in range(500):
        inverse_columns = [[rows[qubit + 36][1] | (rows[qubit + 36][0] << 36), rows[qubit][1] | (rows[qubit][0] << 36)] for qubit in range(36)]
        best_delta = 0
        choices = []
        for side, collection in enumerate((columns, inverse_columns)):
            weights = list(map(weight, collection))
            for first, second in EDGES:
                old = weights[first] + weights[second]
                for axis_first in range(3):
                    for axis_second in range(3):
                        updated = entangle(collection[first], collection[second], axis_first, axis_second)
                        delta = sum(map(weight, updated)) - old
                        if delta < best_delta:
                            best_delta = delta
                            choices = []
                        if delta == best_delta:
                            choices.append((side, first, second, axis_first, axis_second, updated))
        if best_delta >= 0:
            print('stop', seed, step, 'cost', cost, 'zero_moves', len(choices), flush=True)
            break
        side, first, second, axis_first, axis_second, updated = random.choice(choices)
        history.append([side, first, second, axis_first, axis_second])
        cost += best_delta
        if side == 0:
            columns[first], columns[second] = updated
            rows = from_columns(columns)
        else:
            for qubit, pair in zip((first, second), updated):
                rows[qubit + 36] = [pair[0] >> 36, pair[0] & MASK]
                rows[qubit] = [pair[1] >> 36, pair[1] & MASK]
            columns = transpose(rows)
        if step % 20 == 0:
            print('progress', seed, step, cost, flush=True)
        if cost == 108:
            print('solved', seed, len(history), flush=True)
            break
    (OUT / f'greedy_{seed}.json').write_text(json.dumps({'cost': cost, 'history': history, 'rows': rows}))


if __name__ == '__main__':
    started = time.time()
    for seed in range(3):
        run(seed)
    print('seconds', time.time() - started)
