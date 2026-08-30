import argparse
import ctypes
import json
import math
import os
import time
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares, minimize
import fermion


ROOT = Path(__file__).resolve().parent
LIB = ctypes.CDLL(str(ROOT / 'engine.so'))
INT = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
DOUBLE = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
LIB.initialize.argtypes = [ctypes.c_int, ctypes.c_int, INT, INT, INT, DOUBLE]
LIB.state_jac.argtypes = [ctypes.c_int, INT, DOUBLE, DOUBLE, DOUBLE, DOUBLE]
LIB.loss_grad.argtypes = [ctypes.c_int, INT, DOUBLE, DOUBLE, DOUBLE, DOUBLE]
LIB.loss_grad.restype = ctypes.c_double
LIB.candidates.argtypes = [ctypes.c_int, INT, DOUBLE, DOUBLE, DOUBLE, ctypes.c_int, DOUBLE, DOUBLE]
LIB.projected_options.argtypes = [ctypes.c_int, INT, DOUBLE, DOUBLE, DOUBLE, ctypes.c_int, DOUBLE, DOUBLE, DOUBLE]


class Engine:
    def __init__(self, case):
        self.case = case
        self.labels = fermion.allowed_excitations(case.n_orbitals)
        keep = [index for index, mask in enumerate(case.determinants) if sum((mask >> orbital) & 1 for orbital in range(0, case.n_orbitals, 2)) == case.n_alpha]
        mapping = {old: new for new, old in enumerate(keep)}
        self.initial = fermion.reference_state(case)[keep].copy()
        self.target = case.target[keep].copy()
        self.dimension = len(keep)
        sources, destinations, signs, starts = [], [], [], [0]
        for label in self.labels:
            pair_source, pair_dest, pair_sign = fermion.rotation_pairs(case.n_orbitals, case.n_electrons, label)
            for source, dest, sign in zip(pair_source, pair_dest, pair_sign):
                if int(source) in mapping:
                    sources.append(mapping[int(source)])
                    destinations.append(mapping[int(dest)])
                    signs.append(sign)
            starts.append(len(sources))
        self.arrays = (np.array(starts, np.int32), np.array(sources, np.int32), np.array(destinations, np.int32), np.array(signs, np.float64))
        LIB.initialize(self.dimension, len(self.labels), *self.arrays)
        self.best = 1e10
        self.started = time.time()

    def state_jac(self, labels, angles):
        labels = np.asarray(labels, dtype=np.int32)
        angles = np.ascontiguousarray(angles, dtype=np.float64)
        state = np.empty(self.dimension)
        jacobian = np.empty((len(labels), self.dimension))
        LIB.state_jac(len(labels), labels, angles, self.initial, state, jacobian)
        return state, jacobian.T

    def optimize(self, labels, angles, evaluations=100, tolerance=1e-10):
        labels = np.asarray(labels, dtype=np.int32)
        initial_state, _ = self.state_jac(labels, angles)
        if initial_state @ self.target < 0:
            self.target = -self.target
        previous = None
        def evaluate(parameters):
            nonlocal previous
            if previous is None or not np.array_equal(previous[0], parameters):
                state, jacobian = self.state_jac(labels, parameters)
                previous = (parameters.copy(), state - self.target, jacobian)
            return previous
        result = least_squares(lambda parameters: evaluate(parameters)[1], angles, jac=lambda parameters: evaluate(parameters)[2], method='lm' if len(labels) <= self.dimension else 'trf', max_nfev=evaluations, ftol=tolerance, xtol=tolerance, gtol=tolerance)
        return np.asarray(labels, np.int32), (result.x + math.pi) % (2 * math.pi) - math.pi, 2 * result.cost

    def options(self, labels, angles, replacement=False):
        labels = np.asarray(labels, dtype=np.int32)
        angles = np.ascontiguousarray(angles, dtype=np.float64)
        values = np.empty((len(labels) + 1 - int(replacement), len(self.labels)))
        optimal = np.empty_like(values)
        LIB.candidates(len(labels), labels, angles, self.initial, self.target, int(replacement), values, optimal)
        return values, optimal

    def projected(self, labels, angles):
        labels = np.asarray(labels, dtype=np.int32)
        angles = np.ascontiguousarray(angles, dtype=np.float64)
        state, jacobian = self.state_jac(labels, angles)
        left, singular, right = np.linalg.svd(jacobian, full_matrices=False)
        rank = np.count_nonzero(singular > 1e-7)
        basis = np.ascontiguousarray(left[:, :rank].T)
        residual = self.target - state
        values = np.empty((len(labels) + 1, len(self.labels)))
        optimal = np.empty_like(values)
        LIB.projected_options(len(labels), labels, angles, self.initial, residual, rank, basis, values, optimal)
        return values, optimal

    def save(self, labels, angles, loss, suffix='best'):
        destination = ROOT / (self.case.case_id + '_' + suffix + '.json')
        if suffix == 'best' and destination.exists():
            current = json.loads(destination.read_text())['loss']
            self.best = min(self.best, current)
        if suffix == 'best' and loss >= self.best:
            return
        if suffix == 'best':
            self.best = loss
            print(self.case.case_id, 'BEST', len(labels), 'loss', '%.12g' % loss, 'elapsed', round(time.time() - self.started, 2), flush=True)
        gates = [{'annihilate': list(self.labels[int(label)].annihilate), 'create': list(self.labels[int(label)].create), 'theta': float(angle)} for label, angle in zip(labels, angles)]
        temporary = destination.with_suffix('.tmp.' + str(os.getpid()))
        temporary.write_text(json.dumps({'case_id': self.case.case_id, 'gates': gates, 'loss': loss}))
        temporary.replace(destination)

    def load(self, suffix='best'):
        data = json.loads((ROOT / (self.case.case_id + '_' + suffix + '.json')).read_text())
        labels = [self.labels.index(fermion.Excitation(tuple(gate['annihilate']), tuple(gate['create']))) for gate in data['gates']]
        angles = [gate['theta'] for gate in data['gates']]
        state, _ = self.state_jac(labels, angles)
        if state @ self.target < 0:
            self.target = -self.target
        return np.asarray(labels, np.int32), np.asarray(angles), data['loss']

    def grow(self, cap, rng, width=1):
        labels, angles = np.empty(0, np.int32), np.empty(0)
        for step in range(cap):
            values, optimal = self.options(labels, angles)
            candidates = np.argsort(values.ravel())[-width:][::-1]
            trials = []
            for flat in candidates:
                position, label = np.unravel_index(flat, values.shape)
                trial_labels = np.insert(labels, position, label)
                trial_angles = np.insert(angles, position, optimal[position, label])
                trials.append(self.optimize(trial_labels, trial_angles, 100))
            labels, angles, loss = min(trials, key=lambda trial: trial[2])
            if step % 4 == 3 or step == cap - 1:
                print(self.case.case_id, 'grow', step + 1, loss, flush=True)
        return labels, angles, loss

    def polish(self, labels, angles, loss, rounds=100, width=20, rng=None):
        for iteration in range(rounds):
            values, optimal = self.options(labels, angles, replacement=True)
            values[np.arange(len(labels)), labels] = -np.inf
            candidates = np.argsort(values.ravel())[-width:][::-1]
            best = (labels, angles, loss)
            for flat in candidates:
                position, label = np.unravel_index(flat, values.shape)
                trial_labels, trial_angles = labels.copy(), angles.copy()
                trial_labels[position] = label
                trial_angles[position] = optimal[position, label]
                result = self.optimize(trial_labels, trial_angles, 100)
                if result[2] < best[2] - 1e-13:
                    best = result
            if best[2] >= loss - 1e-13:
                break
            labels, angles, loss = best
            if len(labels) <= self.case.max_gates:
                self.save(labels, angles, loss)
            if loss < 1e-12:
                break
        return labels, angles, loss


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', type=int, default=0)
    parser.add_argument('--seconds', type=float, default=600)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--width', type=int, default=5)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    engine = Engine(fermion.load_cases()[args.case])
    rng = np.random.default_rng(args.seed)
    if args.resume:
        labels, angles, loss = engine.load()
    else:
        labels, angles, loss = engine.grow(engine.case.max_gates, rng, args.width)
    engine.save(labels, angles, loss)
    labels, angles, loss = engine.polish(labels, angles, loss, rounds=200, width=30)
    incumbent = (labels, angles, loss)
    iteration = 0
    while time.time() - engine.started < args.seconds and engine.best > 1e-12:
        iteration += 1
        labels, angles, loss = (incumbent[0].copy(), incumbent[1].copy(), incumbent[2])
        for mutation in range(int(rng.integers(1, 5))):
            position = int(rng.integers(len(labels)))
            labels = np.delete(labels, position)
            angles = np.delete(angles, position)
            values, optimal = engine.options(labels, angles)
            top = np.argsort(values.ravel())[-40:]
            flat = rng.choice(top)
            position, label = np.unravel_index(flat, values.shape)
            labels = np.insert(labels, position, label)
            angles = np.insert(angles, position, optimal[position, label])
        labels, angles, loss = engine.optimize(labels, angles, 100)
        labels, angles, loss = engine.polish(labels, angles, loss, rounds=20, width=10)
        engine.save(labels, angles, loss)
        if loss < incumbent[2] or rng.random() < np.exp(min(0, (incumbent[2] - loss) / 0.005)):
            incumbent = (labels, angles, loss)
        if iteration % 10 == 0:
            print('iteration', iteration, 'current', loss, 'best', engine.best, flush=True)


if __name__ == '__main__':
    main()
