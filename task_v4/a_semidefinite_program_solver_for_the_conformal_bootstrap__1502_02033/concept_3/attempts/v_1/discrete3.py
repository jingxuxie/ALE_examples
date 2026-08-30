import itertools
import math
import time

import numpy as np

from fast_lm import optimize
from recover_bounded import Problem


class BOnly:
    def __init__(self, problem, first):
        self.problem, self.first, self.penalty = problem, first, 0

    def residual(self, values):
        self.problem.penalty = 0
        return self.problem.residual(np.concatenate((self.first, values)))

    def jacobian(self, values):
        self.problem.penalty = 0
        return self.problem.jacobian(np.concatenate((self.first, values)))[:, len(self.first):]


endpoints = np.load('endpoints3.npz')
possibilities = [endpoints['last'][0][list(permutation)] * np.array(signs)[:, None]
                 for permutation in itertools.permutations(range(3))
                 for signs in itertools.product([-1, 1], repeat=3)]
selected = [13, 21, 36, 29, 20, 37, 33, 28, 31]
states = {}
for endpoint in selected:
    problem = Problem(3, endpoints['first'][0], possibilities[endpoint])
    problem.weights[:] = 0.1
    first_size = sum(problem.free < problem.size_a)
    stored = np.load(f'aonly3_{endpoint}.npz')
    values = np.concatenate((stored['A'].ravel(), stored['B'].ravel()))[problem.free]
    first = np.rint(values[:first_size])
    second, error, iterations = optimize(BOnly(problem, first), values[first_size:], bound=12, steps=700)
    states[endpoint] = [problem, first, second, error ** 2, error ** 2]
    print('INITIAL', endpoint, error, flush=True)
rng = np.random.default_rng(144873)
started = time.time()
for trial in range(2000):
    endpoint = selected[trial % len(selected)]
    problem, first, second, energy, best = states[endpoint]
    values = np.concatenate((first, second))
    problem.penalty = 0
    residual = problem.residual(values)
    jacobian = problem.jacobian(values)
    first_size = len(first)
    first_jacobian, second_jacobian = jacobian[:, :first_size], jacobian[:, first_size:]
    response = np.linalg.lstsq(second_jacobian, first_jacobian, rcond=1e-9)[0]
    reduced = first_jacobian - second_jacobian @ response
    gradient = reduced.T @ residual
    diagonal = np.sum(reduced ** 2, axis=0)
    options = []
    for position in range(first_size):
        for delta in [-1, 1]:
            if abs(first[position] + delta) <= 5:
                options.append((2 * delta * gradient[position] + diagonal[position], position, delta))
    options.sort()
    choice = rng.integers(min(12, len(options))) if trial % 4 else rng.integers(len(options))
    predicted, position, delta = options[choice]
    candidate_first = first.copy()
    candidate_first[position] += delta
    candidate_second, error, iterations = optimize(BOnly(problem, candidate_first), second - delta * response[:, position],
                                                   bound=12, steps=400)
    candidate_energy = error ** 2
    temperature = [0.03, 0.1, 0.3][(trial // 90) % 3]
    if candidate_energy < energy or rng.random() < math.exp(min(0, (energy - candidate_energy) / temperature)):
        first, second, energy = candidate_first, candidate_second, candidate_energy
    if energy < best:
        best = energy
        statistics = problem.evaluate(np.concatenate((first, second)))
        vector, first_factor, second_factor = problem.unpack(np.concatenate((first, second)))
        np.savez(f'discrete3_{endpoint}.npz', A=first_factor, B=second_factor, error=math.sqrt(best))
        print('BEST', trial, endpoint, statistics, time.time() - started, flush=True)
        if statistics[-1]:
            print('SUCCESS', trial, endpoint, statistics, flush=True)
            break
    states[endpoint] = [problem, first, second, energy, best]
    if trial % 18 == 17:
        print('STATUS', trial, {key: round(value[-1], 6) for key, value in states.items()}, time.time() - started, flush=True)
