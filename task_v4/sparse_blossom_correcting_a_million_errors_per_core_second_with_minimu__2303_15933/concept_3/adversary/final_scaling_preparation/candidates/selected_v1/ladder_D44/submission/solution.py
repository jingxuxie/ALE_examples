import os
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[variable] = '1'
import ctypes
import json
import sys
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.linalg import cho_factor, cho_solve
from scipy.special import ndtr, ndtri, logsumexp
from scipy.stats import qmc

ROOT = Path(__file__).resolve().parent
LIB = ctypes.CDLL(str(ROOT / 'kernel.so'))
LIB.supports_avx2.restype = ctypes.c_int
if LIB.supports_avx2() and (ROOT / 'kernel_avx2.so').is_file():
    try:
        LIB = ctypes.CDLL(str(ROOT / 'kernel_avx2.so'))
    except OSError:
        pass
DOUBLE = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
INTEGER = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
LIB.evaluate.argtypes = [ctypes.c_int] * 3 + [INTEGER] + [DOUBLE] * 6
LIB.evaluate.restype = ctypes.c_double
LIB.distribution.argtypes = [ctypes.c_int] * 3 + [INTEGER] + [DOUBLE] * 6
LIB.distribution.restype = None


class Model:
    def __init__(self, spec):
        self.spec = spec
        self.dimension = spec['detector_count']
        self.bounds = np.log([channel['rate_bounds'] for channel in spec['channels']])
        self.channels = len(self.bounds)
        self.actions = len(spec['actions'])
        self.exposures = np.array([action['exposures'] for action in spec['actions']])
        self.weights = np.array([action['mode_weights'] for action in spec['actions']])
        self.alternate = np.array([action['alternate_probability'] for action in spec['actions']])
        self.original_masks = np.array([channel['masks'] for channel in spec['channels']], dtype=np.int32)
        self.groups = np.array([[channel['family'] == family for channel in spec['channels']]
                               for family in ('boundary', 'bulk', 'hook', 'rare')], dtype=float)
        self.groups /= self.groups.sum(axis=1, keepdims=True)
        self.spent = np.zeros(self.actions)
        self.raw_counts = np.zeros((self.actions, 1 << self.dimension))
        rng = np.random.default_rng(19431)
        unique_masks = np.unique(self.original_masks)
        for attempt in range(64):
            codes = np.left_shift(1, np.arange(self.dimension, dtype=np.int32))
            for iteration in range(10 * self.dimension):
                first, second = rng.choice(self.dimension, 2, replace=False)
                codes[first] ^= codes[second]
            projected = np.zeros(len(unique_masks), dtype=np.int32)
            for detector in range(self.dimension):
                projected ^= ((unique_masks >> detector) & 1) * codes[detector]
            projected &= (1 << min(14, self.dimension)) - 1
            if len(np.unique(projected)) == len(unique_masks) and np.all(projected):
                break
        self.mapping = np.zeros(1 << self.dimension, dtype=np.int32)
        for detector in range(self.dimension):
            self.mapping[1 << detector:1 << (detector + 1)] = self.mapping[:1 << detector] ^ codes[detector]
        self.all_masks = self.mapping[self.original_masks]
        self.calls = 0

    def setup(self, bits, point=None):
        bits = min(bits, self.dimension)
        active = np.flatnonzero(self.spent)
        groups = [(bits, active)]
        if bits > 16 and point is not None:
            firing = (1 - np.exp(-2 * self.exposures * np.exp(point)[None, None])) / 2
            total = np.sum(self.weights[:, :, None] * firing, axis=(1, 2))
            full = (total[active] >= 0.85) & (self.spent[active] >= 350)
            groups = [(bits, active[full]), (16, active[~full])]
        result = []
        for width, actions in groups:
            if len(actions) == 0:
                continue
            size = 1 << width
            masks = np.ascontiguousarray(self.all_masks & (size - 1))
            counts = np.zeros((len(actions), size))
            mapping = self.mapping & (size - 1)
            for index, action in enumerate(actions):
                counts[index] = np.bincount(mapping, weights=self.raw_counts[action], minlength=size)
            result.append((size, masks, counts, self.exposures[actions], self.weights[actions], self.alternate[actions]))
        return result

    def evaluate(self, point, setup):
        gradient = np.zeros(self.channels)
        value = 0.0
        rates = np.exp(point)
        for size, masks, counts, exposures, weights, alternate in setup:
            partial = np.zeros(self.channels)
            value += LIB.evaluate(size, self.channels, len(counts), masks, exposures,
                                  weights, alternate, rates, counts, partial)
            gradient += partial
        self.calls += 1
        return value, gradient

    def fit(self, point=None, bits=14, maxiter=65, deadline=48):
        if bits > 16 and point is not None:
            return self.refine(point, bits, maxiter, deadline)
        if point is None:
            point = self.bounds.mean(axis=1)
        setup = self.setup(bits, point)
        best = [np.array(point), float('inf')]
        scale = max(self.spent.sum(), 1)

        def objective(candidate):
            if time.process_time() > deadline and best[1] < float('inf'):
                raise TimeoutError
            value, gradient = self.evaluate(candidate, setup)
            if value < best[1]:
                best[:] = [candidate.copy(), value]
            return value / scale, gradient / scale

        try:
            result = minimize(objective, point, jac=True, bounds=self.bounds,
                              method='L-BFGS-B', options={'maxiter': maxiter, 'ftol': 1e-11, 'gtol': 1e-8, 'maxcor': 15})
            point = result.x
        except TimeoutError:
            point = best[0]
        print('fit', bits, self.spent.sum(), self.calls, time.process_time(), file=sys.stderr, flush=True)
        return point

    def refine(self, point, bits, maxiter, deadline):
        point = np.array(point, copy=True)
        setup = self.setup(bits, point)
        fisher = getattr(self, 'latest_fisher', None)
        if fisher is None:
            fisher = self.fisher(point, bits=14, active_only=True)
        information = np.einsum('a,akl->kl', self.spent, fisher) + np.eye(self.channels) * 1e-3
        value, gradient = self.evaluate(point, setup)
        lower, upper = self.bounds.T
        for iteration in range(maxiter):
            if time.process_time() >= deadline:
                break
            free = ((point > lower + 1e-10) | (gradient < 0)) & ((point < upper - 1e-10) | (gradient > 0))
            if not np.any(free):
                break
            normalized = np.abs(gradient[free]) / np.sqrt(np.diag(information)[free])
            if np.max(normalized) < 0.002:
                break
            direction = np.zeros(self.channels)
            selected = information[np.ix_(free, free)]
            try:
                direction[free] = -cho_solve(cho_factor(selected, lower=True, check_finite=False),
                                            gradient[free], check_finite=False)
            except np.linalg.LinAlgError:
                direction[free] = -gradient[free] / np.diag(information)[free]
            displacement = np.clip(point + direction, lower, upper) - point
            if gradient @ displacement >= 0:
                direction = -gradient / np.diag(information)
            accepted = False
            step_size = 1.0
            for search in range(12):
                if time.process_time() >= deadline:
                    break
                candidate = np.clip(point + step_size * direction, lower, upper)
                displacement = candidate - point
                candidate_value, candidate_gradient = self.evaluate(candidate, setup)
                if candidate_value <= value + 1e-4 * (gradient @ displacement):
                    accepted = True
                    break
                step_size *= 0.5
            if not accepted:
                break
            change = candidate_gradient - gradient
            transformed = information @ displacement
            curvature = displacement @ change
            predicted = displacement @ transformed
            if predicted > 1e-12:
                if curvature < 0.2 * predicted:
                    weight = 0.8 * predicted / (predicted - curvature)
                    change = weight * change + (1 - weight) * transformed
                    curvature = displacement @ change
                information += np.outer(change, change) / curvature - np.outer(transformed, transformed) / predicted
            point, value, gradient = candidate, candidate_value, candidate_gradient
        print('refine', bits, self.calls, time.process_time(), file=sys.stderr, flush=True)
        self.refined_point = point.copy()
        self.refined_gradient = gradient.copy()
        return point

    def fisher(self, point, bits=14, active_only=False):
        size = 1 << min(bits, self.dimension)
        masks = np.ascontiguousarray(self.all_masks & (size - 1))
        fisher = np.zeros((self.actions, self.channels, self.channels))
        actions = np.flatnonzero(self.spent) if active_only else np.arange(self.actions)
        rates = np.exp(point)
        for start in range(0, len(actions), 4):
            selected = actions[start:start + 4]
            probability = np.zeros((len(selected), size))
            jacobian = np.zeros((len(selected), self.channels, size))
            LIB.distribution(size, self.channels, len(selected), masks, self.exposures[selected],
                             self.weights[selected], self.alternate[selected], rates, probability, jacobian)
            jacobian /= np.sqrt(probability[:, None])
            fisher[selected] = jacobian @ jacobian.transpose(0, 2, 1)
        return fisher

    def posterior(self, fitted):
        fisher = self.fisher(fitted, bits=15, active_only=True)
        information = np.einsum('a,akl->kl', self.spent, fisher)
        covariance = np.linalg.inv(information + np.eye(self.channels) * 1e-6)
        if hasattr(self, 'refined_point') and np.array_equal(fitted, self.refined_point):
            gradient = self.refined_gradient
        else:
            unused, gradient = self.evaluate(fitted, self.setup(self.dimension, fitted))
        center = fitted - covariance @ gradient
        deviations = np.sqrt(np.diag(covariance))
        distances = np.minimum(fitted - self.bounds[:, 0], self.bounds[:, 1] - fitted) / deviations
        order = np.argsort(distances)
        factor = np.linalg.cholesky(covariance[order][:, order])
        bounds = self.bounds[order]
        ordered_center = center[order]
        uniform = qmc.Sobol(self.channels, scramble=True, seed=871923).random_base2(11)
        latent = np.zeros_like(uniform)
        log_weights = np.zeros(len(uniform))
        for channel in range(self.channels):
            conditional = ordered_center[channel] + latent[:, :channel] @ factor[channel, :channel]
            lower = (bounds[channel, 0] - conditional) / factor[channel, channel]
            upper = (bounds[channel, 1] - conditional) / factor[channel, channel]
            positive = lower > 0
            first = ndtr(np.where(positive, -upper, lower))
            second = ndtr(np.where(positive, -lower, upper))
            mass = np.maximum(second - first, 1e-300)
            quantile = np.clip(first + uniform[:, channel] * mass, 1e-300, 1 - np.finfo(float).eps)
            latent[:, channel] = np.where(positive, -ndtri(quantile), ndtri(quantile))
            log_weights += np.log(mass)
        points = ordered_center[None] + latent @ factor.T
        weights = np.exp(log_weights - logsumexp(log_weights))
        mean = (weights @ points)[np.argsort(order)]
        return np.clip(mean, self.bounds[:, 0], self.bounds[:, 1])


