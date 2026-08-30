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
from scipy.special import ndtr

ROOT = Path(__file__).resolve().parent
LIB = ctypes.CDLL(str(ROOT / 'kernel.so'))
DOUBLE = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
INTEGER = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
LIB.evaluate.argtypes = [ctypes.c_int] * 3 + [INTEGER] + [DOUBLE] * 6
LIB.evaluate.restype = ctypes.c_double
LIB.distribution.argtypes = [ctypes.c_int] * 3 + [INTEGER] + [DOUBLE] * 6
LIB.distribution.restype = None


def contiguous(values, dtype=np.float64):
    return np.ascontiguousarray(values, dtype=dtype)


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
        self.masks = np.array([channel['masks'] for channel in spec['channels']], dtype=np.int64)
        self.unions = self.masks[:, 0] | self.masks[:, 1]
        self.family = np.array([channel['family'] for channel in spec['channels']])
        self.groups = np.array([self.family == family for family in ('boundary', 'bulk', 'hook', 'rare')], dtype=float)
        self.groups /= self.groups.sum(axis=1, keepdims=True)
        self.spent = np.zeros(self.actions)
        self.raw = [[] for action in range(self.actions)]
        self.rare_actions = np.flatnonzero((self.exposures[:, 0] >= 2).sum(axis=1) == 1)
        self.general_actions = np.array([action for action in range(self.actions) if action not in self.rare_actions])
        self.rare_target = np.argmax(self.exposures[self.rare_actions, 0], axis=1)
        self.distance = np.full((self.dimension, self.dimension), 100, dtype=int)
        np.fill_diagonal(self.distance, 0)
        for first, second in spec['detector_edges']:
            self.distance[first, second] = self.distance[second, first] = 1
        for detector in range(self.dimension):
            self.distance = np.minimum(self.distance, self.distance[:, detector, None] + self.distance[None, detector, :])
        self.block_cache = {}
        rng = np.random.default_rng(230319)
        for trial in range(100):
            self.hash_codes = rng.integers(1, 1 << 16, self.dimension, dtype=np.int32)
            projected = self.project(self.masks, self.hash_codes) & ((1 << 14) - 1)
            if len(np.unique(projected)) == len(np.unique(self.masks)) and np.all(projected):
                break
        self.calls = 0

    def project(self, syndromes, codes):
        projected = np.zeros(np.shape(syndromes), dtype=np.int32)
        for detector, code in enumerate(codes):
            if code:
                projected ^= ((syndromes >> detector) & 1).astype(np.int32) * code
        return projected

    def local_codes(self, detectors):
        codes = np.zeros(self.dimension, dtype=np.int32)
        codes[detectors] = 1 << np.arange(len(detectors), dtype=np.int32)
        return codes

    def neighborhood(self, mask, width):
        detectors = [detector for detector in range(self.dimension) if (int(mask) >> detector) & 1]
        distances = self.distance[detectors]
        priority = distances.min(axis=0) + distances.mean(axis=0) * 0.1
        return np.sort(np.argsort(priority, kind='stable')[:width])

    def blocks(self, width):
        if width in self.block_cache:
            return self.block_cache[width]
        candidates = sorted(set(tuple(self.neighborhood(mask, width)) for mask in self.unions))
        masks = np.array([sum(1 << detector for detector in detectors) for detectors in candidates], dtype=np.int64)
        covered = (self.unions[None] & masks[:, None]) == self.unions[None]
        coverage = np.zeros(self.channels)
        chosen = []
        for iteration in range(int(np.ceil(3.2 * self.dimension / width))):
            scores = covered @ (1 / (0.4 + coverage) ** 2)
            scores[chosen] = -1
            best = int(np.argmax(scores))
            chosen.append(best)
            coverage += covered[best]
        result = [self.local_codes(list(candidates[index])) for index in chosen]
        self.block_cache[width] = result
        return result

    def make_block(self, codes, actions, weight=1.0, observed=True):
        masks = self.project(self.masks, codes)
        active = np.flatnonzero(np.any(masks, axis=1))
        size = 1 << int(max(codes)).bit_length()
        counts = np.zeros((len(actions), size))
        if observed:
            for index, action in enumerate(actions):
                for syndromes, multiplicities in self.raw[action]:
                    projected = self.project(syndromes, codes)
                    counts[index] += np.bincount(projected, weights=multiplicities, minlength=size)
        return (size, active, contiguous(masks[active], np.int32), contiguous(self.exposures[actions][:, :, active]),
                contiguous(self.weights[actions]), contiguous(self.alternate[actions][:, active]), counts, weight)

    def setup(self, width=10, hashbits=14):
        blocks = self.blocks(width)
        weight = self.dimension / (width * len(blocks))
        general = self.general_actions[self.spent[self.general_actions] > 0]
        rare = self.rare_actions[self.spent[self.rare_actions] > 0]
        result = [self.make_block(codes, general, weight) for codes in blocks] if len(general) else []
        if len(rare):
            result.append(self.make_block(self.hash_codes & ((1 << hashbits) - 1), rare))
        return result

    def evaluate(self, point, setup):
        gradient = np.zeros(self.channels)
        value = 0.0
        rates = np.exp(point)
        for size, active, masks, exposures, weights, alternate, counts, weight in setup:
            partial = np.zeros(len(active))
            value += weight * LIB.evaluate(size, len(active), len(counts), masks, exposures,
                                           weights, alternate, contiguous(rates[active]), counts, partial)
            gradient[active] += weight * partial
        self.calls += 1
        return value, gradient

    def fit(self, point=None, width=10, hashbits=14, maxiter=70, deadline=49):
        if point is None:
            point = self.bounds.mean(axis=1)
        setup = self.setup(width, hashbits)
        started = time.process_time()
        best = [point.copy(), float('inf')]
        def objective(values):
            result = self.evaluate(values, setup)
            if result[0] < best[1]:
                best[:] = [values.copy(), result[0]]
            return result
        def callback(values):
            if time.process_time() >= deadline:
                raise TimeoutError
        try:
            fitted = minimize(objective, point, method='L-BFGS-B', jac=True, bounds=self.bounds,
                              callback=callback, options={'maxiter': maxiter, 'ftol': 1e-11, 'gtol': 0.001, 'maxcor': 15})
            result = fitted.x
        except TimeoutError:
            result = best[0]
        print('fit', width, hashbits, self.calls, round(time.process_time() - started, 3), round(time.process_time(), 3), file=sys.stderr, flush=True)
        return result

    def fisher(self, point, width=8):
        rates = np.exp(point)
        result = np.zeros((self.actions, self.channels, self.channels))
        blocks = self.blocks(width)
        weight = self.dimension / (width * len(blocks))
        work = [(codes, self.general_actions, weight) for codes in blocks]
        for target in np.unique(self.rare_target):
            work.append((self.local_codes(self.neighborhood(self.unions[target], width)),
                         self.rare_actions[self.rare_target == target], 1.0))
        for codes, actions, scale in work:
            size, active, masks, exposures, weights, alternate, counts, unused = self.make_block(codes, actions, observed=False)
            probabilities = np.zeros((len(actions), size))
            jacobian = np.zeros((len(actions), len(active), size))
            LIB.distribution(size, len(active), len(actions), masks, exposures, weights, alternate,
                             contiguous(rates[active]), probabilities, jacobian)
            for index, action in enumerate(actions):
                normalized = jacobian[index] / np.sqrt(np.maximum(probabilities[index], 1e-18))[None]
                result[action][np.ix_(active, active)] += scale * (normalized @ normalized.T)
        return result


