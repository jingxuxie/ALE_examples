import itertools
import sys
import time

import numpy as np

from fast_lm import optimize
from recover_bounded import Problem


endpoints = np.load('endpoints3.npz')
possibilities = [endpoints['last'][0][list(permutation)] * np.array(signs)[:, None]
                 for permutation in itertools.permutations(range(3))
                 for signs in itertools.product([-1, 1], repeat=3)]
selected = [20, 21, 28, 29, 33, 13, 37]
problems = {endpoint: Problem(3, endpoints['first'][0], possibilities[endpoint]) for endpoint in selected}
original_weights = {endpoint: problem.weights.copy() for endpoint, problem in problems.items()}
rng = np.random.default_rng(381742)
started = time.time()
best = {endpoint: float('inf') for endpoint in selected}
for trial in range(5000):
    endpoint = selected[trial % len(selected)]
    problem = problems[endpoint]
    mode = (trial // len(selected)) % 4
    problem.weights = original_weights[endpoint].copy() if mode == 3 else np.full_like(problem.weights, 0.1)
    values = rng.uniform(-4, 4, len(problem.free)) if trial % 2 else rng.normal(0, 2, len(problem.free))
    if mode in [1, 2]:
        for bound in [7.0, 6.0, 5.5, 5.2]:
            values, error, iterations = optimize(problem, values, bound=bound, steps=900,
                                                 penalty=0.05 if mode == 2 else 0)
    values, error, iterations = optimize(problem, values, steps=1800)
    statistics = problem.evaluate(values)
    if statistics[-1]:
        print('SUCCESS INITIAL', trial, endpoint, statistics, flush=True)
        break
    integer_score = np.linalg.norm(np.sin(np.pi * values) / np.pi) ** 2
    if error < 0.05:
        values, error, iterations = optimize(problem, values, penalty=0.1, steps=1200)
        statistics = problem.evaluate(values)
        if statistics[-1]:
            print('SUCCESS POLISH', trial, endpoint, statistics, flush=True)
            break
        integer_score = np.linalg.norm(np.sin(np.pi * values) / np.pi) ** 2
    score = integer_score + 100 * statistics[0] ** 2
    if score < best[endpoint]:
        best[endpoint] = score
        vector, first, second = problem.unpack(values)
        np.savez(f'multistart3_{endpoint}.npz', A=first, B=second, score=score)
        print('BEST', trial, endpoint, mode, score, statistics, time.time() - started, flush=True)
    if trial % 7 == 6:
        print('STATUS', trial, best, time.time() - started, flush=True)
