import itertools
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import bmat, csr_matrix, eye

from fast_lm import optimize
from recover_bounded import Problem


class BOnly:
    def __init__(self, problem, first):
        self.problem = problem
        self.first = first
        self.penalty = 0

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
selected = [13, 21, 31, 20, 29, 33, 37, 36, 28]
states = {}
for endpoint in selected:
    problem = Problem(3, endpoints['first'][0], possibilities[endpoint])
    problem.weights[:] = 0.1
    stored = np.load(f'aonly3_{endpoint}.npz')
    vector = np.concatenate((stored['A'].ravel(), stored['B'].ravel()))[problem.free]
    states[endpoint] = [problem, vector, float('inf')]
started = time.time()
for trial in range(300):
    endpoint = selected[trial % len(selected)]
    problem, values, best = states[endpoint]
    first_size = sum(problem.free < problem.size_a)
    problem.penalty = 0
    residual = problem.residual(values)
    jacobian = problem.jacobian(values)
    nonzero = np.linalg.norm(jacobian, axis=1) > 1e-9
    residual, jacobian = residual[nonzero], jacobian[nonzero]
    equations = len(residual)
    wanted = jacobian[:, :first_size] @ values[:first_size] - residual
    coefficients = csr_matrix(jacobian)
    matrix = bmat([[coefficients, -eye(equations)], [-coefficients, -eye(equations)]], format='csc')
    if trial < len(selected):
        lower = np.floor(values[:first_size])
        upper = np.ceil(values[:first_size])
    else:
        lower = np.maximum(-5, np.rint(values[:first_size]) - 1)
        upper = np.minimum(5, np.rint(values[:first_size]) + 1)
    lows = np.concatenate((lower, np.full(len(values) - first_size, -1.5), np.zeros(equations)))
    highs = np.concatenate((upper, np.full(len(values) - first_size, 1.5), np.full(equations, np.inf)))
    objective = np.concatenate((np.zeros(len(values)), np.ones(equations)))
    integrality = np.concatenate((np.ones(first_size), np.zeros(len(values) - first_size + equations)))
    solution = milp(objective, integrality=integrality, bounds=Bounds(lows, highs),
                    constraints=LinearConstraint(matrix, -np.inf, np.concatenate((wanted, -wanted))),
                    options={'time_limit': 2.0, 'mip_rel_gap': 0.05})
    if solution.x is None:
        print('NO SOLUTION', trial, endpoint, solution.message, flush=True)
        continue
    first = np.rint(solution.x[:first_size])
    second = values[first_size:] + solution.x[first_size:len(values)]
    second, error, iterations = optimize(BOnly(problem, first), second, bound=12, steps=1500)
    candidate = np.concatenate((first, second))
    statistics = problem.evaluate(candidate)
    print('TRIAL', trial, endpoint, solution.fun, statistics, time.time() - started, flush=True)
    if statistics[-1]:
        print('SUCCESS', trial, endpoint, statistics, flush=True)
        break
    if error < best:
        states[endpoint] = [problem, candidate, error]
        vector, first_factor, second_factor = problem.unpack(candidate)
        np.savez(f'mixed3_{endpoint}.npz', A=first_factor, B=second_factor, error=error)
