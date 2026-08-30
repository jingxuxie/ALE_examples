import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import time
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logsumexp


def configurations(count):
    indices = np.arange(1 << count, dtype=np.uint32)
    return 2.0 * ((indices[:, None] >> np.arange(count)) & 1) - 1.0


def regions(couplings):
    count = len(couplings)
    groups = [[site] for site in range(count)]
    threshold = max(0.25, 0.2 * np.max(np.abs(couplings)))
    edges = sorted(((abs(couplings[site, other]), site, other)
                    for site in range(count) for other in range(site)), reverse=True)
    for strength, site, other in edges:
        if strength < threshold:
            break
        first = next(group for group in groups if site in group)
        second = next(group for group in groups if other in group)
        if first is not second and len(first) + len(second) <= 8:
            first.extend(second)
            groups.remove(second)
    while len(groups) > 7:
        groups.sort(key=lambda group: (len(group), min(group)))
        groups[0].extend(groups[1])
        del groups[1]
    return sorted([sorted(group) for group in groups], key=min)


def logistic_fit(design, probability, positive):
    parameters = np.zeros(design.shape[1])
    for iteration in range(60):
        logits = design @ parameters
        predictions = expit(logits)
        gradient = design.T @ (probability * predictions - positive) + 1e-10 * parameters
        curvature = probability * predictions * (1 - predictions)
        hessian = design.T @ (curvature[:, None] * design) + 1e-10 * np.eye(len(parameters))
        if np.max(np.abs(gradient)) < 1e-11:
            break
        update = np.linalg.solve(hessian, gradient)
        step = min(1.0, 6.0 / max(6.0, np.abs(update).sum()))
        parameters -= step * update
    return parameters


class LocalMixture:
    def __init__(self, log_target, orders):
        self.count = len(orders[0])
        self.spins = configurations(self.count)
        self.target = np.exp(log_target)
        self.log_target = log_target
        self.orders = np.asarray(orders)
        self.components = len(orders)
        self.rows = []
        self.cols = []
        for site in range(self.count):
            self.rows.extend([site] * (site + 1))
            self.cols.extend(range(site + 1))
        self.rows = np.asarray(self.rows)
        self.cols = np.asarray(self.cols)
        self.size = len(self.rows)
        self.ordered = self.spins[:, self.orders].transpose(1, 0, 2)
        self.inputs = np.concatenate((np.ones((self.components, len(self.spins), 1)), self.ordered), axis=2)
        self.positive = (self.ordered + 1) * 0.5
        initial = []
        for component in range(self.components):
            parts = []
            for position in range(self.count):
                parts.append(logistic_fit(self.inputs[component, :, :position + 1], self.target,
                                          self.target * self.positive[component, :, position]))
            initial.extend(np.concatenate(parts))
        self.initial = np.asarray(initial)
        self.deadline = float('inf')
        self.best_loss = np.inf
        self.best_parameters = self.initial.copy()

    def evaluate(self, parameters, regularization=0.0, alpha=0.05, chi_weight=0.0002):
        if time.monotonic() > self.deadline:
            raise TimeoutError()
        matrix = np.zeros((self.components, self.count, self.count + 1))
        matrix[:, self.rows, self.cols] = parameters.reshape(self.components, self.size)
        logits = self.inputs @ matrix.transpose(0, 2, 1)
        prediction = expit(logits)
        component_logs = -np.logaddexp(0, -self.ordered * logits).sum(axis=2)
        component_probability = np.exp(component_logs)
        log_model = logsumexp(component_logs, axis=0) - np.log(self.components)
        probability = np.exp(log_model)
        difference = log_model - self.log_target
        reverse = probability @ difference
        forward = -self.target @ difference
        ratio = np.exp(np.minimum(50, self.log_target - log_model))
        chi = self.target @ ratio
        residual = component_probability / self.components * (difference + 1 - alpha * ratio - chi_weight * ratio ** 2)
        loss = reverse + alpha * forward + chi_weight * (chi - 1)
        if regularization:
            component_difference = component_logs - self.log_target
            loss += regularization * np.sum(component_probability * component_difference) / self.components
            residual += regularization * component_probability * (component_difference + 1) / self.components
        gradient = ((residual[:, :, None] * (self.positive - prediction)).transpose(0, 2, 1) @ self.inputs)
        excess = np.maximum(0, np.abs(matrix).sum(axis=2) - 58)
        loss += np.sum(excess ** 2) + 1e-9 * np.sum(parameters ** 2)
        gradient += 2 * excess[:, :, None] * np.sign(matrix)
        self.last = (float(reverse), float(1 / chi), float(forward))
        if np.isfinite(loss) and loss < self.best_loss:
            self.best_loss = loss
            self.best_parameters = parameters.copy()
        return loss, gradient[:, self.rows, self.cols].reshape(-1) + 2e-9 * parameters

    def fit(self, iterations=1000, regularization=0.0, alpha=0.05, deadline=float('inf')):
        self.deadline = deadline
        try:
            minimize(self.evaluate, self.initial, args=(regularization, alpha), method="L-BFGS-B", jac=True,
                     options={"maxiter": iterations, "ftol": 1e-12, "gtol": 1e-8, "maxcor": 20})
        except TimeoutError:
            pass
        self.parameters = self.best_parameters
        self.deadline = float('inf')
        self.evaluate(self.parameters, regularization, alpha)
        return self.last

    def artifact(self):
        weights = np.zeros((self.components, self.count, self.count))
        biases = np.zeros((self.components, self.count))
        vectors = self.parameters.reshape(self.components, self.size)
        for component, order in enumerate(self.orders):
            offset = 0
            for position, site in enumerate(order):
                biases[component, site] = vectors[component, offset]
                weights[component, site, order[:position]] = vectors[component, offset + 1:offset + position + 1]
                offset += position + 1
        return weights, biases
