import ctypes
import os
from pathlib import Path
import numpy as np

_ptr = ctypes.c_void_p
_original = ctypes.CDLL(str(Path(__file__).with_name('solver_next.so')))
_original.create.argtypes = [ctypes.c_int, ctypes.c_int, _ptr, _ptr, _ptr]
_original.create.restype = _ptr
_original.destroy.argtypes = [_ptr]
_original.run_info.argtypes = [_ptr, ctypes.c_int, _ptr, _ptr, _ptr, ctypes.c_int, ctypes.c_int, ctypes.c_int]
_grouped = ctypes.CDLL(str(Path(__file__).with_name('pauli_next.so')))
_grouped.create_group.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, _ptr, _ptr, _ptr, _ptr, _ptr, ctypes.c_int]
_grouped.create_group.restype = _ptr
_grouped.destroy_group.argtypes = [_ptr]
_grouped.set_group_gap.argtypes = [_ptr, ctypes.c_float]
_grouped.run_group.argtypes = [_ptr, ctypes.c_int, _ptr, _ptr, _ptr, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]

class Decoder:
    def __init__(self, model):
        matrix = np.ascontiguousarray(model['detector_matrix'], dtype=np.uint8)
        logical = np.ascontiguousarray(model['observable_matrix'], dtype=np.uint8)
        probabilities = np.ascontiguousarray(model['probabilities'], dtype=np.float64)
        self.original = _original.create(*matrix.shape, matrix.ctypes.data, logical.ctypes.data, probabilities.ctypes.data)
        kinds = model['mechanism_kind']
        columns = []
        physical_columns = []
        groups = []
        weights = []
        basis = int(os.getenv('FINAL_BASIS', 2))
        for index, kind in enumerate(kinds):
            if kind == 'X':
                px, pz, py = probabilities[index:index + 3]
                distribution = np.zeros(4)
                for state in range(8):
                    probability = (px if state & 1 else 1-px) * (pz if state & 2 else 1-pz) * (py if state & 4 else 1-py)
                    distribution[(state & 3) ^ (3 if state & 4 else 0)] += probability
                groups.extend([len(weights), len(weights)])
                physical_columns.extend([index, index + 1])
                columns.extend([index + (1 if basis == 1 else 0), index + 2])
                weights.append(np.log(distribution[0] / distribution))
            elif kind not in ('Z', 'Y'):
                groups.append(len(weights))
                columns.append(index)
                physical_columns.append(index)
                weights.append([0, np.log((1-probabilities[index])/probabilities[index]), 0, 0])
        reduced = np.ascontiguousarray(matrix[:, columns])
        physical = np.ascontiguousarray(matrix[:, physical_columns])
        reduced_logical = np.ascontiguousarray(logical[:, columns])
        weights = np.ascontiguousarray(weights, dtype=np.float32)
        groups = np.ascontiguousarray(groups, dtype=np.int32)
        self.grouped = _grouped.create_group(*reduced.shape, len(weights), reduced.ctypes.data, physical.ctypes.data, reduced_logical.ctypes.data, weights.ctypes.data, groups.ctypes.data, basis)
        _grouped.set_group_gap(self.grouped, float(os.getenv('FINAL_GGAP',os.getenv('GAP',4))))
        self.original_trials = int(os.getenv('FINAL_ORIGINAL', 16))
        self.grouped_trials = int(os.getenv('FINAL_GROUPED', 8))

    def __del__(self):
        if getattr(self, 'original', None):
            _original.destroy(self.original)
            self.original = None
        if getattr(self, 'grouped', None):
            _grouped.destroy_group(self.grouped)
            self.grouped = None

    def decode(self, syndromes):
        syndromes = np.ascontiguousarray(syndromes, dtype=np.uint8)
        output = np.empty((len(syndromes), 4), dtype=np.uint8)
        original_scores = np.empty((len(syndromes), 16), dtype=np.float32)
        grouped_scores = np.empty_like(original_scores)
        iterations = int(os.getenv('FINAL_ITER',40))
        order = int(os.getenv('FINAL_ORDER',40))
        _original.run_info(self.original, len(syndromes), syndromes.ctypes.data, output.ctypes.data, original_scores.ctypes.data, iterations, order, self.original_trials)
        _grouped.run_group(self.grouped, len(syndromes), syndromes.ctypes.data, output.ctypes.data, grouped_scores.ctypes.data, int(os.getenv('FINAL_GITER',iterations)), order, self.grouped_trials, 1)
        self.scores = np.minimum(original_scores, grouped_scores + float(os.getenv('FINAL_OFFSET', 0)))
        labels = self.scores.argmin(axis=1)
        return ((labels[:, None] >> np.arange(4)) & 1).astype(np.uint8)
