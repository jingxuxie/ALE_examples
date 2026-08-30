import ctypes
from pathlib import Path
import numpy as np

LIBRARY = ctypes.CDLL(str(Path(__file__).with_name('libnative_features.so')))
LIBRARY.feature_batch.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
LIBRARY.feature_batch.restype = ctypes.c_int


def describe_cases(cases, spectral=True):
    values = np.ascontiguousarray([case['fields'] for case in cases], dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 14:
        raise ValueError('Expected fourteen ordered fields per case')
    output = np.empty((len(cases), 889))
    status = LIBRARY.feature_batch(values.ctypes.data, output.ctypes.data, len(cases), int(spectral))
    if status:
        raise RuntimeError(f'Unexpected descriptor count: {status}')
    return output
