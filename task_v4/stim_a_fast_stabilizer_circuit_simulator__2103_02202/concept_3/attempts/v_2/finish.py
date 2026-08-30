import random
import json
import sys
from pathlib import Path

import synthesis as syn

def distance(first, second):
    return abs(first // 6 - second // 6) + abs(first % 6 - second % 6)

def plan_pair(source, pivot, active):
    rows = [row[:] for row in source]
    gates = []
    def emit(gate, *targets):
        operation = (gate, *targets)
        gates.append(operation)
        syn.operate(rows, operation)
    for qubit in active:
        if rows[pivot][1] >> qubit & 1:
            emit('S' if rows[pivot][0] >> qubit & 1 else 'H', qubit)
    if not rows[pivot][0] >> pivot & 1:
        endpoint = min((qubit for qubit in active if rows[pivot][0] >> qubit & 1), key=lambda qubit: distance(pivot, qubit))
        emit('CX', endpoint, pivot)
        emit('CX', pivot, endpoint)
    for qubit in active - {pivot}:
        if rows[pivot][0] >> qubit & 1:
            emit('CX', pivot, qubit)
    if rows[pivot + 36][0] >> pivot & 1:
        for gate in 'HSH':
            emit(gate, pivot)
    for qubit in active - {pivot}:
        if rows[pivot + 36][0] >> qubit & 1:
            if rows[pivot + 36][1] >> qubit & 1:
                emit('S', qubit)
            emit('H', qubit)
        if rows[pivot + 36][1] >> qubit & 1:
            emit('CX', qubit, pivot)
    assert rows[pivot][:2] == [1 << pivot, 0]
    assert rows[pivot + 36][:2] == [0, 1 << pivot]
    return rows, gates

def route(gates, seed):
    rng = random.Random(seed)
    depths = [0] * 36
    result = []
    for operation in gates:
        if operation[0] != 'CX':
            result.append(operation)
            continue
        first, second = operation[1:]
        candidates = []
        for trial in range(12):
            path = [first]
            while path[-1] != second:
                previous = path[-1]
                choices = [other for other in syn.NEIGHBORS[previous] if distance(other, second) < distance(previous, second)]
                path.append(rng.choice(choices))
            length = len(path) - 1
            indices = [0] if length == 1 else list(range(length)) + list(range(length - 2, -1, -1)) + list(range(1, length)) + list(range(length - 2, 0, -1))
            bridge = [('CX', path[index], path[index + 1]) for index in indices]
            if trial % 2:
                bridge.reverse()
            updated = depths[:]
            for gate, control, target in bridge:
                updated[control] = updated[target] = 1 + max(updated[control], updated[target])
            candidates.append((max(updated), sum(updated), rng.random(), updated, bridge))
        _, _, _, depths, bridge = min(candidates)
        result.extend(bridge)
    return result

def synthesize(rows, seed):
    rng = random.Random(seed)
    active = set(range(36))
    gates = []
    while active:
        choices = []
        for pivot in active:
            updated, operations = plan_pair(rows, pivot, active)
            cost = sum((1 if distance(*operation[1:]) == 1 else 4 * distance(*operation[1:]) - 4) for operation in operations if operation[0] == 'CX')
            choices.append((cost, rng.random(), pivot, updated, operations))
        _, _, pivot, rows, operations = min(choices)
        gates.extend(operations)
        active.remove(pivot)
    return route(syn.reverse(gates), seed)

def main():
    Path('candidates').mkdir(exist_ok=True)
    patterns = sys.argv[1:] or ['depth_run_*.txt', 'blocks_run_*.txt']
    for pattern in patterns:
        for path in sorted(Path('.').glob(pattern)):
            left, right = syn.load_moves(path)
            rows = syn.residual(left, right)
            weight = sum((row[0] | row[1]).bit_count() for row in rows)
            weight += sum(((rows[qubit][0] ^ rows[qubit + 36][0]) | (rows[qubit][1] ^ rows[qubit + 36][1])).bit_count() for qubit in range(36))
            if weight > 350:
                print('skip', path, weight, flush=True)
                continue
            prefix = [operation for group in right for operation in group]
            suffix = [operation for group in left[::-1] for operation in group]
            for seed in range(2):
                middle = synthesize([row[:] for row in rows], seed)
                gates = prefix + middle + suffix
                result = syn.save(gates, f'finish:{path}:{seed}')
                record = Path('candidates') / (path.stem + '_metrics.json')
                previous = json.loads(record.read_text()) if record.exists() else {'score': -1}
                if result['score'] >= 18 and result['score'] > previous['score']:
                    record.write_text(json.dumps(result) + '\n')
                    record.with_name(path.stem + '.json').write_text(json.dumps(syn.simplify(gates)) + '\n')

if __name__ == '__main__':
    main()
