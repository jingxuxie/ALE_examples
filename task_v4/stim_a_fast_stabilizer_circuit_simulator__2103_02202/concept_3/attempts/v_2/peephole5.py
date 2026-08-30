import ctypes
import json
import random
import sys
import time
from pathlib import Path

import synthesis as syn
import ppr_optimize as ppr
import peephole4 as peep

LIBRARY = ctypes.CDLL(str(Path('libfive.so').resolve()))
LIBRARY.solve_five.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.c_int, ctypes.c_int]
LIBRARY.solve_five.restype = ctypes.c_char_p
CACHE = {}

def solve(key, topology, bound):
    cachekey = (key, topology, bound)
    if cachekey in CACHE:
        return CACHE[cachekey]
    encoded = LIBRARY.solve_five(key & ((1 << 64) - 1), key >> 64, topology, bound)
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

def subsets():
    groups = {frozenset([qubit]) for qubit in range(36)}
    for size in range(1, 5):
        groups = {group | {neighbor} for group in groups for qubit in group for neighbor in syn.NEIGHBORS[qubit] if neighbor not in group}
    result = []
    for group in groups:
        adjacency = {qubit: [other for other in syn.NEIGHBORS[qubit] if other in group] for qubit in group}
        degree = {qubit: len(adjacency[qubit]) for qubit in group}
        center = max(group, key=lambda qubit: degree[qubit])
        if degree[center] == 4:
            result.append(((center, *sorted(adjacency[center])), 1))
        elif degree[center] == 3:
            if sum(degree.values()) == 10:
                leaf = next(qubit for qubit in adjacency[center] if degree[qubit] == 1)
                order = [center, min(qubit for qubit in adjacency[center] if qubit != leaf)]
                while len(order) < 4:
                    order.append(next(qubit for qubit in adjacency[order[-1]] if qubit not in order))
                result.append(((*order, leaf), 3))
            else:
                middle = next(qubit for qubit in adjacency[center] if degree[qubit] == 2)
                endpoint = next(qubit for qubit in adjacency[middle] if qubit != center)
                leaves = sorted(qubit for qubit in adjacency[center] if qubit != middle)
                result.append(((center, middle, endpoint, *leaves), 2))
        else:
            order = [min(qubit for qubit in group if degree[qubit] == 1)]
            while len(order) < 5:
                order.append(next(qubit for qubit in adjacency[order[-1]] if qubit not in order))
            result.append((tuple(order), 0))
    return result

def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('best_gates.json')
    iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    gates = [tuple(operation) for operation in json.loads(source.read_text())]
    groups = subsets()
    rng = random.Random(7844)
    started = time.monotonic()
    for iteration in range(iterations):
        rotations, frames = ppr.extract(gates)
        rotations = ppr.cancel(rotations)
        rotations = ppr.conjugate_reduce(rotations)
        rotations = ppr.reorder(rotations, iteration)
        gates = syn.simplify(ppr.native(rotations, frames))
        rng.shuffle(groups)
        for qubits, topology in groups:
            gates = peep.reduce_block(gates, qubits, topology, solve)
        syn.save(gates[:], f'peephole5:{source}:{iteration}')
        Path('peephole5_latest.json').write_text(json.dumps(gates) + '\n')
        print('elapsed', time.monotonic() - started, 'cache', len(CACHE), flush=True)
        if time.monotonic() - started > 420:
            break

if __name__ == '__main__':
    main()
