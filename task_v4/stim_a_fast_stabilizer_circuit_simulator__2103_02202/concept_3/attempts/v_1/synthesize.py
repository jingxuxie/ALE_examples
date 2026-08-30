import collections
import json
import random
import sys
from pathlib import Path

from greedy import AXES, EDGES, OUT, ROOT, initial

sys.path.insert(0, str(ROOT / 'input'))
from checker import apply_gate, check, parse_pauli, tableau

NEIGHBORS = [[] for _ in range(36)]
for first, second in EDGES:
    NEIGHBORS[first].append(second)
    NEIGHBORS[second].append(first)


def inverse_gates(gates):
    return [(name, targets) for name, targets in reversed(gates) for _ in range(3 if name == 'S' else 1)]


def generalized(first, second, axis_first, axis_second):
    before = []
    for qubit, axis in ((first, axis_first), (second, axis_second)):
        if axis == 0:
            before.append(('H', (qubit,)))
        elif axis == 2:
            before.extend([('S', (qubit,))] * 3 + [('H', (qubit,))])
    return before + [('H', (second,)), ('CX', (first, second)), ('H', (second,))] + inverse_gates(before)


def tree(root, remaining, terminals, randomizer):
    parents = {root: None}
    queue = [root]
    for node in queue:
        neighbors = list(NEIGHBORS[node])
        randomizer.shuffle(neighbors)
        for neighbor in neighbors:
            if neighbor in remaining and neighbor not in parents:
                parents[neighbor] = node
                queue.append(neighbor)
    used = {root}
    for terminal in terminals:
        while terminal not in used:
            used.add(terminal)
            terminal = parents[terminal]
    return [(node, parents[node]) for node in reversed(queue) if node in used and node != root]


def connected(vertices):
    if not vertices:
        return True
    reached = {next(iter(vertices))}
    queue = list(reached)
    for node in queue:
        for neighbor in NEIGHBORS[node]:
            if neighbor in vertices and neighbor not in reached:
                reached.add(neighbor)
                queue.append(neighbor)
    return len(reached) == len(vertices)


def eliminate(input_rows, seed=0):
    rows = [list(row[:2]) + [0] for row in input_rows]
    remaining = set(range(36))
    gates = []
    randomizer = random.Random(seed)

    def operate(name, *targets):
        gates.append((name, targets))
        apply_gate(rows, name, targets)

    while remaining:
        choices = []
        for qubit in remaining:
            if connected(remaining - {qubit}):
                supports = [(rows[index][0] | rows[index][1]).bit_count() for index in (qubit, qubit + 36)]
                choices.append((sum(supports) + randomizer.random() * 2, qubit))
        pivot = min(choices)[1]
        for stage in range(2):
            row = rows[pivot + stage * 36]
            for qubit in remaining:
                xbit = (row[0] >> qubit) & 1
                zbit = (row[1] >> qubit) & 1
                if stage == 1 and qubit == pivot:
                    if xbit:
                        operate('H', qubit)
                        operate('S', qubit)
                        operate('H', qubit)
                elif xbit:
                    if zbit:
                        operate('S', qubit)
                    operate('H', qubit)
            terminals = [qubit for qubit in remaining if (row[1] >> qubit) & 1]
            for child, parent in tree(pivot, remaining, terminals, randomizer):
                if (row[1] >> child) & 1:
                    if not (row[1] >> parent) & 1:
                        operate('CX', parent, child)
                    operate('CX', child, parent)
            if stage == 0:
                operate('H', pivot)
        assert rows[pivot][:2] == [1 << pivot, 0]
        assert rows[pivot + 36][:2] == [0, 1 << pivot]
        remaining.remove(pivot)
    return inverse_gates(gates)


def local_tables(signed):
    identity = (1, 0, 0, 0, 1, 0)
    sequences = {identity: []}
    queue = [identity]
    transitions = {}
    for state in queue:
        for name in ('H', 'S'):
            rows = [list(state[:3]), list(state[3:])]
            apply_gate(rows, name, [0])
            if not signed:
                rows[0][2] = rows[1][2] = 0
            updated = tuple(rows[0] + rows[1])
            transitions[state, name] = updated
            if updated not in sequences:
                sequences[updated] = sequences[state] + [name]
                queue.append(updated)
    return identity, sequences, transitions


