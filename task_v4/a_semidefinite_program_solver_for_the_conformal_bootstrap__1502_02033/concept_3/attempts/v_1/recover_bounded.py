import itertools
import sys
import time

import numpy as np
from scipy.optimize import least_squares

from endpoints import normalized
from solve_numeric import product


class Problem:
    def __init__(self, index, first, last):
        target, a_rows, b_rows, a_degree, b_degree, self.weight = normalized(index)
        self.index = index
        dimension = target.shape[1]
        self.shape_a = (a_degree + 1, a_rows, dimension)
        self.shape_b = (b_degree + 1, b_rows, dimension)
        self.size_a = int(np.prod(self.shape_a))
        total = self.size_a + int(np.prod(self.shape_b))
        fixed = {position: value for position, value in enumerate(first.ravel())}
        fixed.update({self.size_a - a_rows * dimension + position: value
                      for position, value in enumerate(last.ravel())})
        self.free = np.array([position for position in range(total) if position not in fixed])
        self.base = np.zeros(total)
        for position, value in fixed.items():
            self.base[position] = value
        self.upper = np.triu_indices(dimension)
        equations = [(power, row, column) for power in range(len(target))
                     for row, column in zip(*self.upper)]
        mapping = {value: position for position, value in enumerate(equations)}
        free_mapping = {value: position for position, value in enumerate(self.free)}
        contributions = []
        for offset, shape, shift in [(0, self.shape_a, 0), (self.size_a, self.shape_b, 1)]:
            multiplier = self.weight if shift else 1
            for power, row, column in np.ndindex(shape):
                variable = offset + np.ravel_multi_index((power, row, column), shape)
                if variable not in free_mapping:
                    continue
                position = free_mapping[variable]
                for other_power in range(shape[0]):
                    for other_column in range(dimension):
                        equation = mapping[(power + other_power + shift,
                                            min(column, other_column), max(column, other_column))]
                        source = offset + np.ravel_multi_index((other_power, row, other_column), shape)
                        contributions.append((equation, position, source,
                                              multiplier * (2 if column == other_column else 1)))
        self.destinations, self.positions, self.sources, self.multiples = np.array(contributions).T
        self.wanted = target[:, self.upper[0], self.upper[1]].ravel()
        self.weights = 1 / np.sqrt(np.maximum(1, np.abs(self.wanted)))
        self.penalty = 0

    def unpack(self, values):
        vector = self.base.copy()
        vector[self.free] = values
        return vector, vector[:self.size_a].reshape(self.shape_a), vector[self.size_a:].reshape(self.shape_b)

    def residual(self, values):
        vector, first, second = self.unpack(values)
        actual = product(first)
        actual[1:2 * self.shape_b[0]] += self.weight * product(second)
        result = (actual[:, self.upper[0], self.upper[1]].ravel() - self.wanted) * self.weights
        if self.penalty:
            mask = getattr(self, 'penalty_mask', 1)
            result = np.concatenate((result, self.penalty * mask * np.sin(np.pi * values) / np.pi))
        return result

    def jacobian(self, values):
        vector, first, second = self.unpack(values)
        result = np.zeros((len(self.wanted), len(self.free)))
        result[self.destinations, self.positions] = vector[self.sources] * self.multiples
        result *= self.weights[:, None]
        if self.penalty:
            mask = getattr(self, 'penalty_mask', 1)
            result = np.vstack((result, np.diag(self.penalty * mask * np.cos(np.pi * values))))
        return result

    def optimize(self, start, penalty=0, steps=200):
        self.penalty = penalty
        return least_squares(self.residual, np.clip(start, -4.999999, 4.999999), jac=self.jacobian,
                             bounds=(-5, 5), max_nfev=steps, ftol=1e-10, xtol=1e-10, gtol=1e-10)

    def evaluate(self, values):
        self.penalty = 0
        error = np.linalg.norm(self.residual(values))
        vector, first, second = self.unpack(values)
        a_integer = np.max(np.abs(first - np.rint(first)))
        flattened = second.transpose(1, 0, 2).reshape(self.shape_b[1], -1)
        gram = flattened.T @ flattened
        b_integer = np.max(np.abs(gram - np.rint(gram)))
        success = error < 1e-5 and a_integer < 1e-4 and b_integer < 1e-3
        if success:
            np.savez(f'success{self.index}.npz', A=first, B=second)
        return error, a_integer, b_integer, success


def run(index):
    endpoints = np.load(f'endpoints{index}.npz')
    first = endpoints['first'][0]
    leading = endpoints['last'][0]
    possibilities = []
    for permutation in itertools.permutations(range(3)):
        for signs in itertools.product([-1, 1], repeat=3):
            possibilities.append(leading[list(permutation)] * np.array(signs)[:, None])
    rng = np.random.default_rng(3319)
    order = rng.permutation(len(possibilities))
    for endpoint_index in order:
        last = possibilities[endpoint_index]
        problem = Problem(index, first, last)
        print('ENDPOINT', endpoint_index, last.tolist(), flush=True)
        best = float('inf')
        best_values = None
        for trial in range(3 if index == 3 else 30):
            began = time.time()
            if trial % 3 == 2 and best_values is not None:
                start = best_values + rng.normal(0, 1.5, len(problem.free))
            else:
                start = rng.uniform(-4, 4, len(problem.free))
            initial = problem.optimize(start, steps=150 if index == 3 else 250)
            result = problem.evaluate(initial.x)
            print(trial, 'initial', result, initial.nfev, flush=True)
            if result[-1]:
                return
            values = initial.x
            for penalty in [0.03, 0.15, 0.6, 2.0]:
                polished = problem.optimize(values, penalty=penalty, steps=150)
                values = polished.x
                result = problem.evaluate(values)
                if result[-1]:
                    return
            cost = np.linalg.norm(problem.residual(values)) + np.linalg.norm(values - np.rint(values)) / 10
            if cost < best:
                best = cost
                best_values = values.copy()
                vector, first_factor, second_factor = problem.unpack(values)
                np.savez(f'best{index}.npz', A=first_factor, B=second_factor, error=result[0])
            print(trial, 'final', result, 'cost', cost, 'best', best,
                  'seconds', time.time() - began, flush=True)


if __name__ == '__main__':
    run(int(sys.argv[1]))
