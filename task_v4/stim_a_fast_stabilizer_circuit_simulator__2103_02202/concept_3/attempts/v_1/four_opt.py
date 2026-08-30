import itertools
import json
import random
import struct
import sys
import time

import greedy
import pair_opt
import synthesize as syn
import three_opt

SHAPES = [((0, 1), (1, 2), (2, 3)), ((0, 1), (0, 2), (0, 3)), ((0, 1), (1, 2), (2, 3), (3, 0))]
MOVES = [[(first, second, axis_first, axis_second) for first, second in shape for axis_first in range(3) for axis_second in range(3)] for shape in SHAPES]
IDENTITY = tuple(value for qubit in range(4) for value in (1 << qubit, 1 << (qubit + 4)))


def canonicalize(state):
    output, frames = 0, []
    for qubit in range(4):
        xcol, zcol = state[2 * qubit:2 * qubit + 2]
        new_x, new_z, unused = sorted((xcol, zcol, xcol ^ zcol))
        output |= new_x << (16 * qubit)
        output |= new_z << (16 * qubit + 8)
        xcoef = (1, 0) if new_x == xcol else (0, 1) if new_x == zcol else (1, 1)
        zcoef = (1, 0) if new_z == xcol else (0, 1) if new_z == zcol else (1, 1)
        frames.append((xcoef[0], zcoef[0], 0, xcoef[1], zcoef[1], 0))
    return output, frames


class Records:
    def __init__(self, data):
        self.data = data
        self.count, = struct.unpack_from('<I', data)

    def __getitem__(self, index):
        return struct.unpack_from('<QIBBH', self.data, 4 + index * 16)


def load_tables(prefix='four_table_'):
    tables = []
    for shape in range(3):
        data = (greedy.OUT / f'{prefix}{shape}.bin').read_bytes()
        count, = struct.unpack_from('<I', data)
        records = Records(data)
        assert len(data) == 4 + count * 16
        lookup = {struct.unpack_from('<Q', data, 4 + index * 16)[0]: index for index in range(count)}
        tables.append((records, lookup))
        print('table', shape, count, flush=True)
    return tables


def templates():
    paths = set()
    for first in range(36):
        for second in syn.NEIGHBORS[first]:
            for third in syn.NEIGHBORS[second]:
                if third == first:
                    continue
                for fourth in syn.NEIGHBORS[third]:
                    if fourth in (first, second) or fourth in syn.NEIGHBORS[first]:
                        continue
                    path = (first, second, third, fourth)
                    paths.add(min(path, path[::-1]))
    result = [(0, path) for path in sorted(paths)]
    for center, neighbors in enumerate(syn.NEIGHBORS):
        result.extend((1, (center, *ends)) for ends in itertools.combinations(neighbors, 3))
    for row in range(5):
        for column in range(5):
            first = row * 6 + column
            result.append((2, (first, first + 1, first + 7, first + 6)))
    return result


TEMPLATES = templates()


def representation(state, shape, tables):
    canonical, final_frames = canonicalize(state)
    records, lookup = tables[shape]
    index = lookup[canonical]
    path = []
    while index:
        state_key, previous, move_index, depth, frames = records[index]
        path.append((MOVES[shape][move_index], frames))
        index = previous
    raw = []
    for move, frames in reversed(path):
        raw.extend(syn.generalized(*move))
        for qubit in range(4):
            code = (frames >> (qubit * 4)) & 15
            xselector, zselector = code & 3, code >> 2
            frame = (xselector & 1, zselector & 1, 0, xselector >> 1, zselector >> 1, 0)
            raw.extend((name, (qubit,)) for name in syn.FRAME_WORDS[frame])
    last = [(name, (qubit,)) for qubit, frame in enumerate(final_frames) for name in syn.FRAME_WORDS[frame]]
    raw.extend(syn.inverse_gates(last))
    return raw


