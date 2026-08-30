import itertools
import time
from pathlib import Path

import numpy as np

from fast_lm import optimize
from recover_bounded import Problem


endpoints = np.load('endpoints3.npz')
possibilities = [endpoints['last'][0][list(permutation)] * np.array(signs)[:, None]
                 for permutation in itertools.permutations(range(3))
                 for signs in itertools.product([-1, 1], repeat=3)]
selected = [20, 21, 28, 29, 33, 13, 37, 31, 36]
problems = {endpoint: Problem(3, endpoints['first'][0], possibilities[endpoint]) for endpoint in selected}
population = {endpoint: [] for endpoint in selected}
for endpoint, problem in problems.items():
    problem.weights[:] = 0.1
    for name in [f'fast3_uniform_{endpoint}.npz', f'multistart3_{endpoint}.npz', f'hop3_{endpoint}.npz', f'population3_{endpoint}.npz']:
        if not Path(name).exists():
            continue
        stored = np.load(name)
        vector = np.concatenate((stored['A'].ravel(), stored['B'].ravel()))
        population[endpoint].append((100.0, vector[problem.free]))
rng = np.random.default_rng(33172393)
started = time.time()
best = {endpoint: float('inf') for endpoint in selected}
for trial in range(10000):
    endpoint = selected[trial % len(selected)]
    problem = problems[endpoint]
    pool = population[endpoint]
    initial = pool[rng.integers(len(pool))][1]
    amplitude = rng.choice([0.2, 0.5, 1.0, 1.5, 2.5])
    mutation = rng.normal(0, amplitude, len(problem.free))
    if trial % 3:
        mutation *= rng.random(len(problem.free)) < rng.choice([0.05, 0.15, 0.3])
    values = initial + mutation
    values, error, iterations = optimize(problem, values, steps=1500)
    statistics = problem.evaluate(values)
    if statistics[-1]:
        print('SUCCESS INITIAL', trial, endpoint, statistics, flush=True)
        break
    if error < 0.2:
        penalty = rng.choice([0.03, 0.1, 0.3, 0.6])
        values, error, iterations = optimize(problem, values, penalty=penalty, steps=1000)
        statistics = problem.evaluate(values)
        if statistics[-1]:
            print('SUCCESS POLISH', trial, endpoint, statistics, flush=True)
            break
    score = np.linalg.norm(np.sin(np.pi * values) / np.pi) ** 2 + 100 * statistics[0] ** 2
    if score < best[endpoint]:
        best[endpoint] = score
        vector, first, second = problem.unpack(values)
        np.savez(f'population3_{endpoint}.npz', A=first, B=second, score=score)
        print('BEST', trial, endpoint, score, statistics, time.time() - started, flush=True)
    distinct = all(np.linalg.norm(values - entry[1]) > 0.5 for entry in pool)
    if distinct and (len(pool) < 40 or score < max(entry[0] for entry in pool)):
        pool.append((score, values.copy()))
        pool.sort(key=lambda entry: entry[0])
        del pool[40:]
    if trial % 9 == 8:
        print('STATUS', trial, best, time.time() - started, flush=True)
