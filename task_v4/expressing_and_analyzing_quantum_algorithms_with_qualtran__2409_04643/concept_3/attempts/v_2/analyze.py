import json
import os
from collections import Counter
import numpy as np

SUITE = json.load(open(os.environ['ROOT'] + '/input/suite.json'))['instances']

def rank(vectors):
    pivots = {}
    for vector in vectors:
        while vector:
            pivot = vector.bit_length() - 1
            if pivot in pivots:
                vector ^= pivots[pivot]
            else:
                pivots[pivot] = vector
                break
    return len(pivots)

def anf(table):
    result = np.array(table, dtype=np.int64).copy()
    for bit in range(len(result).bit_length() - 1):
        view = result.reshape(-1, 2, 1 << bit)
        view[:, 1, :] ^= view[:, 0, :]
    return result

if __name__ == '__main__':
    for inst in SUITE:
        width, outputs = inst['n'], inst['m']
        table = np.array(inst['table'])
        coeff = anf(table)
        degrees = np.array([mask.bit_count() for mask in range(1 << width)])
        print(inst['id'], flush=True)
        print('degree tail ranks:', [(degree, rank(map(int, coeff[degrees >= degree]))) for degree in range(1, width + 1)])
        combo_degrees = []
        for combo in range(1, 1 << outputs):
            terms = np.array([int(coef & combo).bit_count() % 2 for coef in coeff])
            combo_degrees.append(int(max(degrees[terms > 0], default=0)))
        print('combo degrees', Counter(combo_degrees), sorted(enumerate(combo_degrees, 1), key=lambda pair: pair[1])[:16])
        diff_degrees = []
        diff_ranks = []
        addresses = np.arange(1 << width)
        for direction in range(1, 1 << width):
            derivative = table ^ table[addresses ^ direction]
            diff_ranks.append(rank(map(int, derivative ^ derivative[0])))
            derivative_coeff = anf(derivative)
            diff_degrees.append(int(max(degrees[derivative_coeff != 0], default=0)))
        print('derivative degrees', Counter(diff_degrees), 'ranks', Counter(diff_ranks))
        print('lowest derivatives', sorted(zip(range(1, 1 << width), diff_degrees, diff_ranks), key=lambda item: (item[1], item[2]))[:32], flush=True)
