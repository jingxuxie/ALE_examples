import itertools
import json
import random
import sys
import time

import synthesize as syn
from greedy import AXES, OUT, ROOT

IDENTITY2 = (1, 0, 2, 0, 0, 1, 0, 2)


def entangle_state(state, first_axis, second_axis):
    result = []
    first_x, first_z = AXES[first_axis]
    second_x, second_z = AXES[second_axis]
    for index in range(0, 8, 2):
        xrow, zrow = state[index:index + 2]
        first_anti = (first_x & zrow & 1) ^ (first_z & xrow & 1)
        second_anti = (second_x & (zrow >> 1)) ^ (second_z & (xrow >> 1))
        xrow ^= (first_x * second_anti) | (second_x * first_anti << 1)
        zrow ^= (first_z * second_anti) | (second_z * first_anti << 1)
        result.extend((xrow, zrow))
    return tuple(result)


def apply_frames(state, frames):
    result = []
    for index in range(0, 8, 2):
        xrow, zrow = state[index:index + 2]
        new_x = new_z = 0
        for qubit, frame in enumerate(frames):
            xbit, zbit = (xrow >> qubit) & 1, (zrow >> qubit) & 1
            new_x |= ((frame[0] * xbit) ^ (frame[3] * zbit)) << qubit
            new_z |= ((frame[1] * xbit) ^ (frame[4] * zbit)) << qubit
        result.extend((new_x, new_z))
    return tuple(result)


def make_table():
    table = {}
    local_pairs = list(itertools.product(syn.FRAME_WORDS, repeat=2))
    sequences = [(IDENTITY2, ())]
    for length in range(4):
        for state, sequence in sequences:
            for frames in local_pairs:
                updated = apply_frames(state, frames)
                if updated not in table:
                    table[updated] = (length, [])
                if table[updated][0] == length:
                    table[updated][1].append((sequence, frames))
        sequences = [(entangle_state(state, axis // 3, axis % 3), sequence + (axis,)) for state, sequence in sequences for axis in range(9)]
    assert len(table) == 720
    return table


def windows(gates, table, improvements_only=True):
    proposals = []
    largest = 1 if improvements_only else 0
    for anchor, gate in enumerate(gates):
        first, second = sorted(gate[:2])
        indices = []
        blockers = {first: set(), second: set()}
        for index in range(anchor, -1, -1):
            old = gates[index]
            axes = dict(zip(old[:2], old[2:]))
            if set(old[:2]) == {first, second}:
                if any(any(axis != axes[qubit] for axis in blockers[qubit]) for qubit in (first, second)):
                    break
                indices.append(index)
                if len(indices) >= 2:
                    state = IDENTITY2
                    for chosen in reversed(indices):
                        chosen_axes = dict(zip(gates[chosen][:2], gates[chosen][2:]))
                        state = entangle_state(state, chosen_axes[first], chosen_axes[second])
                    improvement = len(indices) - table[state][0]
                    if improvement >= largest:
                        if improvement > largest:
                            proposals = []
                            largest = improvement
                        proposals.append((indices[:], state, first, second))
                if len(indices) >= 8:
                    break
            else:
                for qubit in (first, second):
                    if qubit in axes:
                        blockers[qubit].add(axes[qubit])
                if any(len(blockers[qubit]) > 1 for qubit in (first, second)):
                    break
    return largest, proposals


def replace(gates, frames, proposal, representation):
    indices, state, first, second = proposal
    chosen = set(indices)
    sequence, local_frames = representation
    raw = []
    for index, gate in enumerate(gates):
        if index == indices[0]:
            for axis in sequence:
                raw.extend(syn.generalized(first, second, axis // 3, axis % 3))
            for qubit, frame in zip((first, second), local_frames):
                raw.extend((name, (qubit,)) for name in syn.FRAME_WORDS[frame])
        elif index not in chosen:
            raw.extend(syn.generalized(*gate))
    for qubit, frame in enumerate(frames):
        raw.extend((name, (qubit,)) for name in syn.FRAME_WORDS[tuple(frame)])
    result, result_frames = syn.generalize(raw)
    return syn.cancel_generalized(result), result_frames


def save(gates, frames, seed=0):
    schedules = [syn.schedule_generalized(gates, seed + offset) for offset in range(10)]
    layers = min(schedules, key=len)
    native = syn.correct_signs(syn.realize(layers, frames))
    artifact = syn.schedule_native(native)
    instance = {name: json.loads((ROOT / 'input' / (name + '.json')).read_text()) for name in ('constraints', 'target')}
    result = syn.check(artifact, instance)
    previous = json.loads((OUT / 'best_metrics.json').read_text())
    print('candidate', len(gates), len(layers), result['score'], result['metrics'], flush=True)
    current_quality = (result['score'], -result['metrics']['cx_count'], -result['metrics']['entangling_depth'], -result['metrics']['gate_count'])
    previous_quality = (previous['score'], -previous['metrics']['cx_count'], -previous['metrics']['entangling_depth'], -previous['metrics']['gate_count'])
    if current_quality > previous_quality:
        (OUT / 'circuit.json').write_text(json.dumps(artifact, separators=(',', ':')))
        (OUT / 'best_metrics.json').write_text(json.dumps(result, indent=2))
        (OUT / 'best_generalized.json').write_text(json.dumps({'gates': gates, 'frames': frames}))
    return len(layers)


def main():
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 240
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    randomizer = random.Random(seed)
    data = json.loads((OUT / 'best_generalized.json').read_text())
    gates, frames = data['gates'], data['frames']
    table = make_table()
    started = time.time()
    best_depth = len(syn.schedule_generalized(gates))
    best_count = len(gates)
    best_state = gates, frames
    iteration = 0
    stagnant = 0
    while time.time() - started < seconds:
        improvement, proposals = windows(gates, table)
        if not proposals:
            depth = len(syn.schedule_generalized(gates))
            if depth < best_depth or (depth == best_depth and len(gates) < best_count):
                best_depth = save(gates, frames, seed)
                best_count = len(gates)
                best_state = gates, frames
                stagnant = 0
            else:
                stagnant += 1
            if stagnant % 5 == 0:
                gates, frames = best_state
            improvement, proposals = windows(gates, table, False)
            if not proposals:
                break
            for _ in range(randomizer.randrange(1, 5)):
                proposal = randomizer.choice(proposals)
                representation = randomizer.choice(table[proposal[1]][1])
                gates, frames = replace(gates, frames, proposal, representation)
                improvement, proposals = windows(gates, table, False)
                if not proposals:
                    break
        else:
            proposal = randomizer.choice(proposals)
            representation = randomizer.choice(table[proposal[1]][1])
            gates, frames = replace(gates, frames, proposal, representation)
        iteration += 1
        if iteration % 100 == 0:
            print('iteration', iteration, 'gates', len(gates), 'best', best_count, best_depth, flush=True)
    save(*best_state, seed)


if __name__ == '__main__':
    main()
