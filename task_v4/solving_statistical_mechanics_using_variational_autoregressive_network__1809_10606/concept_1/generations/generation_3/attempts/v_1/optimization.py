import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import sys
import time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import minimize
from scipy.special import expit, logsumexp
from cube import linear_logits, linear_moments, quadratic_moments


class Finished(Exception):
    pass


class FullRefinement:
    def __init__(self, instance, model, seconds=85, alpha=0.05, chi_weight=0.002, precondition=True, threads=4, verbose=False, ridge=3e-4, distribution=None):
        self.started = time.monotonic()
        self.deadline = self.started + seconds
        self.alpha = alpha
        self.chi_weight = chi_weight
        self.verbose = verbose
        self.count = instance['n']
        self.components = len(model['mixing'])
        self.executor = ThreadPoolExecutor(max_workers=threads)
        self.orders = np.asarray(model['orders'])
        if distribution is None:
            from distribution import Distribution
            distribution = Distribution(instance)
        self.spins = distribution.spins
        self.log_target = distribution.log_target
        self.target = distribution.target
        self.initial = []
        self.transforms = []
        self.slices = []
        self.initial_mixing = np.log(np.asarray(model['mixing']))
        weights = np.asarray(model['weights'])
        biases = np.asarray(model['biases'])
        offset = 0
        for component, order in enumerate(self.orders):
            parameters = []
            transforms = []
            slices = []
            joint = np.zeros(1)
            for position, site in enumerate(order):
                values = np.concatenate(([biases[component, site]], weights[component, site, order[:position]]))
                parameters.append(values)
                slices.append(slice(offset, offset + position + 1))
                offset += position + 1
                logits = linear_logits(values)
                if precondition:
                    predicted = expit(logits)
                    curvature = np.exp(joint) * predicted * (1 - predicted)
                    hessian = quadratic_moments(curvature)
                    hessian.flat[::position + 2] += ridge
                    factor = cholesky(hessian, lower=True, check_finite=False)
                    transforms.append(solve_triangular(factor.T, np.eye(position + 1), lower=False, check_finite=False))
                else:
                    transforms.append(np.eye(position + 1))
                normalizer = np.logaddexp(0, logits)
                joint = np.concatenate((joint - normalizer, joint + logits - normalizer))
            self.initial.append(parameters)
            self.transforms.append(transforms)
            self.slices.append(slices)
        self.size = offset + self.components
        self.best_objective = np.inf
        self.best_feasible = False
        self.best_parameters = np.zeros(self.size)
        self.best_metrics = None
        self.calls = 0

    def to_original(self, values, order):
        return values.reshape((2,) * self.count).transpose(np.argsort(order[::-1])[::-1]).reshape(-1)

    def to_ordered(self, values, order):
        return values.reshape((2,) * self.count).transpose(self.count - 1 - order[::-1]).reshape(-1)

    def unpack(self, vector):
        parameters = []
        originals = []
        for initial, transforms, slices in zip(self.initial, self.transforms, self.slices):
            component = [values + transform @ vector[selection] for values, transform, selection in zip(initial, transforms, slices)]
            originals.append(component)
            parameters.append([values * min(1, 59 / max(1, np.abs(values).sum())) for values in component])
        return parameters, originals

    def evaluate(self, vector):
        if time.monotonic() > self.deadline:
            raise Finished()
        parameters, originals = self.unpack(vector)
        log_mixing = self.initial_mixing + vector[-self.components:]
        log_mixing -= logsumexp(log_mixing)
        mixing = np.exp(log_mixing)
        def forward(arguments):
            order, component = arguments
            joint = np.zeros(1)
            predicted = []
            for values in component:
                logits = linear_logits(values)
                predicted.append(expit(logits))
                normalizer = np.logaddexp(0, logits)
                joint = np.concatenate((joint - normalizer, joint + logits - normalizer))
            return self.to_original(joint, order), predicted
        results = list(self.executor.map(forward, zip(self.orders, parameters)))
        component_logs = [result[0] for result in results]
        probabilities = [result[1] for result in results]
        component_logs = np.asarray(component_logs) + log_mixing[:, None]
        direct_probability = np.min(np.max(component_logs, axis=0)) > -700
        if direct_probability:
            component_probability = np.exp(component_logs)
            probability = component_probability.sum(axis=0)
            log_model = np.log(probability)
        else:
            log_model = logsumexp(component_logs, axis=0)
            probability = np.exp(log_model)
        difference = log_model - self.log_target
        self.current_log_model = log_model
        reverse = probability @ difference
        forward = -self.target @ difference
        log_chi = logsumexp(2 * self.log_target - log_model)
        chi = np.exp(min(50, log_chi))
        tilt = np.exp(2 * self.log_target - log_model - log_chi) * chi
        residual = probability * (difference + 1) - self.alpha * self.target - self.chi_weight * tilt
        objective = reverse + self.alpha * forward + self.chi_weight * (chi * (1 + max(0, log_chi - 50)) - 1)
        gradient = np.zeros(self.size)
        mix_gradient = np.zeros(self.components)
        def backward(component):
            order = self.orders[component]
            if direct_probability:
                local_residual = (component_probability[component] / probability) * residual
            else:
                local_residual = np.exp(component_logs[component] - log_model) * residual
            mixing_gradient = local_residual.sum()
            local_residual = self.to_ordered(local_residual, order)
            for position in range(self.count - 1, -1, -1):
                children = local_residual.reshape(2, -1)
                parent = children.sum(axis=0)
                logit_gradient = children[1] - parent * probabilities[component][position]
                raw_gradient = linear_moments(logit_gradient)
                original = originals[component][position]
                norm = np.abs(original).sum()
                if norm > 59:
                    raw_gradient = 59 / norm * (raw_gradient - np.sign(original) * (raw_gradient @ original) / norm)
                gradient[self.slices[component][position]] = self.transforms[component][position].T @ raw_gradient
                local_residual = parent
            return mixing_gradient
        mix_gradient[:] = list(self.executor.map(backward, range(self.components)))
        gradient[-self.components:] = mix_gradient - mixing * mix_gradient.sum()
        feasible = log_chi <= -np.log(0.30)
        improve = (feasible and not self.best_feasible) or (feasible == self.best_feasible and objective < self.best_objective)
        if np.isfinite(objective) and improve:
            self.best_feasible = feasible
            self.best_objective = objective
            self.best_parameters = vector.copy()
            self.best_metrics = (float(reverse), float(np.exp(-log_chi)))
        self.calls += 1
        if self.verbose and self.calls % 10 == 0:
            print('refinement', self.calls, self.best_metrics, 'elapsed', time.monotonic() - self.started, file=sys.stderr, flush=True)
        return objective, gradient

    def fit(self, iterations=1000, warm_seconds=0, reverse_seconds=0):
        try:
            self.evaluate(np.zeros(self.size))
            if self.verbose:
                print('initial', self.best_metrics, 'setup', time.monotonic() - self.started, file=sys.stderr, flush=True)
            initial_vector = np.zeros(self.size)
            if warm_seconds > 0:
                from warm import warm_start
                candidate = warm_start(self, seconds=warm_seconds)
                self.evaluate(candidate)
                initial_vector = self.best_parameters.copy()
            if reverse_seconds > 0:
                from warm import warm_start
                self.evaluate(initial_vector)
                candidate = warm_start(self, seconds=reverse_seconds, samples=16384,
                                       initial=initial_vector, mode='reverse')
                self.evaluate(candidate)
                initial_vector = self.best_parameters.copy()
            minimize(self.evaluate, initial_vector, method='L-BFGS-B', jac=True,
                     options={'maxiter': iterations, 'maxcor': 20, 'ftol': 1e-11, 'gtol': 1e-7, 'maxls': 12})
        except Finished:
            pass
        finally:
            self.executor.shutdown(wait=True)
        parameters, originals = self.unpack(self.best_parameters)
        weights = np.zeros((self.components, self.count, self.count))
        biases = np.zeros((self.components, self.count))
        for component, order in enumerate(self.orders):
            for position, site in enumerate(order):
                values = parameters[component][position]
                biases[component, site] = values[0]
                weights[component, site, order[:position]] = values[1:]
        log_mixing = self.initial_mixing + self.best_parameters[-self.components:]
        mixing = np.maximum(np.exp(log_mixing - logsumexp(log_mixing)), 1e-100)
        mixing /= mixing.sum()
        if self.verbose:
            print('final', self.best_metrics, 'elapsed', time.monotonic() - self.started, file=sys.stderr, flush=True)
        return {'mixing': mixing.tolist(), 'weights': weights.tolist(), 'biases': biases.tolist(), 'orders': self.orders.tolist()}
