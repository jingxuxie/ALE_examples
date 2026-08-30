import itertools
import math
import sys
import time

import numpy as np

from recover_bounded import Problem


index = int(sys.argv[1])
endpoint_index = int(sys.argv[2])
trials = int(sys.argv[3]) if len(sys.argv) > 3 else 1500
endpoints = np.load(f'endpoints{index}.npz')
possibilities = [endpoints['last'][0][list(permutation)] * np.array(signs)[:, None]
                 for permutation in itertools.permutations(range(3))
                 for signs in itertools.product([-1, 1], repeat=3)]
problem = Problem(index, endpoints['first'][0], possibilities[endpoint_index])
rng = np.random.default_rng(74821 + endpoint_index)
current = None
current_score = float('inf')
best = float('inf')
best_values = None
started = time.time()
for trial in range(trials):
    if current is None or trial % 60 == 0:
        initial = rng.uniform(-4, 4, len(problem.free))
        result = problem.optimize(initial, steps=500)
        values = result.x
    else:
        problem.penalty = 0
        jacobian = problem.jacobian(current)
        left, singular, right = np.linalg.svd(jacobian, full_matrices=True)
        rank = sum(singular > 1e-7)
        nullspace = right[rank:].T
        scale = rng.choice([0.5, 1.0, 2.0, 4.0])
        values = current + scale * nullspace @ rng.normal(size=nullspace.shape[1])
    result = problem.optimize(values, penalty=0.03, steps=300)
    values = result.x
    statistics = problem.evaluate(values)
    score = np.linalg.norm(np.sin(np.pi * values) / np.pi) ** 2
    total = score + 1000 * statistics[0] ** 2
    if statistics[-1]:
        print('SUCCESS', trial, statistics, flush=True)
        break
    if total < best:
        best = total
        best_values = values.copy()
        vector, first, second = problem.unpack(values)
        np.savez(f'hop{index}_{endpoint_index}.npz', A=first, B=second, score=score, error=statistics[0])
        print('BEST', trial, total, score, statistics, time.time() - started, flush=True)
    temperature = [0.03, 0.1, 0.3][(trial // 100) % 3]
    if total < current_score or rng.random() < math.exp(min(0, (current_score - total) / temperature)):
        current = values.copy()
        current_score = total
    if trial % 100 == 99:
        current = best_values.copy()
        current_score = best
    if trial % 20 == 19:
        print('STATUS', trial, 'best', best, 'current', current_score,
              'seconds', time.time() - started, flush=True)
