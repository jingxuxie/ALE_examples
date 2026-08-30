import ctypes
from pathlib import Path
import numpy as np
import os

_native = ctypes.CDLL(str(Path(__file__).with_name('libneighbors.so')))
_ptr = ctypes.c_void_p
_native.create.argtypes = [ctypes.c_int, ctypes.c_int, _ptr, _ptr, _ptr]
_native.create.restype = _ptr
_native.destroy.argtypes = [_ptr]
_native.run_info.argtypes = [_ptr, ctypes.c_int, _ptr, _ptr, _ptr, ctypes.c_int, ctypes.c_int, ctypes.c_int]

class Decoder:
    def __init__(self, model):
        self.trials = int(os.getenv('TRIALS', 2 if model['rounds'] > 1 else 8))
        matrix = np.ascontiguousarray(model['detector_matrix'], dtype=np.uint8)
        logical = np.ascontiguousarray(model['observable_matrix'], dtype=np.uint8)
        probabilities = np.ascontiguousarray(model['probabilities'], dtype=np.float64)
        self.handle = _native.create(*matrix.shape, matrix.ctypes.data, logical.ctypes.data, probabilities.ctypes.data)
    def __del__(self):
        if getattr(self, 'handle', None):
            _native.destroy(self.handle)
    def decode(self, syndromes):
        syndromes = np.ascontiguousarray(syndromes, dtype=np.uint8)
        output = np.empty((len(syndromes), 4), dtype=np.uint8)
        self.scores = np.empty((len(syndromes),5,16),dtype=np.float32)
        _native.run_info(self.handle,len(syndromes),syndromes.ctypes.data,output.ctypes.data,self.scores.ctypes.data,int(os.getenv('ITER',40)),int(os.getenv('ORDER',40)),self.trials)
        return output
