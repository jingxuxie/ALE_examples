import ctypes
import time
from pathlib import Path
import numpy as np
from optimize import rotate

library = ctypes.CDLL(str(Path(__file__).with_name('polish.so')))
pointer = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
library.polish.argtypes = [ctypes.c_int, ctypes.c_int, pointer, pointer, pointer, pointer, ctypes.c_int, ctypes.c_int, ctypes.c_double]
library.polish.restype = ctypes.c_double


def polish(one_body, factors, orbital, auxiliary, sweeps=10, orbital_enabled=True, deadline=None):
    rotated_body, rotated_factors = rotate(one_body, factors, orbital, auxiliary)
    rotated_body = np.ascontiguousarray(rotated_body)
    rotated_factors = np.ascontiguousarray(rotated_factors)
    orbital = orbital.copy(order='C')
    auxiliary = auxiliary.copy(order='C')
    seconds = 1000000.0 if deadline is None else max(0.0, deadline - time.monotonic())
    value = library.polish(len(one_body), len(factors), rotated_body, rotated_factors, orbital, auxiliary, sweeps, orbital_enabled, seconds)
    return value, orbital, auxiliary
