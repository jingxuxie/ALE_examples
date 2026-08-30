import itertools
import sys

import numpy as np

from endpoints import normalized
from recover_bounded import Problem


index = int(sys.argv[1])
endpoint_index = int(sys.argv[2])
endpoints = np.load(f'endpoints{index}.npz')
possibilities = [endpoints['last'][0][list(permutation)] * np.array(signs)[:, None]
                 for permutation in itertools.permutations(range(3))
                 for signs in itertools.product([-1, 1], repeat=3)]
problem = Problem(index, endpoints['first'][0], possibilities[endpoint_index])
rng = np.random.default_rng(5172)
best = float('inf')
for trial in range(10):
    start = rng.uniform(-4, 4, len(problem.free))
    result = problem.optimize(start, steps=300)
    for penalty in [0.1, 0.5, 2.0]:
        result = problem.optimize(result.x, penalty=penalty, steps=150)
    values = np.rint(result.x)
    problem.penalty = 0
    error = np.linalg.norm(problem.residual(values))
    print(trial, error, flush=True)
    if error < best:
        best = error
        vector = problem.unpack(values)[0]
        target, a_rows, b_rows, a_degree, b_degree, weight = normalized(index)
        with open(f'anneal{index}_{endpoint_index}.txt', 'w') as output:
            output.write(f'{target.shape[1]} {a_rows} {b_rows} {a_degree} {b_degree} {weight}\n')
            output.write(' '.join(map(str, problem.wanted)) + '\n')
            output.write(' '.join(str(int(value)) for value in vector) + '\n')
