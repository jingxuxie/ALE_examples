import ctypes
import os
from pathlib import Path
import numpy as np

_grouped = bool(int(os.getenv('GROUP', '0')))
_temporal = bool(int(os.getenv('TEMPORAL', '0')))
_rawgroup = bool(int(os.getenv('RAWGROUP', '0')))
_grouped = _grouped or _temporal or _rawgroup
_native = ctypes.CDLL(str(Path(__file__).with_name(os.getenv('NATIVE', 'group.so' if _grouped else 'decoder.so'))))
_ptr = ctypes.c_void_p
_native.create.argtypes = [ctypes.c_int, ctypes.c_int, _ptr, _ptr, _ptr]
_native.create.restype = _ptr
if _grouped:
    _native.create.argtypes += [ctypes.c_int, _ptr]
if _temporal:
    _native.create.argtypes += [ctypes.c_int]
_native.destroy.argtypes = [_ptr]
_native.run.argtypes = [_ptr, ctypes.c_int, _ptr, _ptr, ctypes.c_int, ctypes.c_int, ctypes.c_int]


class Decoder:
    def __init__(self, model):
        self.matcher = None
        if int(os.getenv('SEEDMATCH', '0')):
            import stim
            import pymatching
            self.match_selected = np.arange(model['num_mechanisms'])
            matrix = model['detector_matrix']
            mapping = {}
            for var in np.flatnonzero(np.isin(model['mechanism_kind'], ['X', 'Z', 'readout'])):
                mapping[tuple(np.flatnonzero(matrix[:, var]))] = int(var)
            lines = []
            for line in model['dem_text'].splitlines():
                if line.startswith('error('):
                    prefix, suffix = line.split(')', 1)
                    pieces = []
                    for piece in suffix.split('^'):
                        detectors = sorted(int(token[1:]) for token in piece.split() if token.startswith('D'))
                        var = mapping[tuple(detectors)]
                        pieces.append(' '.join([f'D{detector}' for detector in detectors] + [f'L{var}']))
                    lines.append(prefix + ') ' + ' ^ '.join(pieces))
                elif not line.startswith('logical_observable'):
                    lines.append(line)
            lines.append(f'logical_observable L{model["num_mechanisms"]-1}')
            self.matcher = pymatching.Matching.from_detector_error_model(stim.DetectorErrorModel('\n'.join(lines)), enable_correlations=True)
        self.trials = int(os.getenv('TRIALS', '2' if model['rounds'] > 1 else '8'))
        self.iterations = int(os.getenv('ITERATIONS', '40'))
        self.order = int(os.getenv('ORDER', '40'))
        matrix = np.ascontiguousarray(model['detector_matrix'], dtype=np.uint8)
        logical = np.ascontiguousarray(model['observable_matrix'], dtype=np.uint8)
        probabilities = np.ascontiguousarray(model['probabilities'], dtype=np.float64)
        if int(os.getenv('MERGE', '0')):
            keys = np.packbits(np.vstack([matrix, logical]), axis=0).T.copy()
            _, selected, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
            merged = np.ones(len(selected))
            np.multiply.at(merged, inverse, 1 - 2 * probabilities)
            probabilities = (1 - merged) / 2
            order = np.argsort(selected)
            merge_map = np.ascontiguousarray(np.argsort(order)[inverse], dtype=np.int32)
            selected = selected[order]
            if self.matcher is not None:
                self.match_selected = selected
            probabilities = probabilities[order]
            matrix = np.ascontiguousarray(matrix[:, selected])
            logical = np.ascontiguousarray(logical[:, selected])
            kinds = model['mechanism_kind'][selected]
        else:
            kinds = model['mechanism_kind']
        extra = []
        if _temporal:
            rounds = int(model['rounds'])
            width = 2 * rounds
            count = 2 * int(model['distance']) ** 2
            first = np.flatnonzero(kinds == 'X').reshape(rounds, count).T
            second = np.flatnonzero(kinds == 'Z').reshape(rounds, count).T
            third = np.flatnonzero(kinds == 'Y').reshape(rounds, count).T
            burst = np.flatnonzero(kinds == 'YY_time').reshape(rounds - 1, count).T
            selected = np.stack([first, second], axis=2).reshape(-1)
            others = np.flatnonzero(~np.isin(kinds, ['X', 'Z', 'Y', 'YY_time']))
            selected = np.r_[selected, others]
            joint = np.zeros((count, 1 << width))
            joint[:, 0] = 1
            states = np.arange(1 << width)
            for time in range(rounds):
                mechanisms = [(first[:, time], 1 << (2*time)), (second[:, time], 2 << (2*time)),
                              (third[:, time], 3 << (2*time))]
                if time < rounds - 1:
                    mechanisms.append((burst[:, time], 15 << (2*time)))
                for indices, mask in mechanisms:
                    rate = probabilities[indices, None]
                    joint = joint * (1-rate) + joint[:, states ^ mask] * rate
            costs = np.ascontiguousarray(-np.log(joint / joint[:, :1]), dtype=np.float32)
            probabilities = probabilities[selected].copy()
            for bit in range(width):
                probabilities[bit:count*width:width] = joint[:, (states & (1 << bit)) != 0].sum(axis=1)
            matrix = np.ascontiguousarray(matrix[:, selected])
            logical = np.ascontiguousarray(logical[:, selected])
            extra = [count, costs.ctypes.data, width]
        elif _grouped:
            first = np.flatnonzero(kinds == 'X')
            second = np.flatnonzero(kinds == 'Z')
            third = np.flatnonzero(kinds == 'Y')
            selected = np.ravel(np.column_stack([first, second, third] if _rawgroup else [first, second]))
            others = np.flatnonzero(~np.isin(kinds, ['X', 'Z', 'Y']))
            selected = np.r_[selected, others]
            matrix = np.ascontiguousarray(matrix[:, selected])
            logical = np.ascontiguousarray(logical[:, selected])
            joint = np.zeros((len(first), 4))
            for state in range(8):
                factors = [probabilities[indices] if state & (1 << bit) else 1 - probabilities[indices]
                           for bit, indices in enumerate([first, second, third])]
                effect = (state & 3) ^ (3 if state & 4 else 0)
                joint[:, effect] += factors[0] * factors[1] * factors[2]
            costs = np.ascontiguousarray(-np.log(joint / joint[:, :1]), dtype=np.float32)
            probabilities = probabilities[selected].copy()
            if not _rawgroup:
                probabilities[:len(first)*2:2] = joint[:, 1] + joint[:, 3]
                probabilities[1:len(first)*2:2] = joint[:, 2] + joint[:, 3]
            extra = [len(first), costs.ctypes.data]
        self.handle = _native.create(*matrix.shape, matrix.ctypes.data, logical.ctypes.data, probabilities.ctypes.data, *extra)
        if os.getenv('REGION') and model['rounds'] == 1:
            coordinates = model['detector_coordinates']
            region = np.flatnonzero(~np.any(matrix[coordinates[:,0] > 1],axis=0))
            region = np.ascontiguousarray(sorted(region,key=lambda var: max(coordinates[np.flatnonzero(matrix[:,var]),1])),dtype=np.int32)
            _native.set_region.argtypes = [_ptr, ctypes.c_int, _ptr]
            _native.set_region(self.handle,len(region),region.ctypes.data)
        if os.getenv('FEATURES'):
            names = ['X', 'Z', 'Y', 'XX', 'ZZ', 'YY_time', 'readout']
            kind_ids = np.ascontiguousarray([names.index(kind) for kind in kinds], dtype=np.int32)
            _native.set_kinds.argtypes = [_ptr, _ptr]
            _native.set_kinds(self.handle, kind_ids.ctypes.data)
        self.alt_handle = None
        if int(os.getenv('HYBRID', '0')):
            original_matrix = np.ascontiguousarray(model['detector_matrix'], dtype=np.uint8)
            original_logical = np.ascontiguousarray(model['observable_matrix'], dtype=np.uint8)
            original_probabilities = np.ascontiguousarray(model['probabilities'], dtype=np.float64)
            self.alt_handle = _native.create(*original_matrix.shape, original_matrix.ctypes.data, original_logical.ctypes.data, original_probabilities.ctypes.data)
            _native.attach.argtypes = [_ptr, _ptr, _ptr]
            _native.attach(self.handle, self.alt_handle, merge_map.ctypes.data)

    def __del__(self):
        if getattr(self, 'handle', None):
            _native.destroy(self.handle)
            self.handle = None
        if getattr(self, 'alt_handle', None):
            _native.destroy(self.alt_handle)
            self.alt_handle = None

    def decode(self, syndromes):
        syndromes = np.ascontiguousarray(syndromes, dtype=np.uint8)
        output = np.empty((len(syndromes), 4), dtype=np.uint8)
        if self.matcher is not None:
            seeds = np.ascontiguousarray(self.matcher.decode_batch(syndromes, enable_correlations=True)[:, self.match_selected])
            _native.run_seed.argtypes = [_ptr, ctypes.c_int, _ptr, _ptr, _ptr, _ptr, ctypes.c_int, ctypes.c_int, ctypes.c_int]
            _native.run_seed(self.handle, len(syndromes), syndromes.ctypes.data, seeds.ctypes.data, output.ctypes.data, None,
                             self.iterations, self.order, self.trials)
            return output
        _native.run(self.handle, len(syndromes), syndromes.ctypes.data, output.ctypes.data,
                    self.iterations, self.order, self.trials)
        return output
