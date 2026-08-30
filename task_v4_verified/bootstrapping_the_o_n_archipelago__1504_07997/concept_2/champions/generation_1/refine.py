import json
import sys

import numpy as np
from scipy.optimize import least_squares

from solve import INPUT, ROOT, Solver, products


def refine(instance):
    solver = Solver(instance)
    case = json.loads((ROOT / (instance['id'] + '.json')).read_text())
    support = [atom['index'] for atom in case['atoms']]
    vectors = np.array([atom['ope'] for atom in case['atoms']])
    solver.evaluate(support, vectors)
    matrix = solver.design[:, support]
    for cutoff in (1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8):
        transformed = []
        observed = []
        for component in range(3):
            scaled = matrix / solver.scales[:, component, None]
            left, singular, right = np.linalg.svd(scaled, full_matrices=False)
            weight = left.T / np.maximum(singular, singular[0] * cutoff)[:, None]
            transformed.append(weight @ scaled)
            observed.append(weight @ (solver.target[:, component] / solver.scales[:, component]))
        transformed = np.array(transformed)
        observed = np.array(observed)

        def unpack(parameters):
            return np.concatenate(([np.sqrt(solver.shared)], parameters)).reshape(-1, 2)

        def residual(parameters):
            current = unpack(parameters)
            return (np.einsum('crk,kc->cr', transformed, products(current)) - observed).ravel()

        def jacobian(parameters):
            current = unpack(parameters)
            jac = np.zeros((3, len(support), len(support), 2))
            jac[0, :, :, 0] = 2 * transformed[0] * current[:, 0]
            jac[1, :, :, 0] = transformed[1] * current[:, 1]
            jac[1, :, :, 1] = transformed[1] * current[:, 0]
            jac[2, :, :, 1] = 2 * transformed[2] * current[:, 1]
            return jac.reshape(3 * len(support), -1)[:, 1:]

        solution = least_squares(residual, vectors.ravel()[1:], jac=jacobian, bounds=(-4, 4), max_nfev=5000, ftol=1e-14, xtol=1e-14, gtol=1e-14)
        vectors = unpack(solution.x)
        error = solver.evaluate(support, vectors)
        print('REFINE', instance['id'], cutoff, solution.nfev, error, flush=True)
        solver.fit(support, vectors)
        if solver.best_error < 1e-10:
            break


if __name__ == '__main__':
    for instance in json.loads(INPUT.read_text())['instances']:
        if instance['id'] in sys.argv[1:]:
            refine(instance)
