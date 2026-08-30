import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

import ctypes
import sys
from pathlib import Path

import numpy as np


def main():
    if len(sys.argv) != 3:
        raise SystemExit('Usage: python3 predict.py INPUT.npz OUTPUT.npz')
    with np.load(sys.argv[1]) as data:
        momentum = np.ascontiguousarray(data['p'], dtype=np.float64)
    if momentum.ndim != 3 or momentum.shape[1:] != (5, 4):
        raise ValueError('p must have shape (N, 5, 4)')
    prediction = np.empty(len(momentum), dtype=np.float64)
    library = ctypes.CDLL(str(Path(__file__).resolve().with_name('kernel.so')))
    pointer = ctypes.POINTER(ctypes.c_double)
    library.predict_kernel.argtypes = [pointer, pointer, ctypes.c_size_t]
    library.predict_kernel.restype = None
    library.predict_kernel(momentum.ctypes.data_as(pointer),
                           prediction.ctypes.data_as(pointer), len(momentum))
    np.savez(sys.argv[2], log_weight=prediction)


if __name__ == '__main__':
    main()
