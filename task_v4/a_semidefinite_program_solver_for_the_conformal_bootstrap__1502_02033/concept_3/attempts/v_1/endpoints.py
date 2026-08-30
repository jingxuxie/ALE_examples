import itertools
import json
from functools import lru_cache

import numpy as np
import sympy as sp


@lru_cache(None)
def vectors(norm, rows, bound=5):
    return [np.array(vector, dtype=int) for vector in itertools.product(range(-bound, bound + 1), repeat=rows)
            if sum(entry * entry for entry in vector) == norm]


def integer_factors(gram, rows=3, bound=5):
    gram = np.array(gram).astype(int)
    columns = gram.shape[0]
    selected = sp.Matrix(gram).rref()[1][:rows]
    candidates = [vectors(int(gram[index, index]), rows, bound) for index in selected]
    result = []
    for first in candidates[0]:
        if list(first) != sorted(abs(entry) for entry in first)[::-1]:
            continue
        for second in candidates[1]:
            if first @ second != gram[selected[0], selected[1]]:
                continue
            last_candidates = candidates[2] if rows == 3 else [None]
            for last in last_candidates:
                chosen = [first, second]
                if rows == 3:
                    if first @ last != gram[selected[0], selected[2]] or second @ last != gram[selected[1], selected[2]]:
                        continue
                    chosen.append(last)
                basis = sp.Matrix(np.array(chosen).T)
                if basis.det() == 0:
                    continue
                factor = basis.T.inv() * sp.Matrix(gram[selected, :])
                if any(entry.q != 1 or abs(entry) > bound for entry in factor):
                    continue
                if factor.T * factor != sp.Matrix(gram):
                    continue
                result.append(np.array(factor).astype(int))
    return result


def normalized(index):
    inputs = json.load(open('../../participant/input/instances.json'))['instances']
    instance = inputs[index - 1]
    if index == 2:
        coefficients = [sp.Matrix(matrix)[:3, :3] * 64 for matrix in instance['coefficients'][:11]]
        return np.array(coefficients).reshape(11, 3, 3).astype(float), 3, 2, 5, 4, 1
    document = json.load(open('normalized3_simple.json'))
    coefficients = [sp.Matrix(matrix) for matrix in document['coefficients']]
    transform = sp.eye(4)
    transform[0, 3] = 1
    transform[2, 3] = 1
    coefficients = [transform.T * matrix * transform for matrix in coefficients]
    return np.array(coefficients).reshape(19, 4, 4).astype(float), 3, 3, 9, 8, 2


if __name__ == '__main__':
    for index in [2, 3]:
        coefficients, a_rows, b_rows, a_degree, b_degree, weight = normalized(index)
        first = integer_factors(coefficients[0])
        last = integer_factors(coefficients[-1])
        print(index, 'first', len(first), [entry.tolist() for entry in first])
        print(index, 'last', len(last), [entry.tolist() for entry in last])
        np.savez(f'endpoints{index}.npz', first=first, last=last)