IDENTITY, SINGLE_WORDS, SINGLE_NEXT = local_tables(True)
_, FRAME_WORDS, FRAME_NEXT = local_tables(False)


def axis_image(frame, axis):
    xbit, zbit = AXES[axis]
    image = ((frame[0] if xbit else 0) ^ (frame[3] if zbit else 0),
             (frame[1] if xbit else 0) ^ (frame[4] if zbit else 0))
    return AXES.index(image)


def generalize(gates):
    frames = [IDENTITY] * 36
    result = []
    for name, targets in gates:
        if name == 'CX':
            first, second = targets
            axis_first = next(axis for axis in range(3) if axis_image(frames[first], axis) == 1)
            axis_second = next(axis for axis in range(3) if axis_image(frames[second], axis) == 0)
            result.append((first, second, axis_first, axis_second))
        else:
            qubit = targets[0]
            frames[qubit] = FRAME_NEXT[frames[qubit], name]
    return result, frames


def cancel_generalized(gates):
    output = []
    for gate in gates:
        first, second, axis_first, axis_second = gate
        axes = {first: axis_first, second: axis_second}
        canceled = False
        for index in range(len(output) - 1, -1, -1):
            old = output[index]
            if old is None:
                continue
            old_first, old_second, old_axis_first, old_axis_second = old
            old_axes = {old_first: old_axis_first, old_second: old_axis_second}
            if axes == old_axes:
                output[index] = None
                canceled = True
                break
            if any(qubit in old_axes and axes[qubit] != old_axes[qubit] for qubit in axes):
                break
        if not canceled:
            output.append(gate)
    return [gate for gate in output if gate is not None]


def schedule_generalized(gates, seed=0):
    randomizer = random.Random(seed)
    predecessors = [set() for _ in gates]
    successors = [set() for _ in gates]
    groups = [[] for _ in range(36)]
    previous_groups = [[] for _ in range(36)]
    current_axes = [None] * 36
    for index, (first, second, axis_first, axis_second) in enumerate(gates):
        for qubit, axis in ((first, axis_first), (second, axis_second)):
            if axis != current_axes[qubit]:
                previous_groups[qubit] = groups[qubit]
                groups[qubit] = []
                current_axes[qubit] = axis
            predecessors[index].update(previous_groups[qubit])
            groups[qubit].append(index)
    for index, dependencies in enumerate(predecessors):
        for predecessor in dependencies:
            successors[predecessor].add(index)
    height = [1] * len(gates)
    for index in reversed(range(len(gates))):
        height[index] += max((height[successor] for successor in successors[index]), default=0)
    ready = {index for index, dependencies in enumerate(predecessors) if not dependencies}
    layers = []
    while ready:
        occupied = set()
        chosen = []
        ranking = sorted(ready, key=lambda index: (-height[index], randomizer.random()))
        for index in ranking:
            first, second = gates[index][:2]
            if first not in occupied and second not in occupied:
                chosen.append(index)
                occupied.update((first, second))
        layers.append([gates[index] for index in chosen])
        for index in chosen:
            ready.remove(index)
            for successor in successors[index]:
                predecessors[successor].remove(index)
                if not predecessors[successor]:
                    ready.add(successor)
    assert sum(map(len, layers)) == len(gates)
    return layers


def realize(layers, final_frames):
    frames = [IDENTITY] * 36
    gates = []
    for layer in layers:
        for first, second, axis_first, axis_second in layer:
            candidates = []
            for reverse in (False, True):
                goals = (0, 1) if reverse else (1, 0)
                local_choices = []
                for qubit, axis, goal in zip((first, second), (axis_first, axis_second), goals):
                    choices = []
                    for update, word in FRAME_WORDS.items():
                        frame = frames[qubit]
                        for name in word:
                            frame = FRAME_NEXT[frame, name]
                        if axis_image(frame, axis) == goal:
                            choices.append((len(word), word, frame))
                    local_choices.append(min(choices))
                candidates.append((sum(choice[0] for choice in local_choices), reverse, local_choices))
            _, reverse, choices = min(candidates)
            for qubit, (_, word, frame) in zip((first, second), choices):
                gates.extend((name, (qubit,)) for name in word)
                frames[qubit] = frame
            gates.append(('CX', (second, first) if reverse else (first, second)))
    for qubit in range(36):
        candidates = []
        for update, word in FRAME_WORDS.items():
            frame = frames[qubit]
            for name in word:
                frame = FRAME_NEXT[frame, name]
            if frame == tuple(final_frames[qubit]):
                candidates.append((len(word), word))
        gates.extend((name, (qubit,)) for name in min(candidates)[1])
    return gates


