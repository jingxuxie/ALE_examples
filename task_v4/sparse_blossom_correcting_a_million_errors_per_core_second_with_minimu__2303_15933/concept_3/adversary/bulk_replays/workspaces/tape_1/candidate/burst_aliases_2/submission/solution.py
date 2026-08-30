import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import json
import sys
import time

import numpy as np
from scipy.optimize import minimize
from scipy.special import ndtr, ndtri
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
        self.state_count = 1 << spec['detector_count']
        masks = np.array([channel['masks'] for channel in spec['channels']])
        parity = np.array([index.bit_count() % 2 for index in range(self.state_count)])
        first = parity[masks[:, 0, None] & np.arange(self.state_count)]
        second = parity[masks[:, 1, None] & np.arange(self.state_count)]
        alternate = np.array([action['alternate_probability'] for action in spec['actions']])
        self.odd = (1 - alternate[:, :, None]) * first + alternate[:, :, None] * second
        families = np.array([channel['family'] for channel in spec['channels']])
        self.family_weights = np.array([(families == family) / np.sum(families == family)
                                        for family in ['boundary', 'bulk', 'hook', 'rare']])

    def spectrum(self, log_rates, selected=None):
        exposures = self.exposures if selected is None else self.exposures[selected]
        odd = self.odd if selected is None else self.odd[selected]
        weights = self.weights if selected is None else self.weights[selected]
        scaled = -2 * exposures * np.exp(log_rates)[None, None, :]
        attenuation = np.exp(scaled)
        factors = np.maximum(1 - odd[:, None, :, :] + attenuation[..., None] * odd[:, None, :, :], 1e-280)
        products = weights[:, :, None] * np.prod(factors, axis=2)
        return products, factors, scaled, attenuation, odd

    def distribution(self, log_rates, gradient=False):
        products, factors, scaled, attenuation, odd = self.spectrum(log_rates)
        probability = np.maximum(walsh(products.sum(axis=1)) / self.state_count, 1e-15)
        if not gradient:
            return probability
        derivative = np.sum(products[:, :, None, :] * (scaled * attenuation)[..., None]
                            * odd[:, None, :, :] / factors, axis=1)
        return probability, walsh(derivative) / self.state_count

    def fit(self, counts, initial=None, iterations=150):
        selected = np.flatnonzero(counts.sum(axis=1))
        observed = counts[selected]
        total = max(float(observed.sum()), 1)
        start = self.bounds.mean(axis=1) if initial is None else initial

        def objective(log_rates):
            products, factors, scaled, attenuation, odd = self.spectrum(log_rates, selected)
            probability = np.maximum(walsh(products.sum(axis=1)) / self.state_count, 1e-15)
            value = -np.sum(observed * np.log(probability)) / total
            score = walsh(observed / probability) / (total * self.state_count)
            log_derivative = (scaled * attenuation)[..., None] * odd[:, None, :, :] / factors
            gradient = -np.einsum('azs,azks->k', products * score[:, None, :], log_derivative)
            return value, gradient

        result = minimize(objective, start, method='L-BFGS-B', jac=True,
                          bounds=self.bounds, options={'maxiter': iterations, 'ftol': 2e-13,
                                                       'gtol': 2e-9, 'maxls': 25})
        return result.x

    def fisher(self, log_rates):
        probability, derivative = self.distribution(log_rates, gradient=True)
        return np.einsum('aks,als,as->akl', derivative, derivative, 1 / probability, optimize=True)


def design(model, log_rates, used, budget, criterion='rms'):
    information = model.fisher(log_rates)
    fraction = used / budget
    remaining = 1 - fraction.sum()
    base = np.einsum('a,akl->kl', fraction, information) + np.eye(len(log_rates)) * 1e-8

    def objective(allocation):
        combined = base + np.einsum('a,akl->kl', allocation, information)
        inverse = np.linalg.inv(combined)
        family_variance = model.family_weights @ inverse.diagonal()
        if criterion == 'rms':
            roots = np.sqrt(np.maximum(family_variance, 1e-20))
            value = roots.mean()
            weight = (model.family_weights / (8 * roots[:, None])).sum(axis=0)
        else:
            value = family_variance.mean()
            weight = model.family_weights.mean(axis=0)
        sensitivity = (inverse * weight[None, :]) @ inverse
        gradient = -np.einsum('kl,alk->a', sensitivity, information)
        return value, gradient

    result = minimize(objective, np.full(len(used), remaining / len(used)), method='SLSQP',
                      jac=True, bounds=[(0, remaining)] * len(used),
                      constraints={'type': 'eq', 'fun': lambda allocation: allocation.sum() - remaining,
                                   'jac': lambda allocation: np.ones(len(allocation))},
                      options={'maxiter': 150, 'ftol': 2e-8})
    allocation = np.maximum(result.x, 0)
    if not np.all(np.isfinite(allocation)) or allocation.sum() <= 0:
        allocation = np.ones(len(used))
    allocation /= allocation.sum()
    return allocation, information


