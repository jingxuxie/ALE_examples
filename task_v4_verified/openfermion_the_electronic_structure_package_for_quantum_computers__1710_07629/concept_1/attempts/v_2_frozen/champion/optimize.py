import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import time
import numpy as np
from scipy.optimize import minimize


class OptimizationDeadline(Exception):
    pass


def cost(one_body, factors):
    weights = np.abs(factors).sum(axis=(1, 2))
    return np.abs(one_body).sum() + 0.5 * weights @ weights


def rotate(one_body, factors, orbital, auxiliary):
    rotated = orbital.T @ factors @ orbital
    return orbital.T @ one_body @ orbital, (auxiliary @ rotated.reshape(len(factors), -1)).reshape(factors.shape)


def candidates(one_body, factors):
    dimension = len(one_body)
    rank = len(factors)
    flat = factors.reshape(rank, -1)
    auxiliary = np.linalg.eigh(flat @ flat.T)[1].T
    canonical = (auxiliary @ flat).reshape(factors.shape)
    orbitals = [np.eye(dimension), np.linalg.eigh(one_body)[1],
                np.linalg.eigh(np.sum(factors @ factors, axis=0))[1]]
    orbitals.extend(np.linalg.eigh(factor)[1] for factor in canonical)
    results = []
    for orbital in orbitals:
        for mixing in (np.eye(rank), auxiliary):
            rotated_body, rotated_factors = rotate(one_body, factors, orbital, mixing)
            results.append((cost(rotated_body, rotated_factors), orbital, mixing))
    return sorted(results, key=lambda entry: entry[0])


class Objective:
    def __init__(self, one_body, factors, smoothing, deadline=None):
        self.one_body = one_body
        self.factors = factors
        self.smoothing = smoothing
        self.dimension = len(one_body)
        self.rank = len(factors)
        self.orbital_indices = np.triu_indices(self.dimension, 1)
        self.auxiliary_indices = np.triu_indices(self.rank, 1)
        self.split = len(self.orbital_indices[0])
        self.size = self.split + len(self.auxiliary_indices[0])
        self.evaluations = 0
        self.deadline = deadline
        self.best_value = float('inf')
        self.best_parameters = np.zeros(self.size)

    def matrices(self, parameters):
        skew_orbital = np.zeros((self.dimension, self.dimension))
        skew_orbital[self.orbital_indices] = parameters[:self.split]
        skew_auxiliary = np.zeros((self.rank, self.rank))
        skew_auxiliary[self.auxiliary_indices] = parameters[self.split:]
        inverse_orbital = np.linalg.inv(np.eye(self.dimension) - skew_orbital + skew_orbital.T)
        inverse_auxiliary = np.linalg.inv(np.eye(self.rank) - skew_auxiliary + skew_auxiliary.T)
        return 2 * inverse_orbital - np.eye(self.dimension), 2 * inverse_auxiliary - np.eye(self.rank), inverse_orbital, inverse_auxiliary

    def __call__(self, parameters):
        if self.deadline is not None and time.monotonic() >= self.deadline:
            raise OptimizationDeadline
        self.evaluations += 1
        orbital, auxiliary, inverse_orbital, inverse_auxiliary = self.matrices(parameters)
        rotated_body = orbital.T @ self.one_body @ orbital
        rotated_factors = orbital.T @ self.factors @ orbital
        mixed = (auxiliary @ rotated_factors.reshape(self.rank, -1)).reshape(self.factors.shape)
        smooth_body = np.sqrt(rotated_body * rotated_body + self.smoothing ** 2)
        smooth_factors = np.sqrt(mixed * mixed + self.smoothing ** 2)
        weights = smooth_factors.sum(axis=(1, 2))
        value = smooth_body.sum() + 0.5 * weights @ weights
        if value < self.best_value:
            self.best_value = value
            self.best_parameters = parameters.copy()
        body_gradient = rotated_body / smooth_body
        mixed_gradient = weights[:, None, None] * mixed / smooth_factors
        factor_gradient = (auxiliary.T @ mixed_gradient.reshape(self.rank, -1)).reshape(self.factors.shape)
        orbital_gradient = 2 * (self.one_body @ orbital @ body_gradient + np.sum(self.factors @ orbital @ factor_gradient, axis=0))
        auxiliary_gradient = mixed_gradient.reshape(self.rank, -1) @ rotated_factors.reshape(self.rank, -1).T
        orbital_gradient = 2 * inverse_orbital.T @ orbital_gradient @ inverse_orbital.T
        auxiliary_gradient = 2 * inverse_auxiliary.T @ auxiliary_gradient @ inverse_auxiliary.T
        gradient = np.concatenate(((orbital_gradient - orbital_gradient.T)[self.orbital_indices],
                                   (auxiliary_gradient - auxiliary_gradient.T)[self.auxiliary_indices]))
        return value, gradient


def refine(one_body, factors, orbital, auxiliary, schedule, maxiter=200, verbose=False, deadline=None):
    total_evaluations = 0
    started = time.monotonic()
    for stage, smoothing in enumerate(schedule):
        if deadline is not None and time.monotonic() >= deadline:
            break
        rotated_body, rotated_factors = rotate(one_body, factors, orbital, auxiliary)
        objective = Objective(rotated_body, rotated_factors, smoothing, deadline=deadline)
        iterations = maxiter if isinstance(maxiter, int) else maxiter[stage]
        iteration_count = 0
        try:
            solution = minimize(objective, np.zeros(objective.size), jac=True, method='L-BFGS-B',
                                options={'maxiter': iterations, 'ftol': 1e-11, 'gtol': 1e-6, 'maxls': 30, 'maxcor': 20})
            parameters = solution.x
            iteration_count = solution.nit
        except OptimizationDeadline:
            parameters = objective.best_parameters
        change_orbital, change_auxiliary, _, _ = objective.matrices(parameters)
        orbital = orbital @ change_orbital
        auxiliary = change_auxiliary @ auxiliary
        total_evaluations += objective.evaluations
        if verbose:
            print(' stage', smoothing, cost(*rotate(one_body, factors, orbital, auxiliary)), iteration_count,
                  objective.evaluations, time.monotonic() - started, flush=True)
    return cost(*rotate(one_body, factors, orbital, auxiliary)), orbital, auxiliary, total_evaluations