def design(model, point, budget):
    started = time.process_time()
    fisher = model.fisher(point)
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
                      options={'maxiter': 60, 'ftol': 1e-8})
    allocation = np.maximum(result.x, 0)
    print('design', round(time.process_time() - started, 3), file=sys.stderr, flush=True)
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
                model.raw[action].append((syndromes, counts))
                model.spent[action] += shots
                remaining -= shots
                queries += 1
    pilot = np.zeros(model.actions, dtype=int)
    for action in model.general_actions:
        exposure = model.exposures[action, 0]
        if np.max(exposure[model.family != 'rare']) >= 2 and np.min(exposure) < 1:
            pilot[action] = 280
    for target in np.unique(model.rare_target):
        actions = model.rare_actions[model.rare_target == target]
        order = actions[np.argsort(model.exposures[actions, 0, target])]
        pilot[order[1]] = 90
        pilot[order[-1]] = 90
    collect(pilot)
    fitted = model.fit(width=8, hashbits=12)
    fractions, fisher = design(model, fitted, budget)
    total = int(budget - model.spent.sum())
    fractions[fractions * total < 180] = 0
    fractions /= fractions.sum()
    allocation = integer_allocation(fractions, total)
    available = spec['max_queries'] - queries
    while np.sum((allocation + maximum - 1) // maximum) > available:
        active = np.flatnonzero(allocation)
        fractions[active[np.argmin(allocation[active])]] = 0
        fractions /= fractions.sum()
        allocation = integer_allocation(fractions, total)
    print('allocate', allocation.tolist(), file=sys.stderr, flush=True)
    collect(allocation)
    fitted = model.fit(fitted, width=10, hashbits=14)
    if time.process_time() < 30:
        fitted = model.fit(fitted, width=12, hashbits=15, maxiter=40, deadline=51)
    return np.exp(fitted)


def main():
    spec = json.loads(sys.stdin.readline())['spec']
    def query(action, shots):
        print(json.dumps({'type': 'query', 'action': action, 'shots': shots}), flush=True)
        response = json.loads(sys.stdin.readline())
        if response.get('type') != 'observation':
            raise RuntimeError('Expected observation')
        return np.asarray(response['syndromes'], dtype=np.int64), np.asarray(response['multiplicities'])
    rates = calibrate(spec, query)
    print(json.dumps({'type': 'final', 'rates': rates.tolist()}, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
