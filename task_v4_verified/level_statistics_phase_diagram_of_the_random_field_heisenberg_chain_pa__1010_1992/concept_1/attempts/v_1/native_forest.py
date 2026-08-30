import ctypes
from pathlib import Path

import numpy as np
from numpy.ctypeslib import ndpointer


class Forest:
    def __init__(self):
        directory = Path(__file__).resolve().parent
        with np.load(directory / 'forest.npz', allow_pickle=False) as archive:
            self.roots = archive['roots']
            self.features = archive['features']
            self.thresholds = archive['thresholds']
            self.right_children = archive['right_children']
            self.values = archive['values']
        self.library = ctypes.CDLL(str(directory / 'forest.so'))
        self.function = self.library.forest_predict
        self.function.restype = None
        self.function.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                  ndpointer(np.float32, 2, flags='C_CONTIGUOUS'),
                                  ndpointer(np.int32, 1, flags='C_CONTIGUOUS'),
                                  ndpointer(np.int16, 1, flags='C_CONTIGUOUS'),
                                  ndpointer(np.float64, 1, flags='C_CONTIGUOUS'),
                                  ndpointer(np.int32, 1, flags='C_CONTIGUOUS'),
                                  ndpointer(np.float32, 1, flags='C_CONTIGUOUS'),
                                  ndpointer(np.float64, 1, flags='C_CONTIGUOUS'),
                                  ndpointer(np.float64, 1, flags='C_CONTIGUOUS')]

    def predict(self, features):
        features = np.ascontiguousarray(features, dtype=np.float32)
        means = np.empty(len(features), dtype=np.float64)
        deviations = np.empty_like(means)
        self.function(len(features), features.shape[1], len(self.roots), features,
                      self.roots, self.features, self.thresholds, self.right_children,
                      self.values, means, deviations)
        return np.clip(means, 0.0, 1.0), deviations
