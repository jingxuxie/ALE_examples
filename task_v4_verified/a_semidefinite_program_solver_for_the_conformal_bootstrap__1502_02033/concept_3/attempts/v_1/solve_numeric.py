import itertools
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares


CONVOLUTIONS = {}


def product(factor):
    degree, rows, columns = factor.shape
    if degree not in CONVOLUTIONS:
        convolution = np.zeros((2 * degree - 1, degree * degree))
        convolution[(np.arange(degree)[:, None] + np.arange(degree)).ravel(), np.arange(degree * degree)] = 1
        CONVOLUTIONS[degree] = convolution
    products = np.einsum('ari,brj->abij', factor, factor).reshape(degree * degree, columns * columns)
    return (CONVOLUTIONS[degree] @ products).reshape(2 * degree - 1, columns, columns)


def fit(target, a_rows, b_rows, a_degree, b_degree, fixed, trials=100):
    dimension = target.shape[1]
    shape_a = (a_degree + 1, a_rows, dimension)
    shape_b = (b_degree + 1, b_rows, dimension)
    size_a = int(np.prod(shape_a))
    total = size_a + int(np.prod(shape_b))
    all_indices = np.arange(total)
    free = np.array([index for index in all_indices if index not in fixed])
    base = np.zeros(total)
    for index, value in fixed.items():
        base[index] = value
    upper = np.triu_indices(dimension)
    equations = [(power, row, col) for power in range(len(target))
                 for row, col in zip(*upper)]
    mapping = {value: index for index, value in enumerate(equations)}
    contributions = []
    for offset, shape, shift in [(0, shape_a, 0), (size_a, shape_b, 1)]:
        for power, row, col in np.ndindex(shape):
            variable = offset + np.ravel_multi_index((power, row, col), shape)
            if variable not in free:
                continue
            position = int(np.where(free == variable)[0][0])
            for other_power in range(shape[0]):
                for other_col in range(dimension):
                    equation = mapping[(power + other_power + shift, min(col, other_col), max(col, other_col))]
                    source = offset + np.ravel_multi_index((other_power, row, other_col), shape)
                    contributions.append((equation, position, source, 2 if col == other_col else 1))
    destinations, positions, sources, multiples = np.array(contributions).T
    wanted = target[:, upper[0], upper[1]].ravel()
    weights = 1 / np.sqrt(np.maximum(1, np.abs(wanted)))

    def unpack(values):
        vector = base.copy()
        vector[free] = values
        return vector, vector[:size_a].reshape(shape_a), vector[size_a:].reshape(shape_b)

    def residual(values):
        vector, first, second = unpack(values)
        actual = product(first)
        actual[1:2 * b_degree + 2] += product(second)
        return (actual[:, upper[0], upper[1]].ravel() - wanted) * weights

    def jacobian(values):
        vector, first, second = unpack(values)
        result = np.zeros((len(wanted), len(free)))
        np.add.at(result, (destinations, positions), vector[sources] * multiples)
        return result * weights[:, None]

    rng = np.random.default_rng(4721)
    best = float('inf')
    for trial in range(trials):
        start = np.clip(rng.normal(0, 2, len(free)), -4.9, 4.9)
        began = time.time()
        solution = least_squares(residual, start, jac=jacobian, max_nfev=2500, bounds=(-5, 5),
                                 ftol=1e-12, xtol=1e-12, gtol=1e-12)
        vector, first, second = unpack(solution.x)
        error = np.linalg.norm(solution.fun)
        a_integer = np.max(np.abs(first - np.rint(first)))
        flattened = second.transpose(1, 0, 2).reshape(b_rows, -1)
        gram = flattened.T @ flattened
        b_integer = np.max(np.abs(gram - np.rint(gram)))
        print(trial, 'error', error, 'integer', a_integer, b_integer,
              'steps', solution.nfev, 'seconds', time.time() - began, flush=True)
        if error < best:
            best = error
            np.savez('best_numeric.npz', A=first, B=second, residual=error)
        if error < 1e-7 and a_integer < 1e-5 and b_integer < 1e-4:
            np.savez('success_numeric.npz', A=first, B=second)
            return first, second
    return None


if __name__ == '__main__':
    from fractions import Fraction
    instance = json.load(open('../../participant/input/instances.json'))['instances'][0]
    target = np.array([[[64 * float(Fraction(entry)) for entry in row] for row in matrix]
                       for matrix in instance['coefficients']])
    endpoint = np.array([[1, 0, -1], [4, -2, -2]])
    leading = np.array([[0, 5, -3], [5, 4, 3]])
    for permutation in itertools.permutations(range(2)):
        for signs in itertools.product([-1, 1], repeat=2):
            fixed = {index: value for index, value in enumerate(endpoint.ravel())}
            last = leading[list(permutation)] * np.array(signs)[:, None]
            fixed.update({36 + index: value for index, value in enumerate(last.ravel())})
            print('ENDPOINT', last.tolist(), flush=True)
            if fit(target, 2, 2, 6, 5, fixed, trials=150) is not None:
                raise SystemExit(0)
