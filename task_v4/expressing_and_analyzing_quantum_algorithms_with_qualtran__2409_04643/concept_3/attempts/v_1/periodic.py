import json
import os

import numpy as np

from analyze import anf, basis
from spectra import walsh


def normalized(instance):
    width, count = instance['n'], instance['m']
    table = np.array(instance['table'])
    parity = np.array([value.bit_count() % 2 for value in range(1 << width)])
    outputs, masks = [], []
    for bit in range(count):
        values = table >> bit & 1
        spectrum = walsh(1 - 2 * values)
        candidates = [mask for mask in range(1 << width) if mask.bit_count() == 3]
        mask = max(candidates, key=lambda candidate: spectrum[candidate])
        masks.append(mask)
        outputs.append(values ^ parity[np.arange(1 << width) & mask])
    return np.array(outputs, dtype=np.int64), masks


if __name__ == '__main__':
    suite = json.load(open(os.environ['PART'] + '/input/suite.json'))
    for instance in suite['instances'][:3]:
        width, count = instance['n'], instance['m']
        outputs, masks = normalized(instance)
        weights = outputs.sum(axis=0)
        labels = 1 - 2 * (weights > (count + 1) / 2).astype(np.int64)
        correlations = walsh(walsh(labels) ** 2) // len(labels)
        best = np.argsort(correlations)[-65:][::-1]
        print(instance['id'], [(int(index), int(correlations[index])) for index in best[:35]], flush=True)
        for amount in (2, 4, 8, 16, 32):
            pivots = basis(map(int, best[1:amount]))
            print('top', amount, 'rank', len(pivots), flush=True)
        np.savez(instance['id'] + '_latent.npz', outputs=outputs, masks=masks, labels=labels, correlations=correlations)
