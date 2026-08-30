import os

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'

import json
import sys
import time

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize
from scipy.special import logsumexp, ndtr, ndtri
from scipy.stats import qmc


def walsh(values):
    output = np.array(values, dtype=float, copy=True)
    width = 1
    while width < output.shape[-1]:
        blocks = output.reshape(output.shape[:-1] + (-1, 2 * width))
        left = blocks[..., :width].copy()
        right = blocks[..., width:].copy()
        blocks[..., :width] = left + right
        blocks[..., width:] = left - right
        width *= 2
    return output


class Model:
    def __init__(self, spec):
        self.bounds = np.log([channel['rate_bounds'] for channel in spec['channels']])
        self.exposures = np.array([action['exposures'] for action in spec['actions']])
        self.weights = np.array([action['mode_weights'] for action in spec['actions']])
        masks = np.array([channel['masks'] for channel in spec['channels']])
        self.state_count = 1 << spec['detector_count']
        parity = np.array([index.bit_count() % 2 for index in range(self.state_count)])
        first = parity[masks[:, 0, None] & np.arange(self.state_count)]
        second = parity[masks[:, 1, None] & np.arange(self.state_count)]
        self.both = np.asarray(first * second, dtype=float)
        self.first_only = np.asarray(first * (1 - second), dtype=float)
        self.second_only = np.asarray((1 - first) * second, dtype=float)
        alternate = np.array([action['alternate_probability'] for action in spec['actions']])
        with np.errstate(divide='ignore'):
            self.log_alternate = np.log(alternate)[:, None, :]
            self.log_primary = np.log1p(-alternate)[:, None, :]
        self.groups = np.array([[channel['family'] == family for channel in spec['channels']]
                                for family in ('boundary', 'bulk', 'hook', 'rare')], dtype=float)
        self.groups /= self.groups.sum(axis=1, keepdims=True)

    def distribution(self, log_rates, gradient=False):
        scaled = 2 * self.exposures * np.exp(log_rates)[None, None, :]
        first_factor = np.logaddexp(self.log_alternate, self.log_primary - scaled)
        second_factor = np.logaddexp(self.log_primary, self.log_alternate - scaled)
        log_products = (-scaled @ self.both + first_factor @ self.first_only
                        + second_factor @ self.second_only)
        products = np.exp(log_products)
        spectrum = np.sum(self.weights[:, :, None] * products, axis=1)
        probability = np.maximum(walsh(spectrum) / self.state_count, 1e-15)
        if not gradient:
            return probability
        first_derivative = -scaled * np.exp(self.log_primary - scaled - first_factor)
        second_derivative = -scaled * np.exp(self.log_alternate - scaled - second_factor)
        logarithmic_derivative = (-scaled[..., None] * self.both
                                  + first_derivative[..., None] * self.first_only
                                  + second_derivative[..., None] * self.second_only)
        derivative = np.sum(self.weights[:, :, None, None] * products[:, :, None, :]
                            * logarithmic_derivative, axis=1)
        return probability, walsh(derivative) / self.state_count

    def log_likelihood_batch(self, counts, points):
        values = np.empty(len(points))
        channel_count = len(self.bounds)
        for start in range(0, len(points), 64):
            batch = points[start:start + 64]
            scaled = 2 * self.exposures[None] * np.exp(batch)[:, None, None, :]
            first_factor = np.logaddexp(self.log_alternate[None], self.log_primary[None] - scaled)
            second_factor = np.logaddexp(self.log_primary[None], self.log_alternate[None] - scaled)
            log_products = (-scaled.reshape(-1, channel_count) @ self.both
                            + first_factor.reshape(-1, channel_count) @ self.first_only
                            + second_factor.reshape(-1, channel_count) @ self.second_only)
            products = np.exp(log_products.reshape(len(batch), len(self.weights), 2, self.state_count))
            spectrum = np.sum(self.weights[None, :, :, None] * products, axis=2)
            probability = np.maximum(walsh(spectrum) / self.state_count, 1e-15)
            values[start:start + len(batch)] = np.sum(counts[None] * np.log(probability), axis=(1, 2))
        return values

    def fit(self, counts, initial=None):
        start = self.bounds.mean(axis=1) if initial is None else np.asarray(initial)
        total = max(float(counts.sum()), 1)

        def objective(log_rates):
            probability, derivative = self.distribution(log_rates, True)
            value = -np.sum(counts * np.log(probability)) / total
            gradient = -np.einsum('as,aks->k', counts / probability, derivative) / total
            return value, gradient

        result = minimize(objective, start, method='L-BFGS-B', jac=True,
                          bounds=self.bounds.tolist(),
                          options={'maxiter': 150, 'ftol': 2e-13, 'gtol': 1e-9, 'maxls': 25})
        return result.x

    def fisher(self, log_rates):
        probability, derivative = self.distribution(log_rates, True)
        normalized = derivative / np.sqrt(probability[:, None])
        return normalized @ normalized.transpose(0, 2, 1)


