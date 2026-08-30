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
from scipy.sparse.csgraph import reverse_cuthill_mckee, shortest_path
from scipy.sparse import csr_matrix

ROOT = Path(__file__).resolve().parent
LIB = ctypes.CDLL(str(ROOT / 'kernel.so'))
LIB.supports_avx2.restype = ctypes.c_int
if LIB.supports_avx2() and (ROOT / 'kernel_avx2.so').is_file():
    LIB = ctypes.CDLL(str(ROOT / 'kernel_avx2.so'))
DOUBLE = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
INTEGER = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
LIB.evaluate.argtypes = [ctypes.c_int] * 3 + [INTEGER] + [DOUBLE] * 6
LIB.evaluate.restype = ctypes.c_double
LIB.distribution.argtypes = [ctypes.c_int] * 3 + [INTEGER] + [DOUBLE] * 6
LIB.distribution.restype = None
LIB.joint_evaluate.argtypes = [ctypes.c_int] * 4 + [INTEGER] * 4 + [DOUBLE] * 7
LIB.joint_evaluate.restype = ctypes.c_double


def project(values, detectors):
    result = np.zeros(values.shape, dtype=np.int32)
    for offset, detector in enumerate(detectors):
        result |= (((values >> int(detector)) & 1) << offset).astype(np.int32)
    return result


