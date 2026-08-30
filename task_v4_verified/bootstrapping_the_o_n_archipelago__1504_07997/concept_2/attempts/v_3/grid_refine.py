import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import sys
sys.dont_write_bytecode = True
import json
import time
import contextlib
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from scipy.optimize import least_squares, linear_sum_assignment
from joint_solver import Joint, ROOT, SOURCE
import improve

def recover(variant):
    os.environ['RESULT_DIR'] = 'grid_results_' + str(variant)
    instance = json.loads(SOURCE.read_text())['instances'][0]
    with (ROOT / ('grid_' + str(variant) + '.log')).open('w', buffering=1) as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            solver = Joint(instance)
            rng = np.random.default_rng(903211+variant)
            deadline = time.monotonic()+420
            dimensions = np.array([candidate['dimension'] for candidate in instance['candidates']])
            spins = np.array([candidate['spin'] for candidate in instance['candidates']])
            column_scales = np.array([candidate['column_scale'] for candidate in instance['candidates']])
            probes = np.array([probe['t'] for probe in instance['probes']])[:, None]
            orders = np.array([probe['order'] for probe in instance['probes']])[:, None]
            weights = []
            observed = []
            for component in range(3):
                matrix = solver.design/solver.scales[:, component, None]
                left, singular, right = np.linalg.svd(matrix, full_matrices=False)
                weight = left.T/np.maximum(singular, singular[0]*(1e-6 if variant == 0 else 1e-3))[:, None]
                weight /= solver.scales[:, component]
                weights.append(weight)
                observed.append(weight @ solver.target[:, component])
            weights = np.array(weights)
            observed = np.array(observed)
            for attempt in range(100):
                saved = improve.load_seed(instance['id'])
                support = np.array([atom['index'] for atom in saved['atoms']])
                vectors = np.array([atom['ope'] for atom in saved['atoms']])
                solver.optimizer.evaluate(support, vectors)
                if solver.optimizer.best_error < 1e-8:
                    return solver.optimizer.best_error
                count = len(support)
                initial_dimensions = dimensions[support]
                base = solver.design[:, support]
                spacing = np.array([np.median(np.diff(np.sort(dimensions[(spins == spin) & (np.arange(solver.count) != 0)]))) for spin in spins[support]])
                lower_dimensions = np.array([min(dimensions[(spins == spin) & (np.arange(solver.count) != 0)]) for spin in spins[support[1:]]])
                upper_dimensions = np.array([max(dimensions[spins == spin]) for spin in spins[support[1:]]])
                lower = np.r_[np.full(2*count-1, -3.99), lower_dimensions]
                upper = np.r_[np.full(2*count-1, 3.99), upper_dimensions]
                parameters = np.r_[vectors.ravel()[1:], initial_dimensions[1:]]
                if attempt:
                    parameters[2*count-1:] += rng.normal(0, (0.3 if attempt % 3 else 1.)*spacing[1:])
                    parameters[1:2*count-1] += rng.normal(0, 0.03, 2*count-2)
                parameters = np.clip(parameters, lower+1e-10, upper-1e-10)
                def unpack(current):
                    return np.r_[solver.optimizer.shared, current[:2*count-1]].reshape(count, 2), np.r_[initial_dimensions[0], current[2*count-1:]]
                def kernel(current_dimensions):
                    return base*np.exp(-probes*(current_dimensions-initial_dimensions))*(current_dimensions/initial_dimensions)**orders
                def assignment(current_dimensions):
                    costs = np.abs(current_dimensions[:, None]-dimensions[None, :])/spacing[:, None]
                    costs[spins[support, None] != spins[None, :]] = 1e6
                    costs[1:, 0] = 1e6
                    costs[0, 1:] = 1e6
                    return linear_sum_assignment(costs)[1]
                for penalty in (0., 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 0.1):
                    def residual(current):
                        current_vectors, current_dimensions = unpack(current)
                        prediction = kernel(current_dimensions) @ improve.products(current_vectors)
                        moments = (np.einsum('crm,mc->cr', weights, prediction)-observed).ravel()
                        nearest = assignment(current_dimensions)
                        return np.r_[moments, penalty*(current_dimensions[1:]-dimensions[nearest[1:]])/spacing[1:]]
                    def jacobian(current):
                        current_vectors, current_dimensions = unpack(current)
                        current_kernel = kernel(current_dimensions)
                        transformed = np.einsum('crm,mk->crk', weights, current_kernel)
                        jac = np.zeros((3, transformed.shape[1], count, 2))
                        jac[0, :, :, 0] = 2*transformed[0]*current_vectors[:, 0]
                        jac[1, :, :, 0] = transformed[1]*current_vectors[:, 1]
                        jac[1, :, :, 1] = transformed[1]*current_vectors[:, 0]
                        jac[2, :, :, 1] = 2*transformed[2]*current_vectors[:, 1]
                        derivative = current_kernel*(-probes+orders/current_dimensions)
                        delta_jac = np.einsum('crm,mk,kc->crk', weights, derivative, improve.products(current_vectors))[:, :, 1:]
                        moments = np.c_[jac.reshape(3*transformed.shape[1], -1)[:, 1:], delta_jac.reshape(3*transformed.shape[1], -1)]
                        grid = np.c_[np.zeros((count-1, 2*count-1)), np.diag(penalty/spacing[1:])]
                        return np.vstack((moments, grid))
                    solution = least_squares(residual, parameters, jac=jacobian, bounds=(lower, upper), x_scale='jac', max_nfev=600, ftol=1e-13, xtol=1e-13, gtol=1e-13)
                    parameters = solution.x
                    current_vectors, current_dimensions = unpack(parameters)
                    snapped = assignment(current_dimensions)
                    snapped_vectors = current_vectors*np.sqrt(column_scales[snapped]/column_scales[support])[:, None]
                    order = np.argsort(snapped)
                    snapped = snapped[order]
                    snapped_vectors = snapped_vectors[order]
                    for cutoff in (1e-4, 1e-6, 0):
                        _, snapped_vectors, _ = solver.optimizer.fit(snapped, snapped_vectors, cutoff, nfev=700)
                        if solver.optimizer.best_error < 1e-8:
                            return solver.optimizer.best_error
                    print('GRID', attempt, penalty, np.linalg.norm(solution.fun), solver.optimizer.best_error, flush=True)
                    if time.monotonic() > deadline:
                        return solver.optimizer.best_error
            return solver.optimizer.best_error

if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=2) as pool:
        jobs = {pool.submit(recover, variant): variant for variant in range(2)}
        for job in as_completed(jobs):
            print('GRID_DONE', jobs[job], job.result(), flush=True)
    from collect import collect
    collect()
