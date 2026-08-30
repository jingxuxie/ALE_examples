import json
import sys
import time

import numpy as np
from scipy.optimize import nnls

from improve import Optimizer, SOURCE, load_seed


def recover(instance, seconds):
    solver = Optimizer(instance)
    saved = load_seed(instance['id'])
    if saved:
        solver.evaluate([atom['index'] for atom in saved['atoms']], np.array([atom['ope'] for atom in saved['atoms']]))
    deadline = time.monotonic() + seconds
    for cutoff in (1e-7, 1e-9, 1e-11, 1e-5, 1e-13, 1e-6, 1e-8, 1e-10):
        coefficients = []
        for component in (0, 2):
            matrix = solver.design / solver.scales[:, component, None]
            target = solver.target[:, component] / solver.scales[:, component]
            if component == 0:
                target = target - matrix[:, 0] * solver.shared ** 2
                matrix = matrix[:, 1:]
            left, singular, right = np.linalg.svd(matrix, full_matrices=False)
            weights = 1 / np.maximum(singular, singular[0] * cutoff)
            transformed = (left.T @ matrix) * weights[:, None]
            observed = (left.T @ target) * weights
            try:
                values, cost = nnls(transformed, observed, maxiter=10000)
            except Exception as error:
                print('NNLS ERROR', error, flush=True)
                break
            if component == 0:
                values = np.r_[solver.shared ** 2, values]
            coefficients.append(values)
        if len(coefficients) < 2:
            continue
        magnitude = coefficients[0] + coefficients[1]
        forced = [index for index, candidate in enumerate(instance['candidates']) if candidate['spin'] != 0 and magnitude[index] > 1e-5]
        if len(forced) >= instance['max_atoms'] - 1:
            forced = []
        chosen = [0] + forced
        chosen += [int(index) for index in np.argsort(-magnitude) if index not in chosen][:instance['max_atoms'] - len(chosen)]
        support = np.array(sorted(chosen))
        print('SEED', instance['id'], cutoff, [(int(index), float(magnitude[index])) for index in np.argsort(-magnitude)[:16]], flush=True)
        vectors = np.sqrt(np.maximum(np.array(coefficients).T[support], 0))
        matrix = solver.design[:, support] / solver.scales[:, 1, None]
        cross = np.linalg.lstsq(matrix, solver.target[:, 1] / solver.scales[:, 1], rcond=1e-9)[0]
        vectors[:, 1] *= np.sign(cross)
        for conditioning in (1e-4, 1e-6, 1e-8):
            error, vectors, cost = solver.fit(support, vectors, conditioning, nfev=1000)
            if solver.best_error < 1e-8:
                return
        if time.monotonic() > deadline:
            break
    if solver.best and solver.best_error > 1e-8 and deadline > time.monotonic():
        solver.improve(solver.best, deadline - time.monotonic())


if __name__ == '__main__':
    instances = json.loads(SOURCE.read_text())['instances']
    for selected in map(int, sys.argv[1:]):
        recover(instances[selected], 180)
