import ctypes
from pathlib import Path

import numpy as np
import pymatching


class Decoder:
    def __init__(self, model):
        self.model = model
        self.checks = model.num_detectors
        self.baseline = pymatching.Matching.from_detector_error_model(model, enable_correlations=True)
        errors = {}
        for instruction in model.flattened():
            if instruction.type != 'error':
                continue
            probability = instruction.args_copy()[0]
            detectors = set()
            logical = 0
            for target in instruction.targets_copy():
                if target.is_relative_detector_id():
                    detectors.symmetric_difference_update([target.val])
                elif target.is_logical_observable_id():
                    logical ^= 1
            key = (tuple(sorted(detectors)), logical)
            if key in errors:
                previous = errors[key]
                errors[key] = previous + probability - 2 * previous * probability
            else:
                errors[key] = probability
        self.detectors = [key[0] for key in errors]
        self.logical = np.array([key[1] for key in errors], dtype=np.uint8)
        self.probability = np.array(list(errors.values()))
        self.prior = np.log((1 - self.probability) / self.probability)
        self.variables = len(errors)
        adjacent = [[] for _ in range(self.checks)]
        for variable, detectors in enumerate(self.detectors):
            for detector in detectors:
                adjacent[detector].append(variable)
        self.starts = np.array([0] + list(np.cumsum([len(row) for row in adjacent])), dtype=np.int32)
        self.neighbors = np.array([value for row in adjacent for value in row], dtype=np.int32)
        self.lib = ctypes.CDLL(str(Path(__file__).with_name('decoder_core.so')))
        self.lib.bp_fast.argtypes = (
            [ctypes.c_int] * 4 + [ctypes.c_void_p] * 4
            + [ctypes.c_int, ctypes.c_double, ctypes.c_double]
            + [ctypes.c_void_p] * 3 + [ctypes.c_int]
        )
        self.lib.bp_fast.restype = None
        self.lib.osd.argtypes = (
            [ctypes.c_int] * 3 + [ctypes.c_void_p] * 6
            + [ctypes.c_int] + [ctypes.c_void_p] * 2
        )
        self.lib.osd.restype = None

    def osd(self, syndromes, posterior, order_count=300):
        syndromes = np.ascontiguousarray(syndromes, dtype=np.uint8)
        posterior = np.ascontiguousarray(posterior, dtype=np.float64)
        minima = np.empty((len(syndromes), 2))
        evidence = np.empty_like(minima)
        self.lib.osd(len(syndromes), self.checks, self.variables,
                     self.starts.ctypes.data, self.neighbors.ctypes.data,
                     self.prior.ctypes.data, self.logical.ctypes.data,
                     syndromes.ctypes.data, posterior.ctypes.data, order_count,
                     minima.ctypes.data, evidence.ctypes.data)
        return minima, evidence

    def beliefs(self, syndromes, iterations=30, damping=0.0, scale=1.0, mode=0):
        syndromes = np.ascontiguousarray(syndromes, dtype=np.uint8)
        posterior = np.empty((len(syndromes), self.variables), dtype=np.float64)
        converged = np.empty(len(syndromes), dtype=np.uint8)
        used = np.empty(len(syndromes), dtype=np.int32)
        self.lib.bp_fast(len(syndromes), self.checks, self.variables, len(self.neighbors),
                         self.starts.ctypes.data, self.neighbors.ctypes.data, self.prior.ctypes.data,
                         syndromes.ctypes.data, iterations, damping, scale,
                         posterior.ctypes.data, converged.ctypes.data, used.ctypes.data, mode)
        return posterior, converged, used