def design(model, fitted, spent, budget, prior_information=None):
    fisher = model.fisher(fitted)
    action_count, channel_count = fisher.shape[:2]
    identity = np.eye(channel_count)
    if prior_information is None:
        base = np.einsum('a,akl->kl', spent / budget, fisher)
    else:
        base = prior_information / budget
    base = base + 1e-10 * identity
    fraction = 1 - spent.sum() / budget

    def objective(allocation):
        information = base + np.einsum('a,akl->kl', allocation * fraction, fisher)
        inverse = cho_solve(cho_factor(information, lower=True, check_finite=False),
                            identity, check_finite=False)
        variances = model.groups @ np.diag(inverse)
        value = np.power(variances, 0.8).sum()
        channel_weights = (0.8 * np.power(variances, -0.2)) @ model.groups
        sensitivity = (inverse * channel_weights[None, :]) @ inverse
        gradient = -fraction * np.einsum('akl,kl->a', fisher, sensitivity)
        return value, gradient

    start = np.full(action_count, 1 / action_count)
    scale = objective(start)[0]

    def normalized_objective(allocation):
        value, gradient = objective(allocation)
        return value / scale, gradient / scale

    result = minimize(normalized_objective, start, jac=True, method='SLSQP',
                      bounds=[(0, 1)] * action_count,
                      constraints=[{'type': 'eq', 'fun': lambda allocation: allocation.sum() - 1,
                                    'jac': lambda allocation: np.ones(action_count)}],
                      options={'maxiter': 120, 'ftol': 1e-9})
    allocation = np.maximum(result.x, 0)
    if not np.all(np.isfinite(allocation)) or allocation.sum() <= 0:
        allocation = start
    return allocation / allocation.sum()


def posterior(model, counts, fitted, power=12, moments=False):
    probability, derivative = model.distribution(fitted, True)
    score = np.einsum('as,aks->k', counts / probability, derivative)
    dimension = len(fitted)
    information = np.empty((dimension, dimension))
    for channel in range(dimension):
        direction = np.zeros(dimension)
        direction[channel] = 0.0001
        plus_probability, plus_derivative = model.distribution(fitted + direction, True)
        minus_probability, minus_derivative = model.distribution(fitted - direction, True)
        plus_score = np.einsum('as,aks->k', counts / plus_probability, plus_derivative)
        minus_score = np.einsum('as,aks->k', counts / minus_probability, minus_derivative)
        information[:, channel] = (minus_score - plus_score) / 0.0002
    information = (information + information.T) * 0.5
    if np.linalg.eigvalsh(information)[0] <= 0:
        information = np.einsum('a,akl->kl', counts.sum(axis=1), model.fisher(fitted))
    covariance = np.linalg.inv(information)
    center = fitted + covariance @ score
    distances = np.minimum(fitted - model.bounds[:, 0], model.bounds[:, 1] - fitted)
    order = np.argsort(distances / np.sqrt(np.diag(covariance)))
    factor = np.linalg.cholesky(covariance[order][:, order])
    ordered_center = center[order]
    bounds = model.bounds[order]
    uniform = qmc.Sobol(dimension, scramble=True, seed=729183).random_base2(power)
    sample_count = len(uniform)
    latent = np.zeros((sample_count, dimension))
    log_weights = np.zeros(sample_count)
    for channel in range(dimension):
        conditional_center = ordered_center[channel] + latent[:, :channel] @ factor[channel, :channel]
        lower = (bounds[channel, 0] - conditional_center) / factor[channel, channel]
        upper = (bounds[channel, 1] - conditional_center) / factor[channel, channel]
        positive = lower > 0
        first = ndtr(np.where(positive, -upper, lower))
        second = ndtr(np.where(positive, -lower, upper))
        mass = np.maximum(second - first, 1e-300)
        quantile = np.clip(first + uniform[:, channel] * mass,
                           np.finfo(float).tiny, 1 - np.finfo(float).eps)
        latent[:, channel] = np.where(positive, -ndtri(quantile), ndtri(quantile))
        log_weights += np.log(mass)
    ordered_points = ordered_center[None, :] + latent @ factor.T
    points = ordered_points[:, np.argsort(order)]
    log_weights += 0.5 * np.sum(latent ** 2, axis=1)
    log_weights += model.log_likelihood_batch(counts, points)
    weights = np.exp(log_weights - logsumexp(log_weights))
    effective_samples = 1 / (weights @ weights)
    if effective_samples < 0.1 * sample_count and power < (12 if moments else 14):
        if time.process_time() < 35:
            return posterior(model, counts, fitted, power=power + 2, moments=moments)
    mean = weights @ points
    if moments:
        centered = points - mean
        return mean, (centered.T * weights) @ centered
    return np.clip(mean, model.bounds[:, 0], model.bounds[:, 1])


