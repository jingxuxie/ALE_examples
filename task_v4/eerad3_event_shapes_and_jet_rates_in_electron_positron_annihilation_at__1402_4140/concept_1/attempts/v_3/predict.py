import ctypes
import os
import sys
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import numpy as np


def main():
    with np.load(sys.argv[1]) as data:
        invariants = np.ascontiguousarray(data['s'], dtype=np.float64)
    if invariants.ndim != 2 or invariants.shape[1] != 10:
        raise ValueError('Expected s with shape (N, 10)')
    output = np.empty(invariants.shape[0], dtype=np.float64)
    library = ctypes.CDLL(str(Path(__file__).resolve().with_name('kernel.so')))
    pointer = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
    library.predict.argtypes = [ctypes.c_size_t, pointer, ctypes.c_void_p, pointer, ctypes.c_int]
    library.predict.restype = None
    library.predict(len(output), invariants, None, output, 0)
    np.savez(sys.argv[2], log_weight=output)


if __name__ == '__main__':
    main()
