import ctypes
import numpy as np
import solution_v2 as base
from solution_v2 import contiguous

LIB = ctypes.CDLL(str(base.ROOT / 'kernel_new.so'))
LIB.conditional.argtypes = [ctypes.c_int] * 4 + [base.INTEGER] * 3 + [base.DOUBLE] * 6
LIB.conditional.restype = ctypes.c_double


class Model(base.Model):
    def make_conditional(self, codes, actions, weight):
        local = sum(1 << int(detector) for detector in np.flatnonzero(codes))
        touching = self.unions[(self.unions & local) != 0]
        blocked = int(np.bitwise_or.reduce(touching))
        remote_detectors = np.array([detector for detector in range(self.dimension) if not ((blocked >> detector) & 1)], dtype=int)
        if len(remote_detectors) == 0:
            return self.make_block(codes, actions, weight)
        remote_codes = np.zeros(self.dimension, dtype=np.int32)
        if len(remote_detectors) <= 12:
            remote_codes[remote_detectors] = 1 << np.arange(len(remote_detectors), dtype=np.int32)
        else:
            remote_codes[remote_detectors] = self.hash_codes[remote_detectors] & 4095
        local_masks = self.project(self.masks, codes)
        remote_masks = self.project(self.masks, remote_codes)
        assert not np.any(np.any(local_masks, axis=1) & np.any(remote_masks, axis=1))
        masks = np.concatenate((local_masks, remote_masks), axis=1)
        active = np.flatnonzero(np.any(masks, axis=1))
        local_size = 1 << int(max(codes)).bit_length()
        remote_size = 1 << int(max(remote_codes)).bit_length()
        observations, counts, offsets = [], [], [0]
        for action in actions:
            packed, weights = [], []
            for syndromes, multiplicities in self.raw[action]:
                first = self.project(syndromes, codes)
                second = self.project(syndromes, remote_codes)
                packed.append(first.astype(np.int64) * remote_size + second)
                weights.append(multiplicities)
            packed = np.concatenate(packed)
            weights = np.concatenate(weights)
            unique, inverse = np.unique(packed, return_inverse=True)
            counts.append(np.bincount(inverse, weights=weights))
            observations.append(np.stack((unique // remote_size, unique % remote_size), axis=1))
            offsets.append(offsets[-1] + len(unique))
        return (local_size, remote_size, active, contiguous(masks[active], np.int32),
                contiguous(self.exposures[actions][:, :, active]), contiguous(self.weights[actions]),
                contiguous(self.alternate[actions][:, active]), contiguous(offsets, np.int32),
                contiguous(np.concatenate(observations), np.int32), contiguous(np.concatenate(counts)), weight)

    def setup(self, width=10, hashbits=14):
        if width < 10:
            return super().setup(width, hashbits)
        blocks = self.blocks(width)
        weight = self.dimension / (width * len(blocks))
        general = self.general_actions[self.spent[self.general_actions] > 0]
        rare = self.rare_actions[self.spent[self.rare_actions] > 0]
        result = [self.make_conditional(codes, general, weight) for codes in blocks] if len(general) else []
        if len(rare):
            result.append(self.make_block(self.hash_codes & ((1 << hashbits) - 1), rare))
        return result

    def evaluate(self, point, setup):
        gradient = np.zeros(self.channels)
        value = 0.0
        rates = np.exp(point)
        for block in setup:
            if len(block) == 8:
                part_value, part_gradient = super().evaluate(point, [block])
                value += part_value
                gradient += part_gradient
            else:
                local_size, remote_size, active, masks, exposures, weights, alternate, offsets, observations, counts, weight = block
                partial = np.zeros(len(active))
                value += weight * LIB.conditional(local_size, remote_size, len(active), len(weights), masks,
                                                  offsets, observations, exposures, weights, alternate,
                                                  contiguous(rates[active]), counts, partial)
                gradient[active] += weight * partial
        return value, gradient


base.Model = Model
calibrate = base.calibrate
main = base.main
if __name__ == '__main__':
    main()