def design(model, point, budget, bits=14):
    fisher = model.fisher(point, bits)
    identity = np.eye(model.channels)
    fraction = 1 - model.spent.sum() / budget
    base = np.einsum('a,akl->kl', model.spent / budget, fisher) + identity / budget

    def objective(allocation):
        information = base + np.einsum('a,akl->kl', allocation * fraction, fisher)
        inverse = cho_solve(cho_factor(information, lower=True, check_finite=False), identity, check_finite=False)
        variances = model.groups @ np.diag(inverse)
        value = np.power(variances, 0.75).sum()
        channel_weights = (0.75 * np.power(variances, -0.25)) @ model.groups
        sensitivity = (inverse * channel_weights[None]) @ inverse
        gradient = -fraction * np.einsum('akl,kl->a', fisher, sensitivity)
        return value, gradient

    start = np.full(model.actions, 1 / model.actions)
    scale = objective(start)[0]

    def normalized(allocation):
        value, gradient = objective(allocation)
        return value / scale, gradient / scale

    result = minimize(normalized, start, jac=True, method='SLSQP', bounds=[(0, 1)] * model.actions,
                      constraints=[{'type': 'eq', 'fun': lambda allocation: allocation.sum() - 1,
                                    'jac': lambda allocation: np.ones(model.actions)}],
                      options={'maxiter': 80, 'ftol': 1e-8})
    allocation = np.maximum(result.x, 0)
    return allocation / allocation.sum(), fisher


