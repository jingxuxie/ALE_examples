import numpy as np


def prepare_columns(matrix):
    return [sum(1 << int(row) for row in np.flatnonzero(matrix[:, column]))
            for column in range(matrix.shape[1])]


def repair(columns, syndrome, reliability):
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
    return np.asarray([(correction >> column) & 1 for column in range(len(columns))], dtype=np.uint8)
