import json
import os
from collections import Counter

import numpy as np


def anf(table, width):
    coefficients = np.array(table, dtype=np.uint64)
    for bit in range(width):
        blocks = coefficients.reshape(-1, 2, 1 << bit)
        blocks[:, 1, :] ^= blocks[:, 0, :]
    return coefficients


def basis(vectors):
    pivots = {}
    for vector in vectors:
        while vector:
            pivot = vector.bit_length() - 1
            if pivot in pivots:
                vector ^= pivots[pivot]
            else:
                pivots[pivot] = vector
                break
    return pivots


def columns(values, width):
    return [int.from_bytes(np.packbits((values >> bit & 1).astype(np.uint8), bitorder='little').tobytes(), 'little') for bit in range(width)]


if __name__ == '__main__':
    suite = json.load(open(os.environ['PART'] + '/input/suite.json'))
    for instance in suite['instances']:
        width, count = instance['n'], instance['m']
        coefficients = anf(instance['table'], width)
        weights = np.array([mask.bit_count() for mask in range(1 << width)])
        print('\n', instance['id'])
        for degree in range(width, -1, -1):
            selected = coefficients[weights == degree]
            print(degree, 'monomials', np.count_nonzero(selected), 'output rank', len(basis(map(int, selected))))
        degrees = Counter()
        for combination in range(1, 1 << count):
            degrees[max(weights[index] for index, coefficient in enumerate(coefficients) if (int(coefficient) & combination).bit_count() % 2)] += 1
        print('combination degrees', degrees)