def integer_allocation(fractions, total):
    exact = fractions * total
    allocation = np.floor(exact).astype(int)
    residual = int(total - allocation.sum())
    if residual:
        allocation[np.argsort(exact - allocation)[-residual:]] += 1
    return allocation


def calibrate(spec, query):
    model = Model(spec)
    budget = spec['shot_budget']
    maximum = spec['max_shots_per_query']
    queries = 0

    def collect(allocation):
        nonlocal queries
        for action in np.flatnonzero(allocation):
            remaining = int(allocation[action])
            while remaining:
                shots = min(remaining, maximum)
                syndromes, counts = query(int(action), shots)
                model.raw_counts[action, syndromes] += counts
                model.spent[action] += shots
                remaining -= shots
                queries += 1

    pilot = np.zeros(model.actions, dtype=int)
    amplified = model.exposures[:, 0] >= 2
    nonrare = model.groups[3] == 0
    general = amplified[:, nonrare].any(axis=1) & (model.exposures[:, 0].min(axis=1) < 1)
    pilot[general] = 120
    for channel in np.flatnonzero(model.groups[3]):
        exposure = model.exposures[:, 0, channel]
        candidates = np.flatnonzero((model.exposures[:, 0, :] >= 2).sum(axis=1) == 1)
        candidates = candidates[exposure[candidates] >= 2]
        for candidate in candidates:
            pilot[candidate] = 75
    collect(pilot)
    fitted = model.fit()
    fisher = None
    for target in (9000, 23000, budget):
        design_bits = 14 if target == 9000 else (15 if target == 23000 else 16)
        fractions, fisher = design(model, fitted, budget, bits=design_bits)
        model.latest_fisher = fisher
        total = int(target - model.spent.sum())
        fractions[fractions * total < 120] = 0
        fractions /= fractions.sum()
        allocation = integer_allocation(fractions, total)
        future = int(np.ceil((budget - target) / maximum))
        available = spec['max_queries'] - queries - future
        while np.sum((allocation + maximum - 1) // maximum) > available:
            active = np.flatnonzero(allocation)
            fractions[active[np.argmin(allocation[active])]] = 0
            fractions /= fractions.sum()
            allocation = integer_allocation(fractions, total)
        print('allocate', target, allocation.tolist(), file=sys.stderr, flush=True)
        collect(allocation)
        fitted = model.fit(fitted, bits=14 if target < budget else 16)
    if model.dimension > 16 and time.process_time() < 40:
        fitted = model.fit(fitted, bits=model.dimension, maxiter=35, deadline=49)
    if time.process_time() < 49:
        try:
            posterior = model.posterior(fitted)
            if np.all(np.isfinite(posterior)):
                fitted = posterior
        except np.linalg.LinAlgError:
            pass
        print('posterior', time.process_time(), file=sys.stderr, flush=True)
    return np.exp(fitted)


def main():
    spec = json.loads(sys.stdin.readline())['spec']

    def query(action, shots):
        print(json.dumps({'type': 'query', 'action': action, 'shots': shots}), flush=True)
        response = json.loads(sys.stdin.readline())
        if response.get('type') != 'observation':
            raise RuntimeError('Expected observation')
        return np.asarray(response['syndromes'], dtype=np.int32), np.asarray(response['multiplicities'])

    rates = calibrate(spec, query)
    print(json.dumps({'type': 'final', 'rates': rates.tolist()}, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
