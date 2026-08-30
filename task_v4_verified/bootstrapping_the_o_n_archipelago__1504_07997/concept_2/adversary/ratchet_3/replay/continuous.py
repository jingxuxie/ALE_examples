import json
import os
import sys
import time

import numpy as np
from scipy.optimize import least_squares, linear_sum_assignment

from improve import Optimizer, SOURCE, load_seed, products


def recover(instance, seconds):
    saved = load_seed(instance['id'])
    if not saved:
        print('NO SEED', instance['id'], flush=True)
        return
    solver = Optimizer(instance)
    support = np.array([atom['index'] for atom in saved['atoms']])
    vectors = np.array([atom['ope'] for atom in saved['atoms']])
    solver.evaluate(support, vectors)
    if solver.best_error < 1e-8:
        return
    end = time.monotonic() + seconds
    metadata = instance['candidates']
    dimensions = np.array([candidate['dimension'] for candidate in metadata])
    spins = np.array([candidate['spin'] for candidate in metadata])
    scales = np.array([candidate['column_scale'] for candidate in metadata])
    probes = np.array([probe['t'] for probe in instance['probes']])[:, None]
    orders = np.array([probe['order'] for probe in instance['probes']])[:, None]
    initial_dimensions = dimensions[support]
    base = solver.design[:, support]
    count = len(support)
    allowed = np.where(np.isin(spins, spins[support]))[0]
    lower_dimensions = np.array([min(dimensions[(spins == spin) & (np.arange(len(spins)) != 0)]) for spin in spins[support[1:]]])
    upper_dimensions = np.array([max(dimensions[spins == spin]) for spin in spins[support[1:]]])
    lower = np.r_[np.full(2 * count - 1, -3.99), lower_dimensions]
    upper = np.r_[np.full(2 * count - 1, 3.99), upper_dimensions]
    parameters = np.r_[vectors.ravel()[1:], initial_dimensions[1:]]
    rng = np.random.default_rng(731)
    best_parameters = parameters.copy()
    best_continuous = np.inf

    def unpack(current):
        return np.r_[solver.shared, current[:2 * count - 1]].reshape(count, 2), np.r_[initial_dimensions[0], current[2 * count - 1:]]

    def kernel(current_dimensions):
        return base * np.exp(-probes * (current_dimensions - initial_dimensions)) * (current_dimensions / initial_dimensions) ** orders

    for attempt in range(20):
        if attempt:
            parameters = best_parameters.copy()
            parameters[2 * count - 1:] += rng.normal(0, 0.08 if attempt % 3 else 0.4, count - 1)
            parameters[1:2 * count - 1] += rng.normal(0, 0.03, 2 * count - 2)
        parameters = np.clip(parameters, lower + 1e-10, upper - 1e-10)
        for cutoff in (1e-4, 1e-6, 1e-8):
            weights = []
            observations = []
            for component in range(3):
                matrix = solver.design[:, allowed] / solver.scales[:, component, None]
                left, singular, right = np.linalg.svd(matrix, full_matrices=False)
                weight = left.T / np.maximum(singular, singular[0] * cutoff)[:, None]
                weight = weight / solver.scales[:, component]
                weights.append(weight)
                observations.append(weight @ solver.target[:, component])
            weights = np.array(weights)
            observations = np.array(observations)

            def residual(current):
                current_vectors, current_dimensions = unpack(current)
                prediction = kernel(current_dimensions) @ products(current_vectors)
                return (np.einsum('crm,mc->cr', weights, prediction) - observations).ravel()

            def jacobian(current):
                current_vectors, current_dimensions = unpack(current)
                current_kernel = kernel(current_dimensions)
                transformed = np.einsum('crm,mk->crk', weights, current_kernel)
                jac = np.zeros((3, transformed.shape[1], count, 2))
                jac[0, :, :, 0] = 2 * transformed[0] * current_vectors[:, 0]
                jac[1, :, :, 0] = transformed[1] * current_vectors[:, 1]
                jac[1, :, :, 1] = transformed[1] * current_vectors[:, 0]
                jac[2, :, :, 1] = 2 * transformed[2] * current_vectors[:, 1]
                derivative_kernel = current_kernel * (-probes + orders / current_dimensions)
                derivative_dimensions = np.einsum('crm,mk,kc->crk', weights, derivative_kernel, products(current_vectors))[:, :, 1:]
                return np.c_[jac.reshape(3 * transformed.shape[1], -1)[:, 1:], derivative_dimensions.reshape(3 * transformed.shape[1], -1)]

            solution = least_squares(residual, parameters, jac=jacobian, bounds=(lower, upper), x_scale='jac', max_nfev=1200, ftol=1e-12, xtol=1e-12, gtol=1e-12)
            parameters = solution.x
            current_vectors, current_dimensions = unpack(parameters)
            error = np.max(np.abs((kernel(current_dimensions) @ products(current_vectors) - solver.target) / solver.scales))
            print('CONTINUOUS', instance['id'], attempt, cutoff, error, solution.nfev, list(zip(spins[support].tolist(), np.round(current_dimensions, 6).tolist())), flush=True)
            if error < best_continuous:
                best_continuous = error
                best_parameters = parameters.copy()
            costs = np.abs(current_dimensions[:, None] - dimensions[None, :])
            costs[spins[support, None] != spins[None, :]] = 1000
            costs[1:, 0] = 1000
            positions, snapped = linear_sum_assignment(costs)
            snapped_vectors = current_vectors * np.sqrt(scales[snapped] / scales[support])[:, None]
            order = np.argsort(snapped)
            snapped = snapped[order]
            snapped_vectors = snapped_vectors[order]
            for conditioning in (1e-4, 1e-6, 1e-8):
                _, snapped_vectors, _ = solver.fit(snapped, snapped_vectors, conditioning, nfev=600)
                if solver.best_error < 1e-8:
                    return
            if time.monotonic() > end:
                return


if __name__ == '__main__':
    instances = json.loads(SOURCE.read_text())['instances']
    for selected in map(int, sys.argv[1:]):
        recover(instances[selected], 240)