class Model:
    def __init__(self, spec, bits=10):
        self.spec = spec
        self.dimension = spec['detector_count']
        self.bounds = np.log([channel['rate_bounds'] for channel in spec['channels']])
        self.channels = len(self.bounds)
        self.actions = len(spec['actions'])
        self.exposures = np.array([action['exposures'] for action in spec['actions']])
        self.weights = np.array([action['mode_weights'] for action in spec['actions']])
        self.alternate = np.array([action['alternate_probability'] for action in spec['actions']])
        self.original_masks = np.array([channel['masks'] for channel in spec['channels']], dtype=np.int64)
        self.groups = np.array([[channel['family'] == family for channel in spec['channels']]
                               for family in ('boundary', 'bulk', 'hook', 'rare')], dtype=float)
        self.groups /= self.groups.sum(axis=1, keepdims=True)
        self.spent = np.zeros(self.actions)
        self.raw = [[] for action in range(self.actions)]
        self.calls = 0
        self.make_blocks(bits)

    def make_blocks(self, bits, style=None):
        dimension = self.dimension
        adjacency = np.zeros((dimension, dimension))
        for first, second in self.spec['detector_edges']:
            adjacency[first, second] = adjacency[second, first] = 1
        if (style or os.environ.get('BLOCK_MODE', 'marginal')) == 'conditional':
            distances = shortest_path(csr_matrix(adjacency), directed=False)
            order = reverse_cuthill_mckee(csr_matrix(adjacency), symmetric_mode=True).tolist()
            regions = []
            signs = []
            core_width = int(os.environ.get('CORE_WIDTH', '3'))
            for start in range(0, dimension, core_width):
                core = order[start:start + core_width]
                previous = order[:start]
                if previous:
                    scores = np.min(distances[np.ix_(core, previous)], axis=0) - 0.05 * adjacency[np.ix_(core, previous)].sum(axis=0)
                    context = [previous[index] for index in np.argsort(scores, kind='stable')[:bits-len(core)]]
                else:
                    context = []
                regions.append(tuple(sorted(core + context)))
                signs.append(1.0)
                if context:
                    regions.append(tuple(sorted(context)))
                    signs.append(-1.0)
            self.coverage = np.ones(self.channels)
            self.block_weights = signs
            self.blocks = []
            for detectors in regions:
                masks = project(self.original_masks, detectors)
                active = np.flatnonzero(np.any(masks, axis=1))
                self.blocks.append((detectors, active, np.ascontiguousarray(masks[active]),
                                    np.ascontiguousarray(self.exposures[:, :, active]),
                                    np.ascontiguousarray(self.alternate[:, active])))
            self.bits = bits
            return
        unions = self.original_masks[:, 0] | self.original_masks[:, 1]
        footprints = [set(np.flatnonzero((int(mask) >> np.arange(dimension, dtype=np.int64)) & 1)) for mask in unions]
        candidates = set()
        for footprint in footprints:
            selected = set(footprint)
            distances = np.full(dimension, 100.0)
            distances[list(selected)] = 0
            for unused in range(dimension):
                updated = np.minimum(distances, np.min(np.where(adjacency, distances[:, None] + 1, 100), axis=0))
                if np.array_equal(updated, distances):
                    break
                distances = updated
            while len(selected) < bits:
                scores = -distances + 0.13 * adjacency[list(selected)].sum(axis=0)
                scores[list(selected)] = -1000
                selected.add(int(np.argmax(scores)))
            candidates.add(tuple(sorted(selected)))
        candidates = sorted(candidates)
        coverage = np.array([[footprint.issubset(candidate) for footprint in footprints] for candidate in candidates], float)
        accumulated = np.zeros(self.channels)
        chosen = []
        for unused in range(min(len(candidates), int(np.ceil(dimension / float(os.environ.get('BLOCK_DIVISOR', '3')))))):
            scores = coverage @ (1 / (0.35 + accumulated))
            scores[chosen] = -1
            index = int(np.argmax(scores))
            chosen.append(index)
            accumulated += coverage[index]
        while np.any(accumulated == 0):
            scores = coverage @ (accumulated == 0)
            index = int(np.argmax(scores))
            chosen.append(index)
            accumulated += coverage[index]
        self.coverage = accumulated
        if os.environ.get('ALL_BLOCKS'):
            chosen = list(range(len(candidates)))
            accumulated = coverage.sum(axis=0)
            self.coverage = accumulated
        self.block_weights = np.ones(len(chosen))
        self.blocks = []
        for index in chosen:
            detectors = candidates[index]
            masks = project(self.original_masks, detectors)
            active = np.flatnonzero(np.any(masks, axis=1))
            self.blocks.append((detectors, active, np.ascontiguousarray(masks[active]),
                                np.ascontiguousarray(self.exposures[:, :, active]),
                                np.ascontiguousarray(self.alternate[:, active])))
        self.bits = bits

    def setup(self):
        actions = np.flatnonzero(self.spent)
        result = []
        for block_weight, (detectors, active, masks, exposures, alternate) in zip(self.block_weights, self.blocks):
            size = 1 << len(detectors)
            counts = np.zeros((len(actions), size))
            for index, action in enumerate(actions):
                for syndromes, multiplicities in self.raw[action]:
                    codes = project(syndromes, detectors)
                    counts[index] += np.bincount(codes, weights=multiplicities, minlength=size)
            result.append((block_weight, active, masks, exposures[actions], self.weights[actions], alternate[actions], counts))
        return result

    def evaluate(self, point, setup):
        rates = np.exp(point)
        gradient = np.zeros(self.channels)
        value = 0.0
        for block_weight, active, masks, exposures, weights, alternate, counts in setup:
            partial = np.zeros(len(active))
            value += block_weight * LIB.evaluate(counts.shape[1], len(active), len(counts), masks, exposures,
                                  weights, alternate, rates[active], counts, partial)
            gradient[active] += block_weight * partial
        self.calls += 1
        return value, gradient

    def setup_joint(self):
        actions = np.flatnonzero(self.spent)
        syndromes = []
        multiplicities = []
        offsets = [0]
        for action in actions:
            codes = np.concatenate([entry[0] for entry in self.raw[action]])
            counts = np.concatenate([entry[1] for entry in self.raw[action]])
            unique, inverse = np.unique(codes, return_inverse=True)
            counts = np.bincount(inverse, weights=counts)
            syndromes.append(unique)
            multiplicities.append(counts)
            offsets.append(offsets[-1] + len(unique))
        syndromes = np.concatenate(syndromes)
        counts = np.concatenate(multiplicities)
        masks = np.stack([project(self.original_masks, block[0]) for block in self.blocks])
        projections = np.stack([project(syndromes, block[0]) for block in self.blocks])
        sizes = np.array([1 << len(block[0]) for block in self.blocks], dtype=np.int32)
        return (sizes, masks, np.array(offsets, dtype=np.int32), projections,
                np.array(self.block_weights, dtype=float), self.exposures[actions],
                self.weights[actions], self.alternate[actions], counts)

    def evaluate_joint(self, point, setup):
        sizes, masks, offsets, projections, signs, exposures, weights, alternate, counts = setup
        gradient = np.zeros(self.channels)
        value = LIB.joint_evaluate(self.channels, len(exposures), len(sizes), len(counts),
                                  sizes, masks, offsets, projections, signs, exposures,
                                  weights, alternate, np.exp(point), counts, gradient)
        self.calls += 1
        return value, gradient

    def fit(self, point=None, maxiter=90, deadline=48, joint=False):
        if point is None:
            point = self.bounds.mean(axis=1)
        setup = self.setup_joint() if joint else self.setup()
        evaluate = self.evaluate_joint if joint else self.evaluate
        best = [point.copy(), float('inf')]
        scale = max(self.spent.sum(), 1) * len(self.blocks)

        def objective(candidate):
            if time.process_time() > deadline and best[1] < float('inf'):
                raise TimeoutError
            value, gradient = evaluate(candidate, setup)
            if value < best[1]:
                best[:] = [candidate.copy(), value]
            return value / scale, gradient / scale

        try:
            result = minimize(objective, point, jac=True, bounds=self.bounds, method='L-BFGS-B',
                              options={'maxiter': maxiter, 'ftol': 2e-12, 'gtol': 1e-8, 'maxcor': 20})
            point = result.x
        except TimeoutError:
            point = best[0]
        print('fit', self.bits, self.spent.sum(), self.calls, time.process_time(), file=sys.stderr, flush=True)
        return point

    def fisher(self, point):
        rates = np.exp(point)
        fisher = np.zeros((self.actions, self.channels, self.channels))
        for block_weight, (detectors, active, masks, exposures, alternate) in zip(self.block_weights, self.blocks):
            size = 1 << len(detectors)
            for action in range(self.actions):
                probability = np.zeros((1, size))
                jacobian = np.zeros((1, len(active), size))
                LIB.distribution(size, len(active), 1, masks, exposures[action:action+1],
                                 self.weights[action:action+1], alternate[action:action+1],
                                 rates[active], probability, jacobian)
                scores = jacobian[0] / np.sqrt(probability[0])
                fisher[action][np.ix_(active, active)] += block_weight * (scores @ scores.T)
        normalization = np.sqrt(self.coverage)
        fisher /= normalization[None, :, None] * normalization[None, None, :]
        return fisher


