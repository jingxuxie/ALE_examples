import itertools
import time

import numpy as np

from fast_lm import optimize
from recover_bounded import Problem


endpoints = np.load('endpoints3.npz')
possibilities = [endpoints['last'][0][list(permutation)] * np.array(signs)[:, None]
                 for permutation in itertools.permutations(range(3))
                 for signs in itertools.product([-1, 1], repeat=3)]
selected = [20, 21, 28, 29, 33, 13, 37, 31, 36]
problems = {endpoint: Problem(3, endpoints['first'][0], possibilities[endpoint]) for endpoint in selected}
for problem in problems.values():
    problem.weights[:] = 0.1
rng = np.random.default_rng(19381744)
started = time.time()
best_integer = 1e100
for trial in range(10000):
    endpoint = selected[trial % len(selected)]
    problem = problems[endpoint]
    amplitude = [1, 2, 3, 4][(trial // len(selected)) % 4]
    start = rng.normal(0, amplitude, len(problem.free))
    values, error, iterations = optimize(problem, start, steps=1500)
    statistics = problem.evaluate(values)
    if statistics[-1]:
        print('SUCCESS', trial, endpoint, statistics, flush=True)
        break
    vector, first, second = problem.unpack(values)
    integer = np.linalg.norm(first - np.rint(first))
    if error < 0.02 and integer < best_integer:
        best_integer = integer
        np.savez('direct3_best.npz', A=first, B=second)
        print('BEST INTEGER', trial, endpoint, error, integer, statistics, flush=True)
    if error < 0.05 and integer < 1.5:
        values, error, iterations = optimize(problem, values, penalty=0.03, steps=2000)
        statistics = problem.evaluate(values)
        print('POLISH', trial, endpoint, statistics, flush=True)
        if statistics[-1]:
            print('SUCCESS', trial, endpoint, statistics, flush=True)
            break
    if trial % 18 == 17:
        print('STATUS', trial, 'best_integer', best_integer, time.time() - started, flush=True)
