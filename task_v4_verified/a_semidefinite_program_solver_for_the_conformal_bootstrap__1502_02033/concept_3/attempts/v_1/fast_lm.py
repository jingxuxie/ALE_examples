import time

import numpy as np
from scipy.linalg import cho_factor, cho_solve


def optimize(problem, initial, steps=2000, penalty=0, bound=5):
    problem.penalty = penalty
    bound = np.broadcast_to(bound, np.shape(initial))
    values = np.clip(initial, -bound, bound)
    errors = problem.residual(values)
    energy = errors @ errors
    damping = 0.01
    accepted = 0
    for iteration in range(steps):
        jacobian = problem.jacobian(values)
        gradient = jacobian.T @ errors
        active = ((values <= -bound + 1e-10) & (gradient > 0)) | ((values >= bound - 1e-10) & (gradient < 0))
        free = np.flatnonzero(~active)
        if not len(free) or np.max(np.abs(gradient[free])) < 1e-9 or energy < 1e-18:
            break
        reduced = jacobian[:, free]
        hessian = reduced.T @ reduced
        diagonal = np.diag_indices(len(free))
        for attempt in range(20):
            damped = hessian.copy()
            damped[diagonal] += damping
            step = cho_solve(cho_factor(damped, check_finite=False), -gradient[free], check_finite=False)
            trial = values.copy()
            trial[free] = np.clip(values[free] + step, -bound[free], bound[free])
            trial_errors = problem.residual(trial)
            trial_energy = trial_errors @ trial_errors
            if trial_energy < energy:
                values, errors, energy = trial, trial_errors, trial_energy
                damping = max(1e-10, damping / 2)
                accepted += 1
                break
            damping *= 4
        else:
            break
    return values, np.sqrt(energy), iteration + 1


if __name__ == '__main__':
    import itertools
    from recover_bounded import Problem
    endpoints = np.load('endpoints3.npz')
    possibilities = [endpoints['last'][0][list(permutation)] * np.array(signs)[:, None]
                     for permutation in itertools.permutations(range(3))
                     for signs in itertools.product([-1, 1], repeat=3)]
    problem = Problem(3, endpoints['first'][0], possibilities[6])
    initial = np.random.default_rng(319).uniform(-4, 4, len(problem.free))
    started = time.time()
    result = optimize(problem, initial, steps=2000)
    print('FAST', result[1:], time.time() - started, flush=True)
    started = time.time()
    result2 = problem.optimize(initial, steps=500)
    print('TRF', np.linalg.norm(result2.fun), result2.nfev, time.time() - started, flush=True)
