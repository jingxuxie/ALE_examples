import itertools
import math
import sys
import time
from pathlib import Path

import numpy as np

from fast_lm import optimize
from recover_bounded import Problem


endpoint = int(sys.argv[1]) if len(sys.argv) > 1 else 21
endpoints = np.load('endpoints3.npz')
possibilities = [endpoints['last'][0][list(permutation)] * np.array(signs)[:, None]
                 for permutation in itertools.permutations(range(3))
                 for signs in itertools.product([-1, 1], repeat=3)]
problem = Problem(3, endpoints['first'][0], possibilities[endpoint])
rng = np.random.default_rng(418732 + endpoint)
current = None
for filename in [f'fast3_{endpoint}.npz', f'fast3_relative_{endpoint}.npz', f'fast3_uniform_{endpoint}.npz']:
    if Path(filename).exists():
        stored = np.load(filename)
        current = np.concatenate((stored['A'].ravel(), stored['B'].ravel()))[problem.free]
        break
best = float('inf')
current_score = float('inf')
best_values = None
started = time.time()
for trial in range(3000):
    if current is None or trial % 10 == 9:
        start = rng.uniform(-4, 4, len(problem.free)) if trial % 2 else rng.normal(0, 2, len(problem.free))
        values, error, iterations = optimize(problem, start, steps=2000)
    elif trial == 0:
        values = current.copy()
    else:
        problem.penalty = 0
        left, singular, right = np.linalg.svd(problem.jacobian(current), full_matrices=True)
        rank = sum(singular > 1e-7)
        nullspace = right[rank:].T
        scale = rng.choice([0.5, 1.0, 2.0, 4.0])
        values = current + scale * nullspace @ rng.normal(size=nullspace.shape[1])
    values, error, iterations = optimize(problem, values, penalty=0.03, steps=1500)
    statistics = problem.evaluate(values)
    score = np.linalg.norm(np.sin(np.pi * values) / np.pi) ** 2
    total = score + 1000 * statistics[0] ** 2
    if statistics[-1]:
        print('SUCCESS', endpoint, trial, statistics, flush=True)
        break
    if total < best:
        best = total
        best_values = values.copy()
        vector, first, second = problem.unpack(values)
        np.savez(f'hop3_{endpoint}.npz', A=first, B=second, score=score, error=statistics[0])
        print('BEST', endpoint, trial, total, score, statistics, time.time() - started, flush=True)
    temperature = [0.03, 0.1, 0.3][(trial // 100) % 3]
    if total < current_score or rng.random() < math.exp(min(0, (current_score - total) / temperature)):
        current = values.copy()
        current_score = total
    if trial % 100 == 99:
        current = best_values.copy()
        current_score = best
    if trial % 10 == 9:
        print('STATUS', endpoint, trial, 'best', best, 'current', current_score,
              'seconds', time.time() - started, flush=True)