def design(model, point, budget):
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
                      options={'maxiter': 70, 'ftol': 1e-8})
    allocation = np.maximum(result.x, 0)
    print('design', time.process_time(), file=sys.stderr, flush=True)
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
    amplified = model.exposures[:, 0] >= 2
    nonrare = model.groups[3] == 0
    general = amplified[:, nonrare].any(axis=1) & (model.exposures[:, 0].min(axis=1) < 1)
    pilot[general] = 220
    for channel in np.flatnonzero(model.groups[3]):
        candidates = np.flatnonzero((amplified.sum(axis=1) == 1) & amplified[:, channel])
        candidates = candidates[np.argsort(model.exposures[candidates, 0, channel])]
        for candidate in candidates[::2]:
            pilot[candidate] = 160
    collect(pilot)
    fitted = model.fit(deadline=16)
    fractions, fisher = design(model, fitted, budget)
    total = int(budget - model.spent.sum())
    fractions[fractions * total < 160] = 0
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
    fitted = model.fit(fitted, deadline=48)
    if time.process_time() < 25:
        model.make_blocks(12)
        fitted = model.fit(fitted, maxiter=60, deadline=48)
    information = np.einsum('a,akl->kl', model.spent, fisher) + np.eye(model.channels) * 1e-4
    covariance = cho_solve(cho_factor(information, lower=True, check_finite=False), np.eye(model.channels), check_finite=False)
    deviation = np.sqrt(np.diag(covariance))
    lower = (model.bounds[:, 0] - fitted) / deviation
    upper = (model.bounds[:, 1] - fitted) / deviation
    mass = np.maximum(ndtr(upper) - ndtr(lower), 1e-12)
    adjustment = deviation * (np.exp(-0.5 * lower**2) - np.exp(-0.5 * upper**2)) / (np.sqrt(2 * np.pi) * mass)
    fitted = np.clip(fitted + adjustment, model.bounds[:, 0], model.bounds[:, 1])
    print('complete', time.process_time(), file=sys.stderr, flush=True)
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
