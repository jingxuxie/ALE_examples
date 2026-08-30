import collections
import itertools
import json
import random
import sys
import time

import greedy
import pair_opt
import synthesize as syn

IDENTITY = (1, 8, 2, 16, 4, 32)
MOVES = [(first, second, axis_first, axis_second) for first, second in ((0, 1), (1, 2)) for axis_first in range(3) for axis_second in range(3)]
PATHS = []
for center, neighbors in enumerate(syn.NEIGHBORS):
    for first, second in itertools.combinations(neighbors, 2):
        PATHS.append((first, center, second))
FRAME_LIST = list(syn.FRAME_WORDS)


def transition(state, move):
    first, second, axis_first, axis_second = move
    updated = greedy.entangle(state[first * 2:first * 2 + 2], state[second * 2:second * 2 + 2], axis_first, axis_second)
    output = list(state)
    output[first * 2:first * 2 + 2] = updated[0]
    output[second * 2:second * 2 + 2] = updated[1]
    return tuple(output)


def canonicalize(state):
    output, frames = [], []
    for qubit in range(3):
        xcol, zcol = state[2 * qubit:2 * qubit + 2]
        new_x, new_z, unused = sorted((xcol, zcol, xcol ^ zcol))
        output.extend((new_x, new_z))
        xcoef = (1, 0) if new_x == xcol else (0, 1) if new_x == zcol else (1, 1)
        zcoef = (1, 0) if new_z == xcol else (0, 1) if new_z == zcol else (1, 1)
        frames.append((xcoef[0], zcoef[0], 0, xcoef[1], zcoef[1], 0))
    return tuple(output), frames


def make_table():
    distances = {IDENTITY: 0}
    predecessors = collections.defaultdict(list)
    queue = [IDENTITY]
    for state in queue:
        distance = distances[state] + 1
        for move in MOVES:
            updated, frames = canonicalize(transition(state, move))
            if updated not in distances:
                distances[updated] = distance
                queue.append(updated)
            if distances[updated] == distance:
                predecessors[updated].append((state, move, frames))
    assert len(distances) == 6720, len(distances)
    print('table', len(distances), 'diameter', max(distances.values()), flush=True)
    return distances, predecessors


def representation(state, predecessors, randomizer):
    canonical, final_frames = canonicalize(state)
    path = []
    while canonical != IDENTITY:
        previous, move, frames = randomizer.choice(predecessors[canonical])
        path.append((move, frames))
        canonical = previous
    raw = []
    for move, frames in reversed(path):
        raw.extend(syn.generalized(*move))
        for qubit, frame in enumerate(frames):
            raw.extend((name, (qubit,)) for name in syn.FRAME_WORDS[frame])
    last = [(name, (qubit,)) for qubit, frame in enumerate(final_frames) for name in syn.FRAME_WORDS[frame]]
    raw.extend(syn.inverse_gates(last))
    return raw


def windows(gates, distances, improvements_only=True, randomizer=None):
    largest = 1 if improvements_only else 0
    proposals = []
    paths = list(PATHS)
    if randomizer:
        randomizer.shuffle(paths)
    for path in paths:
        positions = {qubit: position for position, qubit in enumerate(path)}
        nodes = set(path)
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
                    state = transition(state, move)
                    if len(indices) >= 3 and len(used_edges) == 2:
                        canonical, frames = canonicalize(state)
                        improvement = len(indices) - distances[canonical]
                        if improvement >= largest:
                            if improvement > largest:
                                proposals = []
                                largest = improvement
                            proposals.append((indices[:], state, path))
                    if len(indices) >= 12:
                        break
                else:
                    for qubit in nodes.intersection(axes):
                        blockers[qubit].add(axes[qubit])
                    if sum(len(blockers[qubit]) > 1 for qubit in path) >= 2:
                        break
    return largest, proposals


def replace(gates, frames, proposal, predecessors, randomizer):
    indices, state, path = proposal
    removed = set(indices)
    inverse_block = representation(state, predecessors, randomizer)
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
    distances, predecessors = make_table()
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
            improvement, proposals = windows(gates, distances, True)
            if proposals:
                proposal = randomizer.choice(proposals)
                gates, frames = replace(gates, frames, proposal, predecessors, randomizer)
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
                improvement, proposals = windows(gates, distances, False)
                if not proposals:
                    break
                proposal = randomizer.choice(proposals)
                gates, frames = replace(gates, frames, proposal, predecessors, randomizer)
        iteration += 1
        if iteration % 50 == 0:
            print('iteration', iteration, 'count', len(gates), 'best', best_count, best_depth, flush=True)
    depth = len(syn.schedule_generalized(gates))
    if depth < best_depth:
        best_state = gates, frames
    pair_opt.save(*best_state, seed)


if __name__ == '__main__':
    main()
