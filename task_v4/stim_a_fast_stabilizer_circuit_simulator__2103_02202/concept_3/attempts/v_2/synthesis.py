import collections
import json
import math
import random
import sys
from pathlib import Path

SOURCE = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/stim_a_fast_stabilizer_circuit_simulator__2103_02202/concept_3/participant')
sys.dont_write_bytecode = True
sys.path.insert(0, str(SOURCE / 'input'))
import checker

WIDTH = 36
TARGET = json.loads((SOURCE / 'input/target.json').read_text())
CONSTRAINTS = json.loads((SOURCE / 'input/constraints.json').read_text())
EXPECTED = [checker.parse_pauli(text, WIDTH) for text in TARGET['x_outputs'] + TARGET['z_outputs']]
NEIGHBORS = [[] for _ in range(WIDTH)]
for first, second in CONSTRAINTS['edges']:
    NEIGHBORS[first].append(second)
    NEIGHBORS[second].append(first)

def operate(rows, operation):
    checker.apply_gate(rows, operation[0], operation[1:])

def reverse(gates):
    return [operation for gate in gates[::-1] for operation in ([gate] * (3 if gate[0] == 'S' else 1))]

def ppr(first, second, axis1, axis2):
    before = []
    for qubit, axis in ((first, axis1), (second, axis2)):
        if axis == 1:
            before.append(('H', qubit))
        elif axis == 3:
            before.extend([('S', qubit)] * 3 + [('H', qubit)])
    middle = [('H', second), ('CX', first, second), ('H', second), ('S', first), ('S', second)]
    return before + middle + reverse(before)

def load_moves(path):
    if path is None:
        return [], []
    left, right = [], []
    for line in Path(path).read_text().splitlines():
        fields = line.split()
        if fields[0] in ('H', 'S'):
            gate, side, qubit = fields
            (right if int(side) else left).append([(gate, int(qubit))])
        else:
            if fields[0] == 'R':
                fields = fields[1:]
            side, first, second, axis1, axis2 = map(int, fields)
            (right if side else left).append(ppr(first, second, axis1, axis2))
    return left, right

def tableau(gates):
    rows = [[1 << qubit, 0, 0] for qubit in range(WIDTH)] + [[0, 1 << qubit, 0] for qubit in range(WIDTH)]
    for operation in gates:
        operate(rows, operation)
    return rows

def residual(left, right):
    right_gates = [operation for group in right[::-1] for operation in group]
    rows = tableau(right_gates)
    def product(first, second):
        return [first[0] ^ second[0], first[1] ^ second[1], 0]
    result = []
    for xmask, zmask, sign in rows:
        row = [0, 0, 0]
        for qubit in range(WIDTH):
            if xmask >> qubit & 1:
                row = product(row, EXPECTED[qubit])
            if zmask >> qubit & 1:
                row = product(row, EXPECTED[qubit + WIDTH])
        result.append(row)
    for group in left:
        for operation in group:
            operate(result, operation)
    return result

def connected(active):
    if not active:
        return True
    seen = {next(iter(active))}
    queue = list(seen)
    for qubit in queue:
        for other in NEIGHBORS[qubit]:
            if other in active and other not in seen:
                seen.add(other)
                queue.append(other)
    return len(seen) == len(active)

def tree(root, terminals, active, rng):
    network = {root}
    adjacency = {root: []}
    terminals = set(terminals)
    while not terminals <= network:
        queue = list(network)
        rng.shuffle(queue)
        parents = dict.fromkeys(queue)
        endpoint = None
        for qubit in queue:
            if qubit in terminals and qubit not in network:
                endpoint = qubit
                break
            neighbors = NEIGHBORS[qubit][:]
            rng.shuffle(neighbors)
            for other in neighbors:
                if other in active and other not in parents:
                    parents[other] = qubit
                    queue.append(other)
        while endpoint not in network:
            parent = parents[endpoint]
            adjacency.setdefault(endpoint, []).append(parent)
            adjacency.setdefault(parent, []).append(endpoint)
            network.add(endpoint)
            endpoint = parent
    parents = {root: None}
    order = [root]
    for qubit in order:
        for other in adjacency[qubit]:
            if other not in parents:
                parents[other] = qubit
                order.append(other)
    return [(qubit, parents[qubit]) for qubit in order[:0:-1]]

def eliminate_pair(source_rows, pivot, active, rng):
    rows = [row[:] for row in source_rows]
    gates = []
    def emit(gate, *targets):
        operation = (gate, *targets)
        gates.append(operation)
        operate(rows, operation)
    for qubit in active:
        xvalue = rows[pivot][0] >> qubit & 1
        zvalue = rows[pivot][1] >> qubit & 1
        if zvalue:
            emit('S' if xvalue else 'H', qubit)
    terminals = [qubit for qubit in active if rows[pivot][0] >> qubit & 1]
    for child, parent in tree(pivot, terminals, active, rng):
        if rows[pivot][0] >> child & 1:
            if not rows[pivot][0] >> parent & 1:
                emit('CX', child, parent)
            emit('CX', parent, child)
    assert rows[pivot][:2] == [1 << pivot, 0]
    if rows[pivot + WIDTH][0] >> pivot & 1:
        emit('H', pivot)
        emit('S', pivot)
        emit('H', pivot)
    for qubit in active - {pivot}:
        xvalue = rows[pivot + WIDTH][0] >> qubit & 1
        zvalue = rows[pivot + WIDTH][1] >> qubit & 1
        if xvalue:
            if zvalue:
                emit('S', qubit)
            emit('H', qubit)
    terminals = [qubit for qubit in active if rows[pivot + WIDTH][1] >> qubit & 1]
    for child, parent in tree(pivot, terminals, active, rng):
        if rows[pivot + WIDTH][1] >> child & 1:
            if not rows[pivot + WIDTH][1] >> parent & 1:
                emit('CX', parent, child)
            emit('CX', child, parent)
    assert rows[pivot + WIDTH][:2] == [0, 1 << pivot]
    return rows, gates

