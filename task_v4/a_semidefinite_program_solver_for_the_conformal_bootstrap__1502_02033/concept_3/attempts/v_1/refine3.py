import json
import time
from fractions import Fraction

import mpmath as mp
import numpy as np
from scipy.linalg import qr

from endpoints import normalized
from recover_bounded import Problem


stored = np.load('fast3_uniform_28.npz')
endpoints = np.load('endpoints3.npz')
problem = Problem(3, endpoints['first'][0], stored['A'][-1])
initial = np.concatenate((stored['A'].ravel(), stored['B'].ravel()))[problem.free]
problem.penalty = 0
jacobian = problem.jacobian(initial)
equations = np.flatnonzero(np.linalg.norm(jacobian, axis=1) > 1e-12)
orthogonal, triangular, permutation = qr(jacobian[equations], mode='economic', pivoting=True)
chosen = permutation[:len(equations)]
column_mapping = {int(position): column for column, position in enumerate(chosen)}
row_mapping = {int(equation): row for row, equation in enumerate(equations)}
mp.mp.dps = 110


def number(value):
    rational = Fraction(float(value)).limit_denominator(10 ** 9)
    return mp.mpf(rational.numerator) / rational.denominator


vector = [number(value) for value in problem.base]
for position, index in enumerate(problem.free):
    vector[index] = number(initial[position])
target = [mp.mpf(int(value)) for value in problem.wanted]
terms = [[] for equation in target]
triangle = [(row, column) for row in range(4) for column in range(row, 4)]
for offset, shape, shift, weight in [(0, problem.shape_a, 0, 1), (problem.size_a, problem.shape_b, 1, 2)]:
    for left in range(shape[0]):
        for right in range(shape[0]):
            for row in range(shape[1]):
                for pair, (column, other_column) in enumerate(triangle):
                    first = offset + (left * shape[1] + row) * 4 + column
                    second = offset + (right * shape[1] + row) * 4 + other_column
                    terms[(left + right + shift) * 10 + pair].append((first, second, weight))
jacobian_terms = []
for equation, position, source, multiple in zip(problem.destinations, problem.positions, problem.sources, problem.multiples):
    if int(position) in column_mapping and int(equation) in row_mapping:
        jacobian_terms.append((row_mapping[int(equation)], column_mapping[int(position)], int(source), int(multiple)))


def errors():
    return mp.matrix([sum((weight * vector[first] * vector[second] for first, second, weight in terms[equation]), mp.mpf(0))
                      - target[equation] for equation in equations])


started = time.time()
for iteration in range(12):
    residual = errors()
    error = max(abs(value) for value in residual)
    print('ITERATION', iteration, mp.nstr(error, 10), time.time() - started, flush=True)
    if error < mp.mpf('1e-100'):
        break
    matrix = mp.matrix(len(equations), len(chosen))
    for row, column, source, multiple in jacobian_terms:
        matrix[row, column] = multiple * vector[source]
    update = mp.lu_solve(matrix, -residual)
    for column, position in enumerate(chosen):
        vector[problem.free[position]] += update[column]
first = np.array([str(Fraction(mp.nstr(value, 105))) for value in vector[:problem.size_a]], dtype=object).reshape(problem.shape_a)
second = np.array([str(Fraction(mp.nstr(value, 105))) for value in vector[problem.size_a:]], dtype=object).reshape(problem.shape_b)
json.dump({'A': first.tolist(), 'B': second.tolist(), 'exact': False,
           'normalized_residual': mp.nstr(max(abs(value) for value in errors()), 20)}, open('approximate3.json', 'w'), indent=2)
