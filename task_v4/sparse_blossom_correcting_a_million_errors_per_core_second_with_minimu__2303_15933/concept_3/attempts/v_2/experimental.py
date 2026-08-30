import os

for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'

import json
import sys
import time

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize
from scipy.special import ndtr, ndtri, logsumexp
from scipy.stats import truncnorm
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
        self.spec = spec
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
        self.odd = (1 - alternate[:, :, None]) * first + alternate[:, :, None] * second
        self.groups = np.array([[channel['family'] == family for channel in spec['channels']]
                                for family in ('boundary', 'bulk', 'hook', 'rare')], dtype=float)
        self.groups /= self.groups.sum(axis=1, keepdims=True)
        self.quadrature_diagnostics = []

    def distribution(self, log_rates, gradient=False):
        scaled = 2 * self.exposures * np.exp(log_rates)[None, None, :]
        first_factor = np.logaddexp(self.log_alternate, self.log_primary - scaled)
        second_factor = np.logaddexp(self.log_primary, self.log_alternate - scaled)
        log_products = (-scaled @ self.both + first_factor @ self.first_only + second_factor @ self.second_only)
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

    def fit(self, counts, initial=None, iterations=150):
        start = self.bounds.mean(axis=1) if initial is None else np.asarray(initial)
        total = max(float(counts.sum()), 1)

        def objective(log_rates):
            probability, derivative = self.distribution(log_rates, True)
            value = -np.sum(counts * np.log(probability)) / total
            gradient = -np.einsum('as,aks->k', counts / probability, derivative) / total
            return value, gradient

        result = minimize(objective, start, method='L-BFGS-B', jac=True,
                          bounds=self.bounds.tolist(),
                          options={'maxiter': iterations, 'ftol': 2e-13, 'gtol': 1e-9, 'maxls': 25})
        return result.x

    def fisher(self, log_rates):
        probability, derivative = self.distribution(log_rates, True)
        normalized = derivative / np.sqrt(probability[:, None])
        return normalized @ normalized.transpose(0, 2, 1)


def design(model, fitted, spent, budget, criterion='root', prior_information=None):
    fisher = model.fisher(fitted)
    action_count, channel_count = fisher.shape[:2]
    identity = np.eye(channel_count)
    base = np.einsum('a,akl->kl', spent / budget, fisher) + 1e-10 * identity
    if prior_information is not None:
        base = prior_information / budget + 1e-10 * identity
    fraction = 1 - spent.sum() / budget

    def objective(allocation):
        information = base + np.einsum('a,akl->kl', allocation * fraction, fisher)
        inverse = cho_solve(cho_factor(information, lower=True, check_finite=False), identity, check_finite=False)
        variances = model.groups @ np.diag(inverse)
        power = {'root': 0.5, 'a': 1.0, 'mixed': 0.8}[criterion]
        value = np.power(variances, power).sum()
        channel_weights = (power * np.power(variances, power - 1)) @ model.groups
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
    allocation /= allocation.sum()
    return allocation


def integer_allocation(fractions, total):
    exact = fractions * total
    allocation = np.floor(exact).astype(int)
    residual = total - allocation.sum()
    allocation[np.argsort(exact - allocation)[-residual:]] += 1 if residual else 0
    return allocation


def posterior_mean(model, counts, fitted, skew=False, details=False):
    probability, derivative = model.distribution(fitted, True)
    score = np.einsum('as,aks->k', counts / probability, derivative)
    information = np.einsum('a,akl->kl', counts.sum(axis=1), model.fisher(fitted))
    covariance = np.linalg.inv(information)
    center = fitted + covariance @ score
    if skew:
        factor = np.linalg.cholesky(covariance)
        curvature_score = np.zeros(len(fitted))
        for direction in factor.T:
            for sign in (-1, 1):
                shifted_probability, shifted_derivative = model.distribution(fitted + sign * direction, True)
                curvature_score += 0.5 * (np.einsum('as,aks->k', counts / shifted_probability, shifted_derivative) - score)
        center += covariance @ curvature_score
    active = np.flatnonzero(np.minimum((fitted - model.bounds[:, 0]),
                                      (model.bounds[:, 1] - fitted)) < 5 * np.sqrt(np.diag(covariance)))
    site_precision = np.zeros(len(fitted))
    site_location = np.zeros(len(fitted))
    for iteration in range(12):
        previous = center.copy()
        for channel in active:
            marginal_variance = covariance[channel, channel]
            cavity_variance = 1 / (1 / marginal_variance - site_precision[channel])
            cavity_center = cavity_variance * (center[channel] / marginal_variance - site_location[channel])
            deviation = np.sqrt(cavity_variance)
            lower, upper = (model.bounds[channel] - cavity_center) / deviation
            mean, variance = truncnorm.stats(lower, upper, moments='mv')
            tilted_center = cavity_center + deviation * mean
            tilted_variance = max(cavity_variance * variance, 1e-12)
            new_precision = 1 / tilted_variance - 1 / cavity_variance
            new_location = tilted_center / tilted_variance - cavity_center / cavity_variance
            delta_precision = 0.8 * (new_precision - site_precision[channel])
            delta_location = 0.8 * (new_location - site_location[channel])
            column = covariance[:, channel].copy()
            denominator = 1 + delta_precision * marginal_variance
            center += column * (delta_location - delta_precision * center[channel]) / denominator
            covariance -= delta_precision / denominator * np.outer(column, column)
            site_precision[channel] += delta_precision
            site_location[channel] += delta_location
        if np.max(np.abs(center - previous)) < 1e-7:
            break
    center = np.clip(center, model.bounds[:, 0], model.bounds[:, 1])
    return (center, covariance) if details else center


