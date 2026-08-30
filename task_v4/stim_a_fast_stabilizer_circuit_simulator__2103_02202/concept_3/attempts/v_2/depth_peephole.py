import ctypes
import json
import random
import time
from pathlib import Path

import synthesis as syn
import ppr_optimize as ppr
import peephole4 as peep

LIBRARY = ctypes.CDLL(str(Path('libfourdepth.so').resolve()))
LIBRARY.solve_four_depth.argtypes = [ctypes.c_uint64, ctypes.c_int, ctypes.c_int]
LIBRARY.solve_four_depth.restype = ctypes.c_char_p
CACHE = {}

def solve(key, topology, bound):
    if bound <= 0:
        return None
    cachekey = (key, topology, bound)
    if cachekey in CACHE:
        return CACHE[cachekey]
    encoded = LIBRARY.solve_four_depth(key, topology, bound)
    if encoded is None:
        CACHE[cachekey] = None
        return None
    gates = []
    for item in encoded.decode().split(';'):
        if not item:
            continue
        fields = item.split(',')
        arguments = list(map(int, fields[1:]))
        gates.extend(syn.ppr(*arguments) if fields[0] == 'R' else [(fields[0], *arguments)])
    CACHE[cachekey] = syn.simplify(gates)
    return CACHE[cachekey]

def main():
    gates = [tuple(operation) for operation in json.loads(Path('best_gates.json').read_text())]
    groups = [(qubits, topology) for qubits, topology in peep.subsets() if topology != 1]
    rng = random.Random(2647)
    started = time.monotonic()
    for iteration in range(12):
        rotations, frames = ppr.extract(gates)
        rotations = ppr.reorder(rotations, iteration)
        gates = syn.simplify(ppr.native(rotations, frames))
        rng.shuffle(groups)
        for qubits, topology in groups:
            gates = peep.reduce_block(gates, qubits, topology, solve, True)
        syn.save(gates[:], f'depth_peephole:{iteration}')
        Path('depth_peephole_latest.json').write_text(json.dumps(gates) + '\n')
        print('elapsed', time.monotonic() - started, flush=True)
        if time.monotonic() - started > 150 or sum(operation[0] == 'CX' for operation in gates) > 650:
            break

if __name__ == '__main__':
    main()
