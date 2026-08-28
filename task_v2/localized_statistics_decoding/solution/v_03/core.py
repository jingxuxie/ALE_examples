from pathlib import Path
import sys
import types

import numpy as np


package = types.ModuleType('ldpc')
package.__path__ = [str(Path(__file__).with_name('vendor') / 'ldpc')]
sys.modules['ldpc'] = package
from ldpc.bposd_decoder import BpOsdDecoder


def legacy_correction(matrix, syndrome, reliability):
    columns = [sum(1 << int(row) for row in np.flatnonzero(matrix[:, column]))
               for column in range(matrix.shape[1])]
    basis = {}
    for column in np.argsort(reliability, kind='stable'):
        column = int(column)
        vector = columns[column]
        combination = 1 << column
        while vector:
            pivot = vector.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = vector, combination
                break
            vector ^= basis[pivot][0]
            combination ^= basis[pivot][1]
    target = sum(int(bit) << row for row, bit in enumerate(syndrome))
    correction = 0
    while target:
        pivot = target.bit_length() - 1
        vector, combination = basis[pivot]
        target ^= vector
        correction ^= combination
    return np.asarray([(correction >> column) & 1 for column in range(matrix.shape[1])], dtype=np.uint8)


def make_decoders(matrix, priors):
    configurations = [('minimum_sum', 0.625, 'parallel'), ('minimum_sum', 0.75, 'serial'),
                      ('product_sum', 1.0, 'parallel'), ('minimum_sum', 0.5, 'serial')]
    return [BpOsdDecoder(matrix, error_channel=priors.tolist(), max_iter=100,
                         bp_method=method, ms_scaling_factor=scale, schedule=schedule,
                         osd_method='OSD_CS', osd_order=50, omp_thread_count=1)
            for method, scale, schedule in configurations]


def recover(matrix, syndrome, priors, reliability, decoders):
    candidates = [legacy_correction(matrix, syndrome, reliability)]
    candidates.extend(np.asarray(decoder.decode(syndrome), dtype=np.uint8).copy() for decoder in decoders)
    weights = np.log((1 - priors) / priors)
    valid = [candidate for candidate in candidates if np.array_equal((matrix @ candidate) % 2, syndrome)]
    if not valid:
        raise ValueError('No syndrome-consistent candidate')
    return min(valid, key=lambda candidate: float(weights @ candidate))
