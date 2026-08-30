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
    problem.penalty_mask = (problem.free < problem.size_a).astype(float)
rng = np.random.default_rng(933812)
started = time.time()
best = {endpoint: float('inf') for endpoint in selected}
best_values = {}
for trial in range(5000):
    endpoint = selected[trial % len(selected)]
    problem = problems[endpoint]
    bounds = np.where(problem.free < problem.size_a, 5.0, 9.0)
    if endpoint in best_values and trial % 3:
        values = best_values[endpoint] + rng.normal(0, 1.5, len(problem.free))
    else:
        values = rng.normal(0, 3, len(problem.free))
    values, error, iterations = optimize(problem, values, steps=1200, bound=bounds)
    for penalty in [0.03, 0.15]:
        values, error, iterations = optimize(problem, values, penalty=penalty, bound=bounds, steps=1200)
    statistics = problem.evaluate(values)
    score = np.linalg.norm(problem.penalty_mask * np.sin(np.pi * values) / np.pi) ** 2
    total = score + 100 * statistics[0] ** 2
    if statistics[-1]:
        print('SUCCESS', trial, endpoint, statistics, flush=True)
        break
    if total < best[endpoint]:
        best[endpoint] = total
        best_values[endpoint] = values.copy()
        vector, first, second = problem.unpack(values)
        np.savez(f'aonly3_{endpoint}.npz', A=first, B=second, error=statistics[0])
        print('BEST', trial, endpoint, total, statistics, time.time() - started, flush=True)
    if trial % 9 == 8:
        print('STATUS', trial, best, time.time() - started, flush=True)
