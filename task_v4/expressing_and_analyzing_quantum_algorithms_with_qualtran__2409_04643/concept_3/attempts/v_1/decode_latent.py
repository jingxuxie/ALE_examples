import json
import os
import sys
import time

import numpy as np

from latent import majority_decode
from periodic import normalized
from analyze import anf


def affine_permutation(width, generator):
    columns = [1 << bit for bit in range(width)]
    for repeat in range(width * 12):
        source, target = generator.choice(width, 2, replace=False)
        columns[target] ^= columns[source]
    permutation = np.full(1 << width, generator.integers(1 << width), dtype=np.int64)
    addresses = np.arange(1 << width)
    for bit, column in enumerate(columns):
        permutation ^= ((addresses >> bit & 1) * column)
    return permutation


if __name__ == '__main__':
    suite = json.load(open(os.environ['PART'] + '/input/suite.json'))
    generator = np.random.default_rng(5823)
    for instance in suite['instances'][:3]:
        outputs, masks = normalized(instance)
        width, count = instance['n'], instance['m']
        weights = outputs.sum(axis=0)
        labels = (weights > (count + 1) / 2).astype(np.uint8)
        best = int(weights.sum())
        started = time.time()
        print(instance['id'], 'zero cost', best, flush=True)
        for trial in range(250):
            permutation = affine_permutation(width, generator)
            for degree in ([2, 3] if width == 10 else [3, 4]):
                decoded_permuted = majority_decode(labels[permutation], width, degree)
                decoded = np.empty_like(decoded_permuted)
                decoded[permutation] = decoded_permuted
                cost = int((outputs ^ decoded).sum() + decoded.sum())
                if cost < best:
                    best = cost
                    print('trial', trial, 'degree', degree, 'cost', cost, 'error', np.mean(decoded != labels), 'time', time.time()-started, flush=True)
                    np.save(instance['id'] + '_decoded.npy', decoded)
        print('done', time.time()-started, flush=True)
