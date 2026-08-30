import ctypes
import json
import random
import sys
import time
from pathlib import Path

import synthesis as syn
import ppr_optimize as ppr

LIBRARY = ctypes.CDLL(str(Path('libfour.so').resolve()))
LIBRARY.solve_four.argtypes = [ctypes.c_uint64, ctypes.c_int, ctypes.c_int]
LIBRARY.solve_four.restype = ctypes.c_char_p
CACHE = {}

def solve(key, topology, bound):
    cachekey = (key, topology, bound)
    if cachekey in CACHE:
        return CACHE[cachekey]
    encoded = LIBRARY.solve_four(key, topology, bound)
    if encoded is None:
        CACHE[cachekey] = None
        return None
    gates = []
    for item in encoded.decode().split(';'):
        if not item:
            continue
        fields = item.split(',')
        arguments = list(map(int, fields[1:]))
        if fields[0] == 'R':
            gates.extend(syn.ppr(*arguments))
        else:
            gates.append((fields[0], *arguments))
    CACHE[cachekey] = syn.simplify(gates)
    return CACHE[cachekey]

def depth(gates):
    depths = [0] * 36
    for operation in gates:
        if operation[0] == 'CX':
            first, second = operation[1:]
            depths[first] = depths[second] = 1 + max(depths[first], depths[second])
    return max(depths)

def reduce_block(gates, qubits, topology, solver=solve, depth_mode=False):
    positions = []
    replacements = {}
    removed = set()
    mapping = {qubit: index for index, qubit in enumerate(qubits)}
    def flush():
        if not positions:
            return
        original_gates = [gates[index] for index in positions]
        count = sum(operation[0] == 'CX' for operation in original_gates)
        if count < 2:
            positions.clear()
            return
        width = len(qubits)
        state = [column for qubit in range(width) for column in (1 << qubit, 1 << (qubit + width))]
        for operation in original_gates:
            gate, first = operation[0], mapping[operation[1]]
            if gate == 'H':
                state[2 * first], state[2 * first + 1] = state[2 * first + 1], state[2 * first]
            elif gate == 'S':
                state[2 * first + 1] ^= state[2 * first]
            else:
                second = mapping[operation[2]]
                state[2 * second] ^= state[2 * first]
                state[2 * first + 1] ^= state[2 * second + 1]
        tail = []
        for qubit in range(width):
            original = state[2 * qubit:2 * qubit + 2]
            canonical = sorted([*original, original[0] ^ original[1]])[:2]
            for word in ('', 'H', 'S', 'HS', 'SH', 'HSH'):
                trial = original[:]
                for gate in word:
                    if gate == 'H':
                        trial.reverse()
                    else:
                        trial[1] ^= trial[0]
                if trial == canonical:
                    tail.extend((gate, qubit) for gate in word[::-1])
                    break
            state[2 * qubit:2 * qubit + 2] = canonical
        key = sum(column << (2 * width * index) for index, column in enumerate(state))
        olddepth = depth(original_gates)
        solved = solver(key, topology, min(olddepth - 1, 4) if depth_mode else min(count, 6))
        if solved is not None:
            word = syn.simplify(solved + tail)
            newcount = sum(operation[0] == 'CX' for operation in word)
            improvement = depth(word) < olddepth and newcount <= count + 2 if depth_mode else (newcount, depth(word), len(word)) < (count, olddepth, len(positions))
            if improvement:
                replacements[positions[0]] = [(operation[0], *(qubits[qubit] for qubit in operation[1:])) for operation in word]
                removed.update(positions)
        positions.clear()
    for index, operation in enumerate(gates):
        if not any(qubit in mapping for qubit in operation[1:]):
            continue
        if all(qubit in mapping for qubit in operation[1:]):
            positions.append(index)
        else:
            flush()
    flush()
    return [operation for index, original in enumerate(gates) for operation in (replacements.get(index, []) if index in removed else [original])]

def subsets():
    groups = {frozenset([qubit]) for qubit in range(36)}
    for size in range(1, 4):
        groups = {group | {neighbor} for group in groups for qubit in group for neighbor in syn.NEIGHBORS[qubit] if neighbor not in group}
    result = []
    for group in groups:
        adjacency = {qubit: [other for other in syn.NEIGHBORS[qubit] if other in group] for qubit in group}
        centers = [qubit for qubit in group if len(adjacency[qubit]) == 3]
        if centers:
            center = centers[0]
            leaves = sorted(adjacency[center])
            result.append(((leaves[0], center, leaves[1], leaves[2]), 1))
        else:
            endpoints = [qubit for qubit in group if len(adjacency[qubit]) == 1]
            order = [min(endpoints) if endpoints else min(group)]
            while len(order) < 4:
                order.append(min(other for other in adjacency[order[-1]] if other not in order))
            result.append((tuple(order), 0 if endpoints else 2))
    return result

def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('best_gates.json')
    iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    gates = [tuple(operation) for operation in json.loads(source.read_text())]
    groups = subsets()
    rng = random.Random(5473)
    started = time.monotonic()
    for iteration in range(iterations):
        rotations, frames = ppr.extract(gates)
        rotations = ppr.cancel(rotations)
        rotations = ppr.conjugate_reduce(rotations)
        rotations = ppr.reorder(rotations, iteration)
        gates = syn.simplify(ppr.native(rotations, frames))
        rng.shuffle(groups)
        for qubits, topology in groups:
            gates = reduce_block(gates, qubits, topology)
        syn.save(gates[:], f'peephole4:{source}:{iteration}')
        Path('peephole4_latest.json').write_text(json.dumps(gates) + '\n')
        print('elapsed', time.monotonic() - started, 'cache', len(CACHE), flush=True)
        if time.monotonic() - started > 480:
            break

if __name__ == '__main__':
    main()