def synthesize(rows, seed):
    rng = random.Random(seed)
    active = set(range(WIDTH))
    gates = []
    depths = [0] * WIDTH
    while active:
        candidates = []
        for pivot in active:
            if not connected(active - {pivot}):
                continue
            trial_rows, trial_gates = eliminate_pair(rows, pivot, active, rng)
            trial_depths = depths[:]
            for operation in trial_gates:
                if operation[0] == 'CX':
                    first, second = operation[1:]
                    trial_depths[first] = trial_depths[second] = 1 + max(trial_depths[first], trial_depths[second])
            count = sum(operation[0] == 'CX' for operation in trial_gates)
            value = count + (max(trial_depths) - max(depths)) * (0.5 + (seed % 4) * 0.5)
            value += rng.random() * (seed // 4 % 4)
            candidates.append((value, pivot, trial_rows, trial_gates, trial_depths))
        value, pivot, rows, trial_gates, depths = min(candidates, key=lambda item: item[0])
        gates.extend(trial_gates)
        active.remove(pivot)
    return reverse(gates)

def onequbit_words():
    queue = [((1, 2), ())]
    words = {(1, 2): ()}
    for state, word in queue:
        for gate in ('H', 'S'):
            updated = tuple((((axis & 1) << 1) | (axis >> 1)) if gate == 'H' else axis ^ ((axis & 1) << 1) for axis in state)
            if updated not in words:
                words[updated] = word + (gate,)
                queue.append((updated, words[updated]))
    return words

WORDS = onequbit_words()

def simplify(gates):
    pending = [(1, 2)] * WIDTH
    result = []
    def flush(qubit):
        result.extend((gate, qubit) for gate in WORDS[pending[qubit]])
        pending[qubit] = (1, 2)
    for operation in gates:
        if operation[0] == 'CX':
            for qubit in operation[1:]:
                flush(qubit)
            result.append(operation)
        else:
            gate, qubit = operation
            pending[qubit] = tuple((((axis & 1) << 1) | (axis >> 1)) if gate == 'H' else axis ^ ((axis & 1) << 1) for axis in pending[qubit])
    for qubit in range(WIDTH):
        flush(qubit)
    return result

def sign_correction(gates):
    actual = tableau(gates)
    assert all(first[:2] == second[:2] for first, second in zip(actual, EXPECTED))
    xmask = zmask = 0
    for qubit in range(WIDTH):
        if actual[qubit][2] ^ EXPECTED[qubit][2]:
            xmask ^= actual[qubit + WIDTH][0]
            zmask ^= actual[qubit + WIDTH][1]
        if actual[qubit + WIDTH][2] ^ EXPECTED[qubit + WIDTH][2]:
            xmask ^= actual[qubit][0]
            zmask ^= actual[qubit][1]
    for qubit in range(WIDTH):
        if xmask >> qubit & 1:
            gates.extend([('H', qubit), ('S', qubit), ('S', qubit), ('H', qubit)])
        if zmask >> qubit & 1:
            gates.extend([('S', qubit), ('S', qubit)])
    return gates

def schedule(gates):
    depths = [0] * WIDTH
    pending = [[] for _ in range(WIDTH)]
    singles = collections.defaultdict(lambda: [[] for _ in range(WIDTH)])
    entanglers = collections.defaultdict(list)
    for operation in gates:
        if operation[0] != 'CX':
            pending[operation[1]].append(operation)
            continue
        first, second = operation[1:]
        depth = 1 + max(depths[first], depths[second])
        for qubit in (first, second):
            singles[depth][qubit].extend(pending[qubit])
            pending[qubit] = []
            depths[qubit] = depth
        entanglers[depth].append(operation)
    for qubit in range(WIDTH):
        singles[max(depths) + 1][qubit].extend(pending[qubit])
    layers = []
    for depth in range(1, max(depths) + 2):
        for index in range(max(map(len, singles[depth]))):
            layers.append([{'gate': operations[index][0], 'targets': list(operations[index][1:])} for operations in singles[depth] if len(operations) > index])
        if entanglers[depth]:
            layers.append([{'gate': operation[0], 'targets': list(operation[1:])} for operation in entanglers[depth]])
    return {'schema_version': 1, 'num_qubits': WIDTH, 'layers': layers}

def save(gates, label):
    gates = sign_correction(simplify(gates))
    artifact = schedule(gates)
    result = checker.check(artifact, {'target': TARGET, 'constraints': CONSTRAINTS})
    print(label, json.dumps(result), flush=True)
    assert result['semantic_valid']
    best = json.loads(Path('best_result.json').read_text()) if Path('best_result.json').exists() else {'score': -1}
    if result['score'] > best['score']:
        Path('circuit.json').write_text(json.dumps(artifact, separators=(',', ':')) + '\n')
        Path('best_result.json').write_text(json.dumps(dict(result, label=label), indent=2) + '\n')
        Path('best_gates.json').write_text(json.dumps(gates) + '\n')
    return result

def main():
    path = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != '-' else None
    seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    left, right = load_moves(path)
    rows = residual(left, right)
    prefix = [operation for group in right for operation in group]
    suffix = [operation for group in left[::-1] for operation in group]
    for seed in range(seeds):
        middle = synthesize([row[:] for row in rows], seed)
        save(prefix + middle + suffix, f'{path}:{seed}')

if __name__ == '__main__':
    main()
