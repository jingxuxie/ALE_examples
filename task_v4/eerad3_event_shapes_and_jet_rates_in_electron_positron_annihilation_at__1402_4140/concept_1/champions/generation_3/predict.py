import os
import sys
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import ctypes
import numpy as np


def main():
    with np.load(sys.argv[1], allow_pickle=False) as data:
        invariants = np.ascontiguousarray(data['s'], dtype=np.float64)
    if invariants.ndim != 2 or invariants.shape[1] != 10:
        raise ValueError('s must have shape (N, 10)')
    prediction = np.empty(invariants.shape[0], dtype=np.float64)
    library = ctypes.CDLL(str(Path(__file__).resolve().with_name('kernel.so')))
    pointer = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
    library.predict.argtypes = [pointer, pointer, ctypes.c_int]
    library.predict.restype = None
    library.predict(invariants, prediction, prediction.size)
    np.savez(sys.argv[2], log_weight=prediction)


if __name__ == '__main__':
    main()