def windows(gates, tables, improvements_only=True, randomizer=None):
    largest = 1 if improvements_only else 0
    proposals = []
    selected_templates = TEMPLATES[:]
    if randomizer:
        randomizer.shuffle(selected_templates)
    for shape, path in selected_templates:
        positions = {qubit: position for position, qubit in enumerate(path)}
        nodes = set(path)
        records, lookup = tables[shape]
        anchors = [index for index, gate in enumerate(gates) if set(gate[:2]) <= nodes]
        for anchor in anchors:
            indices = []
            blockers = {qubit: set() for qubit in path}
            state = IDENTITY
            used_edges = set()
            for index in range(anchor, max(-1, anchor - 150), -1):
                gate = gates[index]
                axes = dict(zip(gate[:2], gate[2:]))
                if set(gate[:2]) <= nodes:
                    if any(any(axis != axes[qubit] for axis in blockers[qubit]) for qubit in gate[:2]):
                        break
                    indices.append(index)
                    used_edges.add(tuple(sorted(gate[:2])))
                    move = (positions[gate[0]], positions[gate[1]], gate[2], gate[3])
                    state = three_opt.transition(state, move)
                    if len(indices) >= 4 and len(used_edges) >= 3:
                        canonical, frames = canonicalize(state)
                        found = lookup.get(canonical)
                        if found is not None:
                            improvement = len(indices) - records[found][3]
                            if improvement >= largest:
                                if improvement > largest:
                                    proposals = []
                                    largest = improvement
                                proposals.append((indices[:], state, shape, path))
                    if len(indices) >= 10:
                        break
                else:
                    for qubit in nodes.intersection(axes):
                        blockers[qubit].add(axes[qubit])
                    if sum(len(blockers[qubit]) > 1 for qubit in path) >= 3:
                        break
    return largest, proposals


def replace(gates, frames, proposal, tables):
    indices, state, shape, path = proposal
    removed = set(indices)
    inverse_block = representation(state, shape, tables)
    block = [(name, tuple(path[qubit] for qubit in targets)) for name, targets in syn.inverse_gates(inverse_block)]
    raw = []
    for index, gate in enumerate(gates):
        if index == indices[0]:
            raw.extend(block)
        elif index not in removed:
            raw.extend(syn.generalized(*gate))
    for qubit, frame in enumerate(frames):
        raw.extend((name, (qubit,)) for name in syn.FRAME_WORDS[tuple(frame)])
    result, final_frames = syn.generalize(raw)
    return syn.cancel_generalized(result), final_frames


def main():
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    randomizer = random.Random(seed)
    data = json.loads((greedy.OUT / 'best_generalized.json').read_text())
    gates, frames = data['gates'], data['frames']
    tables = load_tables()
    distances, predecessors = three_opt.make_table()
    pair_table = pair_opt.make_table()
    started = time.time()
    best_depth = len(syn.schedule_generalized(gates))
    best_count = len(gates)
    best_state = gates, frames
    iteration, stagnant = 0, 0
    while time.time() - started < seconds:
        improvement, proposals = pair_opt.windows(gates, pair_table)
        if proposals:
            proposal = randomizer.choice(proposals)
            choice = randomizer.choice(pair_table[proposal[1]][1])
            gates, frames = pair_opt.replace(gates, frames, proposal, choice)
        else:
            improvement, proposals = three_opt.windows(gates, distances, True)
            if proposals:
                proposal = randomizer.choice(proposals)
                gates, frames = three_opt.replace(gates, frames, proposal, predecessors, randomizer)
            else:
                improvement, proposals = windows(gates, tables, True)
                if proposals:
                    proposal = randomizer.choice(proposals)
                    gates, frames = replace(gates, frames, proposal, tables)
                else:
                    depth = len(syn.schedule_generalized(gates))
                    if depth < best_depth or (depth == best_depth and len(gates) < best_count):
                        best_depth = pair_opt.save(gates, frames, seed)
                        best_count = len(gates)
                        best_state = gates, frames
                        stagnant = 0
                    else:
                        stagnant += 1
                    if stagnant % 10 == 0:
                        gates, frames = best_state
                    improvement, proposals = windows(gates, tables, False, randomizer)
                    if not proposals:
                        break
                    gates, frames = replace(gates, frames, randomizer.choice(proposals), tables)
        iteration += 1
        if iteration % 25 == 0:
            depth = len(syn.schedule_generalized(gates))
            print('iteration', iteration, 'count', len(gates), 'depth', depth, 'best', best_count, best_depth, flush=True)
            if depth < best_depth:
                best_depth = pair_opt.save(gates, frames, seed)
                best_count = len(gates)
                best_state = gates, frames
    depth = len(syn.schedule_generalized(gates))
    if depth < best_depth:
        best_state = gates, frames
    pair_opt.save(*best_state, seed)


if __name__ == '__main__':
    main()
