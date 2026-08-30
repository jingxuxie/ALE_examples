import ctypes
import os
from pathlib import Path
import numpy as np


def capsule_pointer(capsule):
    name_function = ctypes.pythonapi.PyCapsule_GetName
    name_function.argtypes = [ctypes.py_object]
    name_function.restype = ctypes.c_char_p
    pointer_function = ctypes.pythonapi.PyCapsule_GetPointer
    pointer_function.argtypes = [ctypes.py_object, ctypes.c_char_p]
    pointer_function.restype = ctypes.c_void_p
    return pointer_function(capsule, name_function(capsule))


library = None
if not os.environ.get('MPS_PYTHON_ONLY'):
    try:
        import scipy.linalg.cython_blas as blas
        import scipy.linalg.cython_lapack as lapack
        library = ctypes.CDLL(str(Path(__file__).with_name('native_core.so')))
        double_pointer = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        library.site_lowest.argtypes = [ctypes.c_int]*3 + [double_pointer]*4 + [ctypes.c_double]*2 + [double_pointer, ctypes.c_double, ctypes.c_int, double_pointer, ctypes.c_void_p, ctypes.c_void_p]
        library.site_lowest.restype = ctypes.c_double
        gemm_pointer = capsule_pointer(blas.__pyx_capi__['dgemm'])
        syev_pointer = capsule_pointer(lapack.__pyx_capi__['dsyev'])
    except (OSError, ImportError, AttributeError, KeyError, ValueError):
        library = None


def lowest_site(diagonal, tensor, left_position, position, right_position,
                left_coupling, right_coupling, tolerance, steps):
    if library is None:
        from fast import lowest, physical_action
        left, dimension, right = tensor.shape
        def matvec(vector):
            current = vector.reshape(tensor.shape)
            position_tensor = physical_action(position, current)
            image = diagonal.reshape(tensor.shape)*current
            image -= left_coupling*(left_position @ position_tensor.reshape(left, dimension*right)).reshape(tensor.shape)
            image -= right_coupling*(position_tensor.reshape(left*dimension, right) @ right_position).reshape(tensor.shape)
            return image.ravel()
        class LocalClock:
            def remaining(self):
                return 1.0
        return lowest(matvec, diagonal, tensor.ravel(), tolerance, steps, LocalClock())
    tensor = np.ascontiguousarray(tensor)
    output = np.empty(tensor.size)
    energy = library.site_lowest(*tensor.shape, np.ascontiguousarray(diagonal),
        np.ascontiguousarray(left_position), np.ascontiguousarray(position),
        np.ascontiguousarray(right_position), left_coupling, right_coupling,
        tensor, tolerance, steps, output, gemm_pointer, syev_pointer)
    if not np.isfinite(energy):
        raise ArithmeticError('Native local eigensolver failed')
    return output, energy
