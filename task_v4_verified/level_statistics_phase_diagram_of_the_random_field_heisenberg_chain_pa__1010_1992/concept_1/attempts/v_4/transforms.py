import numpy as np
from scipy.special import ndtri
import ctypes
import functools
from pathlib import Path


LIBRARY = ctypes.CDLL(str(Path(__file__).with_name('fast_transform.so')))
LIBRARY.quantile_transform.argtypes = [ctypes.c_void_p] * 4 + [ctypes.c_size_t] * 3
LIBRARY.quantile_transform.restype = None


class QuantileMap:
    def __init__(self, quantiles, references):
        self.quantiles_ = quantiles
        self.references_ = references


@functools.lru_cache(maxsize=8)
def prepare(transformer):
    return np.ascontiguousarray(transformer.quantiles_.T, dtype=np.float64), np.ascontiguousarray(transformer.references_, dtype=np.float64)


def transform(transformer, values):
    knots, references = prepare(transformer)
    values = np.ascontiguousarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != knots.shape[0]:
        raise ValueError('Descriptor count does not match the fitted quantiles')
    output = np.empty(values.shape)
    LIBRARY.quantile_transform(values.ctypes.data, knots.ctypes.data, references.ctypes.data,
                               output.ctypes.data, values.shape[0], values.shape[1], len(references))
    return np.clip(ndtri(output), -3, 3)
