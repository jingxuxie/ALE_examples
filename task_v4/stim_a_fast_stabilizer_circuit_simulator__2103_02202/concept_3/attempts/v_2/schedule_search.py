import ctypes
import json
import sys
import time
from pathlib import Path

import synthesis as syn
import ppr_optimize as ppr

LIBRARY = ctypes.CDLL(str(Path('libscheduler.so').resolve()))
LIBRARY.schedule_rotations.argtypes = [ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint64), ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
LIBRARY.schedule_rotations.restype = ctypes.c_int

def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('best_gates.json')
    gates = [tuple(operation) for operation in json.loads(source.read_text())]
    rotations, frames = ppr.extract(gates)
    started = time.monotonic()
    for seed in range(24):
        count = len(rotations)
        xvalues = (ctypes.c_uint64 * count)(*(rotation[0] for rotation in rotations))
        zvalues = (ctypes.c_uint64 * count)(*(rotation[1] for rotation in rotations))
        indices = (ctypes.c_int * count)()
        depth = LIBRARY.schedule_rotations(xvalues, zvalues, count, 120000, 3673 + seed, indices)
        rotations = [rotations[index] for index in indices]
        syn.save(ppr.native(rotations, frames), f'schedule_search:{source}:{seed}:{depth}')
        print('elapsed', time.monotonic() - started, flush=True)
        if time.monotonic() - started > 180:
            break

if __name__ == '__main__':
    main()
