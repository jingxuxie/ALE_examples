import itertools
import json
import os
import time

from analyze import columns

import numpy as np


def kernel(vectors):
    pivots = {}
    dependencies = []
    for index, vector in enumerate(vectors):
        expression = 1 << index
        while vector:
            pivot = vector.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = vector, expression
                break
            other, other_expression = pivots[pivot]
            vector ^= other
            expression ^= other_expression
        if not vector:
            dependencies.append(expression)
    return dependencies


if __name__ == '__main__':
    suite = json.load(open(os.environ['PART'] + '/input/suite.json'))
    for instance in suite['instances']:
        started = time.time()
        width, count = instance['n'], instance['m']
        variables = columns(np.arange(1 << width, dtype=np.uint64), width) + columns(np.array(instance['table'], dtype=np.uint64), count)
        vectors, masks = [(1 << (1 << width)) - 1], [()]
        print(instance['id'], flush=True)
        for degree in range(1, 4):
            for subset in itertools.combinations(range(width + count), degree):
                value = vectors[0]
                for variable in subset:
                    value &= variables[variable]
                vectors.append(value)
                masks.append(subset)
            dependencies = kernel(vectors)
            print('degree', degree, 'columns', len(vectors), 'nullity', len(dependencies), 'seconds', round(time.time()-started, 2), flush=True)
            if len(dependencies) < 12:
                for dependency in dependencies:
                    print([masks[index] for index in range(len(masks)) if dependency >> index & 1], flush=True)
