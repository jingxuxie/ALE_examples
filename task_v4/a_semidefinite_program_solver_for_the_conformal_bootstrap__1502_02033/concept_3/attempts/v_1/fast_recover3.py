import itertools
import sys
import time
from pathlib import Path

import numpy as np

from fast_lm import optimize
from recover_bounded import Problem
import recover_bounded


endpoints = np.load('endpoints3.npz')
variant = int(sys.argv[3]) if len(sys.argv) > 3 else 0
if variant:
    coordinate = np.eye(4, dtype=int)
    if variant == 1:
        coordinate[1, 3] = 1
    else:
        coordinate[0, 3] = -1
        coordinate[2, 3] = 1
    original_normalized = recover_bounded.normalized

    def shifted_normalized(index):
        result = original_normalized(index)
        target = np.array([coordinate.T @ matrix @ coordinate for matrix in result[0]])
        return (target, *result[1:])

    recover_bounded.normalized = shifted_normalized
    endpoints = {key: np.array([matrix @ coordinate for matrix in endpoints[key]]) for key in ['first', 'last']}
possibilities = [endpoints['last'][0][list(permutation)] * np.array(signs)[:, None]
                 for permutation in itertools.permutations(range(3))
                 for signs in itertools.product([-1, 1], repeat=3)]
problems = {endpoint: Problem(3, endpoints['first'][0], last) for endpoint, last in enumerate(possibilities)}
mode = sys.argv[2] if len(sys.argv) > 2 else 'relative'
if mode.startswith('uniform'):
    for problem in problems.values():
        problem.weights[:] = 0.1
if variant:
    for problem in problems.values():
        problem.index = f'3_variant{variant}'
best = {endpoint: float('inf') for endpoint in problems}
best_values = {}
for endpoint, problem in problems.items():
    for filename in ([f'fast3_{endpoint}.npz'] if not variant else []) + [f'fast3_{mode}_{endpoint}.npz']:
        if not Path(filename).exists():
            continue
        stored = np.load(filename)
        vector = np.concatenate((stored['A'].ravel(), stored['B'].ravel()))
        values = vector[problem.free]
        error = np.linalg.norm(problem.residual(values))
        if error < best[endpoint]:
            best[endpoint] = error
            best_values[endpoint] = values
rng = np.random.default_rng(1837649 if mode == 'relative' else 98317731)
started = time.time()
passes = int(sys.argv[1]) if len(sys.argv) > 1 else 10
for cycle in range(passes):
    order = sorted(problems, key=lambda endpoint: best[endpoint])
    for endpoint in order:
        problem = problems[endpoint]
        for trial in range(2):
            if endpoint in best_values and trial == 1 and cycle % 3:
                start = best_values[endpoint] + rng.normal(0, 1.5, len(problem.free))
            else:
                start = rng.uniform(-4, 4, len(problem.free)) if mode == 'relative' else rng.normal(0, 2, len(problem.free))
            values, error, iterations = optimize(problem, start, steps=1800)
            if error < best[endpoint]:
                best[endpoint] = error
                best_values[endpoint] = values.copy()
                vector, first, second = problem.unpack(values)
                np.savez(f'fast3_{mode}_{endpoint}.npz', A=first, B=second, error=error)
                print('BEST', cycle, endpoint, trial, error, iterations, time.time() - started, flush=True)
            statistics = problem.evaluate(values)
            if statistics[-1]:
                print('SUCCESS', cycle, endpoint, statistics, flush=True)
                raise SystemExit(0)
            if error < 0.1:
                values, error, iterations = optimize(problem, values, penalty=0.03, steps=2000)
                statistics = problem.evaluate(values)
                print('POLISH', cycle, endpoint, statistics, flush=True)
                if statistics[-1]:
                    print('SUCCESS', cycle, endpoint, statistics, flush=True)
                    raise SystemExit(0)
        print('STATUS', cycle, endpoint, best[endpoint], time.time() - started, flush=True)
    print('PASS', cycle, sorted(best.items(), key=lambda entry: entry[1]), flush=True)
