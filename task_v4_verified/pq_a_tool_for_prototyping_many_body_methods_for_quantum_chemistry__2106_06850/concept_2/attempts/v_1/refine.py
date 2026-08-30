import os
import sys
import time
from pathlib import Path

import search_exact as search
import numpy as np
import jax
import jax.numpy as jnp
from scipy.optimize import minimize


def targeted_quantities(parameters):
    original = search.quantities(parameters)
    regularizer = .01 * jnp.sum(search.weights * parameters[:120] ** 2) + .02 * jnp.sum(parameters[120:138] ** 2)
    updated = original.at[0].set(regularizer)
    updated = updated.at[41].add(-.14)
    updated = updated.at[42].add(-.18)
    updated = updated.at[43].add(-.035)
    updated = updated.at[44].add(-.035)
    updated = updated.at[46].add(-.09)
    return jnp.concatenate((updated, jnp.atleast_1d(-original[0] - .03)))


search.values_function = jax.jit(targeted_quantities)
search.derivative_function = jax.jit(jax.jacrev(targeted_quantities))


def main():
    started = time.monotonic()
    sources = sys.argv[1:] or ['candidate_0.npy', 'candidate_2.npy']
    for restart, source in enumerate(sources):
        parameters = np.load(source)
        evaluation = search.CachedEvaluation()
        iterations = [0]

        def callback(current):
            iterations[0] += 1
            values = evaluation.evaluate(current)[0]
            if iterations[0] % 10 == 0:
                np.save('refine_current.npy', current)
                print('REFINE', restart, iterations[0], 'seconds', time.monotonic() - started, 'objective', values[0], 'violation', values[-1] + .03, 'equality', np.max(np.abs(values[1:38])), 'inequality', np.min(values[38:]), flush=True)
            if np.max(np.abs(values[1:38])) < 1e-8 and np.min(values[38:]) > -1e-7:
                if search.assess(current, f'refine_feasible_{restart}'):
                    raise SystemExit(0)

        constraints = [
            {'type': 'eq', 'fun': evaluation.equality, 'jac': evaluation.equality_jacobian},
            {'type': 'ineq', 'fun': evaluation.inequality, 'jac': evaluation.inequality_jacobian},
        ]
        result = minimize(evaluation.objective, parameters, jac=True, method='SLSQP',
                          bounds=[(-1.48, 1.48)] * 120 + [(-1.24, 1.24)] * 18 + [(-1.48, 1.48)] * 18,
                          constraints=constraints, callback=callback,
                          options={'maxiter': 700, 'ftol': 2e-11, 'disp': True})
        print('REFINE_RESULT', restart, result.success, result.message, flush=True)
        if search.assess(result.x, f'refined_{restart}'):
            return


if __name__ == '__main__':
    main()
