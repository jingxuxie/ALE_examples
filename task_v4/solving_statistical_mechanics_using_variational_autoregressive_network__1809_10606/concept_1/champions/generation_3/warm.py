import time
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logsumexp


class WarmDeadline(Exception):
    pass


def warm_start(optimizer, seconds=25, samples=32768, initial=None, mode='forward'):
    deadline = min(optimizer.deadline - 5, time.monotonic() + seconds)
    selected = np.argpartition(optimizer.target, -samples)[-samples:]
    tail_coefficient = 0.
    if mode == 'reverse':
        selected = np.union1d(selected, np.argpartition(optimizer.current_log_model, -samples)[-samples:])
        outside = np.ones(len(optimizer.target), dtype=bool)
        outside[selected] = False
        outside_model = optimizer.current_log_model[outside]
        outside_target = optimizer.log_target[outside]
        outside_probability = np.exp(outside_model)
        residual = (outside_probability * (outside_model - outside_target + 1)
                    - optimizer.alpha * np.exp(outside_target)
                    - optimizer.chi_weight * np.exp(np.minimum(50, 2 * outside_target - outside_model)))
        tail_coefficient = residual.sum() / max(1e-20, outside_probability.sum())
    probability = optimizer.target[selected].copy()
    if mode == 'forward':
        probability /= probability.sum()
    target_logs = optimizer.log_target[selected]
    spins = optimizer.spins[selected]
    inputs = [np.ascontiguousarray(np.column_stack((np.ones(len(selected)), spins[:, order])))
              for order in optimizer.orders]
    positive = [(design[:, 1:] + 1) * .5 for design in inputs]
    best_value = float('inf')
    best_vector = np.zeros(optimizer.size) if initial is None else initial.copy()
    calls = 0

    def evaluate(vector):
        nonlocal best_value, best_vector, calls
        if time.monotonic() >= deadline:
            raise WarmDeadline()
        parameters, originals = optimizer.unpack(vector)
        log_mixing = optimizer.initial_mixing + vector[-optimizer.components:]
        log_mixing -= logsumexp(log_mixing)
        mixing = np.exp(log_mixing)

        def forward(component):
            matrix = np.zeros((optimizer.count, optimizer.count + 1))
            for position, values in enumerate(parameters[component]):
                matrix[position, :position + 1] = values
            logits = inputs[component] @ matrix.T
            logs = -np.logaddexp(0, -(2 * positive[component] - 1) * logits).sum(axis=1)
            return logs, expit(logits)

        predictions = list(optimizer.executor.map(forward, range(optimizer.components)))
        logs = np.asarray([entry[0] for entry in predictions]) + log_mixing[:, None]
        if np.min(np.max(logs, axis=0)) > -700:
            component_probability = np.exp(logs)
            model_probability = component_probability.sum(axis=0)
            model = np.log(model_probability)
            responsibility = component_probability / model_probability * probability
        else:
            model = logsumexp(logs, axis=0)
            responsibility = np.exp(logs - model) * probability
        if mode == 'forward':
            objective = float(-probability @ model)
        else:
            model_probability = np.exp(model)
            difference = model - target_logs
            log_chi = logsumexp(2 * target_logs - model)
            chi = np.exp(min(50, log_chi))
            tilt = np.exp(2 * target_logs - model - log_chi) * chi
            residual = (model_probability * (difference + 1 - tail_coefficient)
                        - optimizer.alpha * probability - optimizer.chi_weight * tilt)
            responsibility = -np.exp(logs - model) * residual
            objective = float(model_probability @ difference - optimizer.alpha * (probability @ difference)
                              + optimizer.chi_weight * chi + tail_coefficient * (1 - model_probability.sum()))
        gradient = np.zeros_like(vector)

        def backward(component):
            residual = responsibility[component, :, None] * (predictions[component][1] - positive[component])
            raw = residual.T @ inputs[component]
            for position in range(optimizer.count):
                raw_gradient = raw[position, :position + 1]
                original = originals[component][position]
                norm = np.abs(original).sum()
                if norm > 59:
                    raw_gradient = 59 / norm * (raw_gradient - np.sign(original) * (raw_gradient @ original) / norm)
                gradient[optimizer.slices[component][position]] = optimizer.transforms[component][position].T @ raw_gradient

        list(optimizer.executor.map(backward, range(optimizer.components)))
        gradient[-optimizer.components:] = mixing * responsibility.sum() - responsibility.sum(axis=1)
        if np.isfinite(objective) and objective < best_value:
            best_value = objective
            best_vector = vector.copy()
        calls += 1
        return objective, gradient

    try:
        minimize(evaluate, best_vector, jac=True, method='L-BFGS-B',
                 options={'maxiter': 1000, 'maxcor': 30, 'ftol': 1e-12, 'gtol': 1e-7, 'maxls': 12})
    except WarmDeadline:
        pass
    if optimizer.verbose:
        print('warm start', mode, len(selected), calls, best_value, 'elapsed', time.monotonic() - optimizer.started, flush=True)
    return best_vector
