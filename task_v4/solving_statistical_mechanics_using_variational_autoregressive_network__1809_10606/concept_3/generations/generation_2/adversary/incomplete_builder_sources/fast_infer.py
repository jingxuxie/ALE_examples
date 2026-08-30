import time

import numpy as np
from scipy.special import logsumexp

from infer import Likelihood, load_data


class FastLikelihood:
    def __init__(self, likelihood):
        self.signs = likelihood.signs.numpy().copy()
        self.states = likelihood.states.numpy().copy()
        self.vertical_products = likelihood.vertical_products.numpy().copy()
        self.statistics = likelihood.statistics.numpy().copy()
        self.components = [{key: value.numpy().copy() for key, value in component.items()} for component in likelihood.components]
        self.betas = likelihood.betas.copy()
        self.count = likelihood.count
        self.parameter_count = 268

    def partition(self, values, beta, moments=True):
        couplings = values[:172] * self.signs
        vertical = couplings[:84].reshape(12, 7)
        horizontal = couplings[84:].reshape(11, 8)
        fields = values[172:].reshape(12, 8)
        unary_energy = beta * (vertical @ self.vertical_products.T + fields @ self.states.T)
        shifts = np.max(unary_energy, axis=1)
        unary = np.exp(unary_energy - shifts[:, None])
        same = np.exp(beta * horizontal)
        different = 1 / same
        forward = np.empty((12, 256))
        weights = unary[0]
        normalization = weights.sum()
        forward[0] = weights / normalization
        log_partition = np.log(normalization) + shifts[0]
        stages = np.empty((11, 9, 256))
        for column in range(1, 12):
            stages[column - 1, 0] = forward[column - 1]
            for row in range(8):
                blocks = stages[column - 1, row].reshape(-1, 2, 1 << row)
                result = stages[column - 1, row + 1].reshape(-1, 2, 1 << row)
                result[:, 0] = same[column - 1, row] * blocks[:, 0] + different[column - 1, row] * blocks[:, 1]
                result[:, 1] = different[column - 1, row] * blocks[:, 0] + same[column - 1, row] * blocks[:, 1]
            weights = unary[column] * stages[column - 1, 8]
            normalization = weights.sum()
            log_partition += np.log(normalization) + shifts[column]
            forward[column] = weights / normalization
        if not moments:
            return log_partition
        marginals = np.empty((12, 256))
        marginals[-1] = forward[-1]
        backward = np.ones(256)
        horizontal_moments = np.empty((11, 8))
        for column in range(10, -1, -1):
            right = unary[column + 1] * backward
            normalization = np.dot(stages[column, 8], right)
            sensitivity = right / normalization
            for row in range(7, -1, -1):
                blocks = stages[column, row].reshape(-1, 2, 1 << row)
                sensitive_blocks = sensitivity.reshape(-1, 2, 1 << row)
                horizontal_moments[column, row] = same[column, row] * np.sum(sensitive_blocks[:, 0] * blocks[:, 0] + sensitive_blocks[:, 1] * blocks[:, 1]) - different[column, row] * np.sum(sensitive_blocks[:, 0] * blocks[:, 1] + sensitive_blocks[:, 1] * blocks[:, 0])
                new_sensitivity = np.empty_like(sensitive_blocks)
                new_sensitivity[:, 0] = same[column, row] * sensitive_blocks[:, 0] + different[column, row] * sensitive_blocks[:, 1]
                new_sensitivity[:, 1] = different[column, row] * sensitive_blocks[:, 0] + same[column, row] * sensitive_blocks[:, 1]
                sensitivity = new_sensitivity.reshape(256)
            backward = sensitivity / sensitivity.max()
            marginal = forward[column] * backward
            marginals[column] = marginal / marginal.sum()
        gradient = np.concatenate(((marginals @ self.vertical_products).ravel(), horizontal_moments.ravel(), (marginals @ self.states).ravel()))
        gradient[:172] *= self.signs
        gradient *= beta
        return log_partition, gradient

    def evaluate(self, values, gradient=True):
        couplings = values[:172] * self.signs
        fields = values[172:]
        energies = []
        for component in self.components:
            energy = component['hidden'] @ fields[component['sites']]
            energy += component['internal_features'] @ couplings[component['internal_indices']]
            energy = energy[None, :] + (component['cross_boundary'] * couplings[component['cross_indices']]) @ component['cross_hidden']
            energies.append(energy)
        total = 0.0
        total_gradient = np.zeros(self.parameter_count)
        for condition, beta in enumerate(self.betas):
            numerator = beta * np.dot(self.statistics[condition], values)
            numerator_gradient = beta * self.statistics[condition].copy()
            for component, energy in zip(self.components, energies):
                logits = beta * energy
                log_normalization = logsumexp(logits, axis=1)
                numerator += component['weights'][condition] @ log_normalization
                if gradient:
                    posterior = np.exp(logits - log_normalization[:, None]) * component['weights'][condition][:, None]
                    hidden_weights = posterior.sum(axis=0)
                    numerator_gradient[172 + component['sites']] += beta * (hidden_weights @ component['hidden'])
                    internal = component['internal_indices']
                    numerator_gradient[internal] += beta * (hidden_weights @ component['internal_features']) * self.signs[internal]
                    cross = component['cross_indices']
                    numerator_gradient[cross] += beta * np.sum((component['cross_boundary'].T @ posterior) * component['cross_hidden'], axis=1) * self.signs[cross]
            if gradient:
                log_partition, partition_gradient = self.partition(values, beta)
                total_gradient += partition_gradient - numerator_gradient
            else:
                log_partition = self.partition(values, beta, moments=False)
            total += log_partition - numerator
        if gradient:
            return total / len(self.betas), total_gradient / len(self.betas)
        return total / len(self.betas)


if __name__ == '__main__':
    configurations, betas, spec = load_data()
    slow = Likelihood(configurations, betas, spec)
    fast = FastLikelihood(slow)
    values = np.load('fit_checkpoint.npz')['theta']
    value, gradient = slow.evaluate(values)
    fast_value, fast_gradient = fast.evaluate(values)
    print('value error', fast_value - value)
    print('gradient error', np.max(np.abs(fast_gradient - gradient)))
    assert abs(value - fast_value) < 1e-10
    assert np.max(np.abs(fast_gradient - gradient)) < 1e-10
    start = time.monotonic()
    for iteration in range(100):
        fast.evaluate(values)
    print('fast evaluation seconds', (time.monotonic() - start) / 100)