def simplify_locals(gates):
    pending = [IDENTITY] * 36
    output = []
    for name, targets in gates:
        if name == 'CX':
            for qubit in targets:
                output.extend((local, (qubit,)) for local in SINGLE_WORDS[pending[qubit]])
                pending[qubit] = IDENTITY
            output.append((name, targets))
        else:
            qubit = targets[0]
            pending[qubit] = SINGLE_NEXT[pending[qubit], name]
    for qubit in range(36):
        output.extend((local, (qubit,)) for local in SINGLE_WORDS[pending[qubit]])
    return output


def schedule_native(gates):
    depth = [0] * 36
    pending = [[] for _ in range(36)]
    cx_layers = collections.defaultdict(list)
    local_layers = collections.defaultdict(dict)
    for name, targets in gates:
        if name == 'CX':
            first, second = targets
            level = max(depth[first], depth[second]) + 1
            for qubit in targets:
                if pending[qubit]:
                    local_layers[level][qubit] = pending[qubit]
                    pending[qubit] = []
                depth[qubit] = level
            cx_layers[level].append({'gate': name, 'targets': list(targets)})
        else:
            pending[targets[0]].append(name)
    last = max(depth) + 1
    for qubit in range(36):
        if pending[qubit]:
            local_layers[last][qubit] = pending[qubit]
    layers = []
    for level in range(1, last + 1):
        singles = local_layers[level]
        for offset in range(max(map(len, singles.values()), default=0)):
            layers.append([{'gate': word[offset], 'targets': [qubit]} for qubit, word in singles.items() if offset < len(word)])
        if cx_layers[level]:
            layers.append(cx_layers[level])
    return {'schema_version': 1, 'num_qubits': 36, 'layers': layers}


def correct_signs(gates):
    target = json.loads((ROOT / 'input/target.json').read_text())
    expected = [parse_pauli(text, 36) for text in target['x_outputs'] + target['z_outputs']]
    actual = tableau(schedule_native(gates))
    assert all(left[:2] == right[:2] for left, right in zip(actual, expected)), 'unsigned mismatch'
    before = []
    for qubit in range(36):
        if actual[qubit][2] != expected[qubit][2]:
            before.extend([('S', (qubit,))] * 2)
        if actual[qubit + 36][2] != expected[qubit + 36][2]:
            before.extend([('H', (qubit,)), ('S', (qubit,)), ('S', (qubit,)), ('H', (qubit,))])
    return simplify_locals(before + gates)


def build(search_path=None, seed=0):
    left, right = [], []
    rows = initial()
    if search_path:
        data = json.loads(Path(search_path).read_text())
        rows = data['rows']
        for side, first, second, axis_first, axis_second in data['history']:
            block = generalized(first, second, axis_first, axis_second)
            if side == 0:
                left.extend(block)
            else:
                right.extend(block)
    raw = right + eliminate(rows, seed) + inverse_gates(left)
    generalized_gates, frames = generalize(raw)
    generalized_gates = cancel_generalized(generalized_gates)
    if search_path and Path(search_path).name.startswith('trial_'):
        (OUT / ('generalized_' + Path(search_path).name)).write_text(json.dumps({'gates': generalized_gates, 'frames': frames}))
    schedules = [schedule_generalized(generalized_gates, seed + index) for index in range(10)]
    layers = min(schedules, key=len)
    gates = correct_signs(realize(layers, frames))
    artifact = schedule_native(gates)
    instance = {name: json.loads((ROOT / 'input' / (name + '.json')).read_text()) for name in ('constraints', 'target')}
    result = check(artifact, instance)
    print(search_path, seed, json.dumps(result), flush=True)
    previous = OUT / 'best_metrics.json'
    if not previous.exists() or json.loads(previous.read_text())['score'] < result['score']:
        (OUT / 'circuit.json').write_text(json.dumps(artifact, separators=(',', ':')))
        previous.write_text(json.dumps(result, indent=2))
        (OUT / 'best_generalized.json').write_text(json.dumps({'gates': generalized_gates, 'frames': frames}))
    return result


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != '-' else None
    build(path, int(sys.argv[2]) if len(sys.argv) > 2 else 0)
