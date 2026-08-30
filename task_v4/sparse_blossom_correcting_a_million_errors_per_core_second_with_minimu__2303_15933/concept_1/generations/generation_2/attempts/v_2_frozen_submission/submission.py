import ctypes
from pathlib import Path

import numpy as np


_native = ctypes.CDLL(str(Path(__file__).with_name('final.so')))
_pointer = ctypes.c_void_p
_native.create.argtypes = [ctypes.c_int, ctypes.c_int, _pointer, _pointer, _pointer]
_native.create.restype = _pointer
_native.destroy.argtypes = [_pointer]
_native.destroy.restype = None
_native.attach.argtypes = [_pointer, _pointer, _pointer]
_native.attach.restype = None
_native.set_entropy.argtypes = [_pointer, ctypes.c_float]
_native.set_entropy.restype = None
_native.run.argtypes = [_pointer, ctypes.c_int, _pointer, _pointer, ctypes.c_int, ctypes.c_int, ctypes.c_int]
_native.run.restype = None


class Decoder:
    def __init__(self, model):
        self.handle = None
        self.alternate = None
        matrix = np.ascontiguousarray(model['detector_matrix'], dtype=np.uint8)
        logical = np.ascontiguousarray(model['observable_matrix'], dtype=np.uint8)
        probabilities = np.ascontiguousarray(model['probabilities'], dtype=np.float64)
        keys = np.packbits(np.vstack([matrix, logical]), axis=0).T.copy()
        _, selected, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
        products = np.ones(len(selected), dtype=np.float64)
        np.multiply.at(products, inverse, 1 - 2 * probabilities)
        order = np.argsort(selected)
        mapping = np.ascontiguousarray(np.argsort(order)[inverse], dtype=np.int32)
        selected = selected[order]
        merged_probabilities = np.ascontiguousarray((1 - products[order]) / 2)
        merged_matrix = np.ascontiguousarray(matrix[:, selected])
        merged_logical = np.ascontiguousarray(logical[:, selected])
        self.handle = _native.create(*merged_matrix.shape, merged_matrix.ctypes.data,
                                     merged_logical.ctypes.data, merged_probabilities.ctypes.data)
        if model['profile'] != 'detector_support_strip':
            self.alternate = _native.create(*matrix.shape, matrix.ctypes.data,
                                            logical.ctypes.data, probabilities.ctypes.data)
            _native.attach(self.handle, self.alternate, mapping.ctypes.data)
        self.trials = 16
        if model['profile'] == 'detector_support_strip' and model['distance'] == 9:
            _native.set_entropy(self.handle, 1.5)

    def __del__(self):
        if getattr(self, 'handle', None):
            _native.destroy(self.handle)
            self.handle = None
        if getattr(self, 'alternate', None):
            _native.destroy(self.alternate)
            self.alternate = None

    def decode(self, syndromes):
        syndromes = np.ascontiguousarray(syndromes, dtype=np.uint8)
        output = np.empty((len(syndromes), 4), dtype=np.uint8)
        _native.run(self.handle, len(syndromes), syndromes.ctypes.data, output.ctypes.data,
                    40, 60, self.trials)
        return output