def integer_allocation(fractions, total):
    exact = fractions * total
    allocation = np.floor(exact).astype(int)
    residual = total - allocation.sum()
    if residual:
        allocation[np.argsort(exact - allocation)[-residual:]] += 1
    return allocation


def calibrate(spec, query):
    model = Model(spec)
    action_count = len(spec['actions'])
    counts = np.zeros((action_count, model.state_count), dtype=np.int64)
    spent = np.zeros(action_count, dtype=int)
    queries = 0
    budget = spec['shot_budget']
    maximum_shots = spec['max_shots_per_query']

    def collect(allocation):
        nonlocal queries
        for action_id in np.flatnonzero(allocation):
            remaining = int(allocation[action_id])
            while remaining:
                shots = min(remaining, maximum_shots)
                counts[action_id] += query(int(action_id), shots)
                spent[action_id] += shots
                remaining -= shots
                queries += 1

    exposure = model.exposures[:, 0, :]
    amplified = exposure >= 2
    nonrare = model.groups[3] == 0
    general = (amplified[:, nonrare].any(axis=1) | (amplified.sum(axis=1) > 1))
    general &= exposure.min(axis=1) < 1
    pilot = np.where(general, 100, 0)
    for channel in np.flatnonzero(~nonrare):
        candidates = np.flatnonzero((amplified.sum(axis=1) == 1) & amplified[:, channel])
        for gain in (120, 720):
            chosen = candidates[np.argmin(np.abs(np.log(exposure[candidates, channel] / gain)))]
            pilot[chosen] = 100
    collect(pilot)
    fitted = model.fit(counts)
    for target in (6000, 14000, 26000, budget):
        if spent.sum() >= 6000:
            center, covariance = posterior(model, counts, fitted, power=10, moments=True)
            fractions = design(model, center, spent, budget, np.linalg.inv(covariance))
        else:
            fractions = design(model, fitted, spent, budget)
        total = target - int(spent.sum())
        fractions[fractions * total < 80] = 0
        fractions /= fractions.sum()
        allocation = integer_allocation(fractions, total)
        future_queries = int(np.ceil((budget - target) / maximum_shots))
        available_queries = spec['max_queries'] - queries - future_queries
        while np.sum((allocation + maximum_shots - 1) // maximum_shots) > available_queries:
            active = np.flatnonzero(allocation)
            smallest = active[np.argmin(allocation[active])]
            fractions[smallest] = 0
            fractions /= fractions.sum()
            allocation = integer_allocation(fractions, total)
        collect(allocation)
        fitted = model.fit(counts, fitted)
    return np.exp(posterior(model, counts, fitted))


def send(message):
    print(json.dumps(message, allow_nan=False), flush=True)


def main():
    spec = json.loads(sys.stdin.readline())['spec']

    def query(action, shots):
        send({'type': 'query', 'action': action, 'shots': shots})
        response = json.loads(sys.stdin.readline())
        if response.get('type') != 'observation':
            raise RuntimeError('Expected an observation')
        return np.asarray(response['counts'], dtype=np.int64)

    send({'type': 'final', 'rates': calibrate(spec, query).tolist()})


if __name__ == '__main__':
    main()
