import os

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import ctypes
from pathlib import Path
import subprocess
import sys

import numpy as np


def predict(momenta, invariants):
    directory = Path(__file__).resolve().parent
    library_path = directory / 'kernel.so'
    if not library_path.exists():
        subprocess.run(['g++', '-std=c++17', '-O3', '-DNDEBUG', '-fPIC', '-shared',
                        str(directory / 'kernel.cpp'), '-o', str(library_path)], check=True)
    library = ctypes.CDLL(str(library_path))
    function = library.predict_kernel
    pointer = ctypes.POINTER(ctypes.c_double)
    function.argtypes = [pointer, pointer, pointer, ctypes.c_long]
    function.restype = None
    momenta = np.ascontiguousarray(momenta, dtype=np.float64)
    invariants = np.ascontiguousarray(invariants, dtype=np.float64)
    if momenta.ndim != 3 or momenta.shape[1:] != (5, 4):
        raise ValueError('p must have shape (N, 5, 4)')
    if invariants.shape != (len(momenta), 10):
        raise ValueError('s must have shape (N, 10)')
    output = np.empty(len(momenta), dtype=np.float64)
    function(momenta.ctypes.data_as(pointer), invariants.ctypes.data_as(pointer),
             output.ctypes.data_as(pointer), len(output))
    if not np.all(np.isfinite(output)):
        raise ValueError('Nonfinite matrix element for an input event')
    return output


def main():
    if len(sys.argv) != 3:
        raise SystemExit('Usage: python3 predict.py INPUT.npz OUTPUT.npz')
    with np.load(sys.argv[1], allow_pickle=False) as data:
        result = predict(data['p'], data['s'])
    with open(sys.argv[2], 'wb') as stream:
        np.savez(stream, log_weight=result)


if __name__ == '__main__':
    main()