def posterior_integral(model, counts, fitted, power=11, details=False, moments=False):
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
    distances = np.minimum(fitted - model.bounds[:, 0], model.bounds[:, 1] - fitted) / np.sqrt(np.diag(covariance))
    order = np.argsort(distances)
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
        quantile = np.clip(first + uniform[:, channel] * mass, 1e-15, 1 - 1e-15)
        latent[:, channel] = np.where(positive, -ndtri(quantile), ndtri(quantile))
        log_weights += np.log(mass)
    ordered_points = ordered_center[None, :] + latent @ factor.T
    points = ordered_points[:, np.argsort(order)]
    log_weights += 0.5 * np.sum(latent ** 2, axis=1)
    log_weights += model.log_likelihood_batch(counts, points)
    weights = np.exp(log_weights - logsumexp(log_weights))
    mean = weights @ points
    if moments:
        model.quadrature_diagnostics.append({'shots': int(counts.sum()), 'ess': float(1 / (weights @ weights)), 'max_weight': float(weights.max())})
        centered = points - mean
        return mean, (centered.T * weights) @ centered
    if details:
        return mean, {'ess': float(1 / (weights @ weights)), 'max_weight': float(weights.max())}
    return mean


def calibrate(spec, query, debug=False, return_state=False, strategy='v1'):
    started = time.process_time()
    model = Model(spec)
    action_count = len(spec['actions'])
    counts = np.zeros((action_count, model.state_count), dtype=np.int64)
    spent = np.zeros(action_count, dtype=int)
    queries = 0

    def collect(allocation):
        nonlocal queries
        for action_id in np.flatnonzero(allocation):
            remaining = int(allocation[action_id])
            while remaining:
                shots = min(remaining, spec['max_shots_per_query'])
                counts[action_id] += query(int(action_id), shots)
                spent[action_id] += shots
                remaining -= shots
                queries += 1

    pilot = np.zeros(action_count, dtype=int)
    for action_id, action in enumerate(spec['actions']):
        if action['name'].startswith('configuration'):
            pilot[action_id] = 200 if strategy == 'v1' else (100 if 2 <= action_id <= 11 else 0)
        elif action['name'].endswith('_120') or action['name'].endswith('_720'):
            pilot[action_id] = 150 if strategy == 'v1' else 100
    collect(pilot)
    fitted = model.fit(counts)
    if strategy == 'sequential':
        stage = 0
        while spent.sum() < spec['shot_budget']:
            fractions = design(model, fitted, spent, spec['shot_budget'])
            allocation = np.zeros(action_count, dtype=int)
            allocation[np.argmax(fractions)] = min(1000, spec['shot_budget'] - int(spent.sum()))
            collect(allocation)
            fitted = model.fit(counts, fitted)
            stage += 1
        if debug:
            print('sequential', 'shots', int(spent.sum()), 'queries', queries,
                  'cpu', round(time.process_time() - started, 3), file=sys.stderr)
        if return_state:
            return model, counts, fitted
        return np.exp(fitted)
    stages = [14000, None] if strategy == 'v1' else [6000, 12000, None]
    if strategy in ('v3', 'v3a', 'bayes', 'mixed', 'final', 'posterior'):
        stages = [4200, 8000, 12000, None]
    for stage, stage_total in enumerate(stages):
        criterion = 'a' if strategy.endswith('a') else ('mixed' if strategy in ('mixed', 'final', 'posterior') else 'root')
        if strategy in ('bayes', 'final', 'posterior') and spent.sum() >= 6000:
            if strategy == 'posterior':
                center, covariance = posterior_integral(model, counts, fitted, power=10, moments=True)
            else:
                center, covariance = posterior_mean(model, counts, fitted, details=True)
            fractions = design(model, center, spent, spec['shot_budget'], criterion, np.linalg.inv(covariance))
        else:
            fractions = design(model, fitted, spent, spec['shot_budget'], criterion)
        total = stage_total if stage_total is not None else spec['shot_budget'] - int(spent.sum())
        fractions[fractions * total < 80] = 0
        fractions /= fractions.sum()
        allocation = integer_allocation(fractions, total)
        future_queries = int(np.ceil((spec['shot_budget'] - spent.sum() - total) / spec['max_shots_per_query']))
        while np.sum((allocation + spec['max_shots_per_query'] - 1) // spec['max_shots_per_query']) > spec['max_queries'] - queries - future_queries:
            active = np.flatnonzero(allocation)
            smallest = active[np.argmin(allocation[active])]
            fractions[smallest] = 0
            fractions /= fractions.sum()
            allocation = integer_allocation(fractions, total)
        collect(allocation)
        fitted = model.fit(counts, fitted)
        if debug:
            print('stage', stage, 'shots', int(spent.sum()), 'queries', queries,
                  'cpu', round(time.process_time() - started, 3), file=sys.stderr)
    if return_state:
        return model, counts, fitted
    return np.exp(fitted)


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

    rates = calibrate(spec, query)
    send({'type': 'final', 'rates': rates.tolist()})


if __name__ == '__main__':
    main()