def log_likelihoods(model, counts, samples, batch_size=16):
    selected = np.flatnonzero(counts.sum(axis=1))
    observed = counts[selected]
    exposures = model.exposures[selected]
    odd = model.odd[selected]
    weights = model.weights[selected]
    likelihoods = np.empty(len(samples))
    for start in range(0, len(samples), batch_size):
        batch = samples[start:start + batch_size]
        attenuation = np.exp(-2 * exposures[None, :, :, :] * np.exp(batch)[:, None, None, :])
        products = np.ones((len(batch), len(selected), 2, model.state_count))
        for channel in range(len(model.bounds)):
            parity = odd[None, :, None, channel, :]
            products *= 1 - parity + attenuation[:, :, :, channel, None] * parity
        probability = np.maximum(walsh(np.sum(products * weights[None, :, :, None], axis=2))
                                 / model.state_count, 1e-15)
        likelihoods[start:start + len(batch)] = np.einsum('bas,as->b', np.log(probability), observed)
    return likelihoods


def posterior_mean(model, counts, fitted, power=10):
    bounds = model.bounds.copy()
    model.bounds = bounds + np.array([-0.5, 0.5])
    try:
        mode = model.fit(counts, fitted, iterations=70)
    finally:
        model.bounds = bounds
    information = np.einsum('a,akl->kl', counts.sum(axis=1), model.fisher(mode))
    covariance = np.linalg.inv(information)
    cholesky = np.linalg.cholesky(covariance)
    dimension = len(mode)
    uniforms = qmc.Sobol(dimension, scramble=True, seed=783).random_base2(power)
    white = np.zeros_like(uniforms)
    log_mass = np.zeros(len(uniforms))
    for channel in range(dimension):
        center = mode[channel] + white[:, :channel] @ cholesky[channel, :channel]
        low = ndtr((bounds[channel, 0] - center) / cholesky[channel, channel])
        high = ndtr((bounds[channel, 1] - center) / cholesky[channel, channel])
        mass = np.maximum(high - low, 1e-100)
        white[:, channel] = ndtri(np.clip(low + uniforms[:, channel] * mass, 1e-15, 1 - 1e-15))
        log_mass += np.log(mass)
    samples = np.clip(mode + white @ cholesky.T, bounds[:, 0], bounds[:, 1])
    log_weights = log_mass + 0.5 * np.sum(white ** 2, axis=1)
    log_weights += log_likelihoods(model, counts, samples)
    weights = np.exp(log_weights - log_weights.max())
    weights /= weights.sum()
    effective_samples = 1 / np.sum(weights ** 2)
    if not np.isfinite(effective_samples) or effective_samples < 30:
        return fitted
    return np.clip(weights @ samples, bounds[:, 0], bounds[:, 1])


def solve(spec, query, pilot=100, intermediate=12000, criterion='rms', diagnostics=None, early=0,
          posterior=False):
    started = time.process_time()
    model = Model(spec)
    action_count = len(spec['actions'])
    counts = np.zeros((action_count, model.state_count), dtype=np.int64)
    used = np.zeros(action_count, dtype=np.int64)
    queries = 0
    budget = spec['shot_budget']

    def sample(action, shots):
        nonlocal queries
        while shots:
            batch = min(int(shots), spec['max_shots_per_query'])
            counts[action] += query(int(action), batch)
            used[action] += batch
            queries += 1
            shots -= batch

    for action in range(1, action_count):
        exposures = model.exposures[action, 0]
        if early and exposures.max() < 3 * exposures.min():
            continue
        sample(action, pilot)
    fitted = model.fit(counts)
    stages = ([early] if early else []) + [intermediate, budget]
    for phase, desired in enumerate(stages):
        allocation, information = design(model, fitted, used, budget, criterion)
        remaining = budget - int(used.sum())
        phase_budget = min(desired, remaining)
        last = phase == len(stages) - 1
        active = np.flatnonzero(allocation * phase_budget >= (30 if last else 100))
        if len(active) == 0:
            active = np.array([np.argmax(allocation)])
        available = spec['max_queries'] - queries
        max_active = max(1, available - (phase_budget + spec['max_shots_per_query'] - 1) // spec['max_shots_per_query'])
        if not last:
            max_active = min(max_active, max(1, (available - 12) // (len(stages) - phase)))
        if len(active) > max_active:
            active = np.argsort(allocation)[-max_active:]
        target = phase_budget * allocation[active] / allocation[active].sum()
        shots = np.floor(target).astype(int)
        remainder = phase_budget - int(shots.sum())
        if remainder:
            shots[np.argsort(target - shots)[-remainder:]] += 1
        for action, batch in zip(active, shots):
            if batch:
                sample(action, int(batch))
        fitted = model.fit(counts, fitted)
    if posterior and time.process_time() - started < 40:
        try:
            fitted = posterior_mean(model, counts, fitted)
        except np.linalg.LinAlgError:
            pass
    if diagnostics is not None:
        diagnostics.update(used=used.tolist(), queries=queries,
                           predicted=np.sqrt(model.family_weights @ np.linalg.inv(
                               np.einsum('a,akl->kl', used, model.fisher(fitted))).diagonal()).tolist())
    return np.exp(fitted)


def main():
    spec = json.loads(sys.stdin.readline())['spec']

    def query(action, shots):
        print(json.dumps({'type': 'query', 'action': action, 'shots': shots}), flush=True)
        response = json.loads(sys.stdin.readline())
        if response.get('type') != 'observation':
            raise RuntimeError('Expected observation')
        return np.asarray(response['counts'], dtype=np.int64)

    rates = solve(spec, query, pilot=35, intermediate=9000, early=2500, posterior=True)
    print(json.dumps({'type': 'final', 'rates': rates.tolist()}, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
