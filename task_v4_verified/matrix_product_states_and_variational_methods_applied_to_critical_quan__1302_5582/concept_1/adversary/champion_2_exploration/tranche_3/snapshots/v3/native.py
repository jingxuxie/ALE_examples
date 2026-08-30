import ctypes
from pathlib import Path
import numpy as np

_library = ctypes.CDLL(str(Path(__file__).with_name('local_solver.so')))
_pointer = ctypes.c_void_p
_integer_pointer = ctypes.c_void_p
_function = _library.local_lowest
_function.restype = ctypes.c_double
_function.argtypes = ([ctypes.c_int]*3 + [_pointer]*4 + [ctypes.c_double]*2
                     + [_integer_pointer, ctypes.c_int] + [_pointer]*2
                     + [ctypes.c_double, ctypes.c_int, ctypes.c_double,
                        ctypes.c_double, _pointer, ctypes.POINTER(ctypes.c_int)])


def lowest(left, dimension, right, full_diagonal, position, left_position,
           right_position, left_coupling, right_coupling, allowed, diagonal,
           start, tolerance, max_steps, clock):
    arrays = [np.ascontiguousarray(array) for array in
              (full_diagonal, position, left_position, right_position, diagonal, start)]
    pointers = [array.ctypes.data for array in arrays]
    indices = None if allowed is None else allowed.ctypes.data
    output = np.empty_like(start)
    iterations = ctypes.c_int()
    energy = _function(left, dimension, right, *pointers[:4], left_coupling,
                       right_coupling, indices, len(start), *pointers[4:], tolerance,
                       max_steps, clock.cpu, clock.wall, output.ctypes.data,
                       ctypes.byref(iterations))
    if iterations.value < 0 or not np.isfinite(energy):
        raise ArithmeticError('Native local eigensolver failed')
    return output, energy
