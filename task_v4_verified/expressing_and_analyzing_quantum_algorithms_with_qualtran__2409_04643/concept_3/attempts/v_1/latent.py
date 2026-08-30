import itertools
import json
import os

import numpy as np

from spectra import walsh
from analyze import anf


def majority_decode(labels, width, degree):
    rows = len(labels)
    addresses = np.arange(rows)
    residual = labels.copy()
    result = np.zeros(rows, dtype=np.uint8)
    for current_degree in range(degree, -1, -1):
        updates = np.zeros(rows, dtype=np.uint8)
        for subset in itertools.combinations(range(width), current_degree):
            mask = sum(1 << bit for bit in subset)
            derivative = residual.copy()
            for bit in subset:
                derivative ^= derivative[addresses ^ (1 << bit)]
            coefficient = derivative.sum() > rows // 2
            if coefficient:
                monomial = ((addresses & mask) == mask).astype(np.uint8)
                updates ^= monomial
        result ^= updates
        residual ^= updates
    return result


if __name__ == '__main__':
    suite = json.load(open(os.environ['PART'] + '/input/suite.json'))
    for instance in suite['instances'][:3]:
        width, count = instance['n'], instance['m']
        table = np.array(instance['table'])
        parity = np.array([value.bit_count() % 2 for value in range(1 << width)])
        outputs = []
        print(instance['id'], flush=True)
        for bit in range(count):
            values = table >> bit & 1
            spectrum = walsh(1 - 2 * values)
            candidates = [mask for mask in range(1 << width) if mask.bit_count() == 3]
            mask = max(candidates, key=lambda candidate: spectrum[candidate])
            outputs.append(values ^ parity[np.arange(1 << width) & mask])
            print('output', bit, 'affine', mask, 'bias', spectrum[mask], flush=True)
        outputs = np.array(outputs, dtype=np.uint8)
        weights = outputs.sum(axis=0)
        print('distribution', np.bincount(weights.astype(np.int64)), flush=True)
        labels = (weights > (count + 1) / 2).astype(np.uint8)
        for degree in range(1, 5):
            decoded = majority_decode(labels, width, degree)
            print('degree', degree, 'error', np.mean(decoded != labels), 'weight', decoded.sum(), 'disagreement', (outputs ^ decoded).sum(axis=1), flush=True)
