import numpy as np


def solve_binary(matrix, syndrome, order):
    matrix = matrix[:, order].astype(np.uint8).copy()
    right = np.asarray(syndrome, dtype=np.uint8).copy()
    row = 0
    pivots = []
    for column in range(matrix.shape[1]):
        candidates = np.flatnonzero(matrix[row:, column])
        if not len(candidates):
            continue
        pivot = row + int(candidates[0])
        matrix[[row, pivot]] = matrix[[pivot, row]]
        right[[row, pivot]] = right[[pivot, row]]
        for target in range(matrix.shape[0]):
            if target != row and matrix[target, column]:
                matrix[target] ^= matrix[row]
                right[target] ^= right[row]
        pivots.append(column)
        row += 1
        if row == matrix.shape[0]:
            break
    solution = np.zeros(matrix.shape[1], dtype=np.uint8)
    for pivot_row, pivot_column in enumerate(pivots):
        solution[pivot_column] = right[pivot_row]
    restored = np.zeros_like(solution)
    restored[order] = solution
    return restored
