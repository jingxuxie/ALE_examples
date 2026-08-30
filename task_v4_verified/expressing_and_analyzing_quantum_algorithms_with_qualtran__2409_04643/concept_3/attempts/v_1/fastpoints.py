import json
import os
from collections import Counter

import numpy as np

from analyze import anf
from relations import kernel


def fast_points(coefficients, width, combination):
    present = [mask for mask, coefficient in enumerate(coefficients) if (int(coefficient) & combination).bit_count() & 1]
    degree = max(mask.bit_count() for mask in present)
    highest = [mask for mask in present if mask.bit_count() == degree]
    derivatives = [0] * width
    for mask in highest:
        for bit in range(width):
            if mask >> bit & 1:
                derivatives[bit] ^= 1 << (mask ^ (1 << bit))
    return degree, kernel(derivatives)


if __name__ == '__main__':
    for instance in json.load(open(os.environ['PART'] + '/input/suite.json'))['instances']:
        coefficients = anf(instance['table'], instance['n'])
        records = []
        counts = Counter()
        for combination in range(1, 1 << instance['m']):
            degree, directions = fast_points(coefficients, instance['n'], combination)
            counts[degree, len(directions)] += 1
            if directions:
                records.append((combination, degree, directions))
        print(instance['id'], counts, 'fast', records[:35], flush=True)
