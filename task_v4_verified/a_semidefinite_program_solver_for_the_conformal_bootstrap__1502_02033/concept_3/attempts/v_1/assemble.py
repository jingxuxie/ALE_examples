import json
from pathlib import Path

import numpy as np
import sympy as sp

from endpoints import integer_factors


def integer_solution(index):
    path = Path(f'integer{index}.npz')
    if path.exists():
        stored = np.load(path)
        return stored['A'], stored['B']
    stored = np.load(f'success{index}.npz')
    first = np.rint(stored['A']).astype(int)
    second = stored['B']
    rows = second.shape[1]
    flat = second.transpose(1, 0, 2).reshape(rows, -1)
    gram = np.rint(flat.T @ flat).astype(int)
    possibilities = integer_factors(gram, rows=rows)
    if not possibilities:
        raise ValueError(f'Cannot reconstruct integer B for block {index}')
    second = possibilities[0].reshape(rows, second.shape[0], second.shape[2]).transpose(1, 0, 2)
    np.savez(path, A=first, B=second)
    return first, second


def polynomial_congruence(factors, matrix):
    variable = sp.Symbol('x')
    degree = len(factors) - 1
    polynomial = sum((sp.Matrix(factor) * variable ** power for power, factor in enumerate(factors)),
                     sp.zeros(factors.shape[1], factors.shape[2]))
    transformed = (polynomial * matrix).applyfunc(sp.expand)
    actual_degree = max(sp.degree(entry, variable) if entry != 0 else 0 for entry in transformed)
    return [transformed.applyfunc(lambda entry: entry.coeff(variable, power))
            for power in range(int(actual_degree) + 1)]


def construct(index, first, second):
    if index == 1:
        return [[sp.Matrix(matrix) / 8 for matrix in factor] for factor in [first, second]]
    if index == 2:
        variable = sp.Symbol('x')
        matrix = sp.eye(3).row_join(sp.Matrix([variable + 1, variable ** 2 - variable + 2, 2 * variable - 1]))
        return [[entry / 8 for entry in polynomial_congruence(factor, matrix)] for factor in [first, second]]
    document = json.load(open('normalized3_simple.json'))
    transform = sp.Matrix(document['T'])
    adjustment = sp.eye(4)
    adjustment[0, 3] = 1
    adjustment[2, 3] = 1
    inverse = (transform * adjustment).inv()
    return [[sp.Matrix(matrix) * inverse / (8 * 2 ** power) for power, matrix in enumerate(factor)]
            for factor in [first, second]]


def assemble():
    inputs = json.load(open('../../participant/input/instances.json'))['instances']
    certificates = []
    for index, instance in enumerate(inputs, 1):
        if Path(f'integer{index}.npz').exists() or Path(f'success{index}.npz').exists():
            factors = construct(index, *integer_solution(index))
        elif index == 3 and Path('approximate3.json').exists():
            approximate = json.load(open('approximate3.json'))
            factors = construct(index, np.array(approximate['A'], dtype=object), np.array(approximate['B'], dtype=object))
        else:
            factors = [[], []]
        certificate = {'id': instance['id']}
        for name, factor in zip(['A', 'B'], factors):
            degree = instance[f'{name.lower()}_degree']
            rows = instance[f'{name.lower()}_rows']
            factor += [sp.zeros(rows, instance['dimension']) for power in range(degree + 1 - len(factor))]
            certificate[name] = [[[str(entry) for entry in row] for row in matrix.tolist()] for matrix in factor]
        certificates.append(certificate)
    Path('certificate.json').write_text(json.dumps({'certificates': certificates}, indent=2) + '\n')


if __name__ == '__main__':
    assemble()
