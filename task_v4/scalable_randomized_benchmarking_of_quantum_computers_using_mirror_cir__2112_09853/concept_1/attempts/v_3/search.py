import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import ctypes
import json
import time
import numpy as np
from scipy.linalg import null_space, qr
from scipy.optimize import minimize, LinearConstraint

ROOT = Path(__file__).resolve().parent
PARTICIPANT = ROOT.parent.parent / 'participant'
sys.path.insert(0, str(PARTICIPANT / 'workspace'))
import model

BASE = np.r_[np.full(72, 20.), np.full(120, 4.)]
LOWER = np.r_[np.full(72, 2.), np.full(120, 1.)]
UPPER = np.r_[np.full(72, 42.), np.full(120, 21.)]
OFFSETS = np.r_[np.arange(0, 73, 3), np.arange(87, 193, 15)].astype(np.int32)
LABELS = np.concatenate(model.SUPPORTS)
LAYERS = np.repeat(np.arange(32), np.diff(OFFSETS))
MAPPING = {(layer, label): entry for entry, (layer, label) in enumerate(zip(LAYERS, LABELS))}
PAIR = np.array([MAPPING[model.INVERSE[layer], model.PERMUTATIONS[model.INVERSE[layer], label]]
                 for layer, label in zip(LAYERS, LABELS)])
assert np.array_equal(PAIR[PAIR], np.arange(192))

def linear_matrix():
    rows = [np.equal(LAYERS, layer).astype(float) for layer in range(32)]
    for begin, end in ((0, 24), (24, 32)):
        for label in np.unique(LABELS[(LAYERS >= begin) & (LAYERS < end)]):
            rows.append(((LAYERS >= begin) & (LAYERS < end) & (LABELS == label)).astype(float))
    return np.array(rows)

LINEAR = linear_matrix()
NULL = null_space(LINEAR)
SINGLE_Q = NULL[:72].T @ NULL[PAIR[:72]]
CNOT_Q = NULL[72:].T @ NULL[PAIR[72:]]
LIB = ctypes.CDLL(str(ROOT / 'kernel.so'))
INT_POINTER = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
DOUBLE_POINTER = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
LIB.initialize.argtypes = [INT_POINTER, INT_POINTER, INT_POINTER, DOUBLE_POINTER]
LIB.compute.argtypes = [DOUBLE_POINTER, DOUBLE_POINTER, DOUBLE_POINTER, DOUBLE_POINTER, ctypes.c_int]
LIB.initialize(np.ascontiguousarray(model.PERMUTATIONS[:, 1:] - 1, dtype=np.int32),
               model.INVERSE.astype(np.int32), OFFSETS,
               np.ascontiguousarray(model.CHARACTERS[LABELS, 1:] / 3000.))

def metrics(counts, gradient=False):
    signal = np.zeros(129)
    derivative = np.zeros(192)
    result = np.zeros(4)
    LIB.compute(np.ascontiguousarray(counts, dtype=float), signal, derivative, result, int(gradient))
    return result, signal, derivative

def artifact(counts):
    counts = np.asarray(counts).astype(int)
    return {'single': counts[:72].reshape(4, 6, 3).tolist(), 'cx': counts[72:].reshape(8, 15).tolist()}

def overlaps(counts):
    deviations = counts - BASE
    return np.array([deviations[:72] @ deviations[PAIR[:72]], deviations[72:] @ deviations[PAIR[72:]]])

def random_start(rng):
    displacement = np.zeros(192)
    for start, stop in ((0, 72), (72, 192)):
        basis = null_space(LINEAR[:, start:stop])
        quadratic = basis.T @ basis[PAIR[start:stop] - start]
        values, vectors = np.linalg.eigh(quadratic)
        positive = vectors[:, values > 1e-8] @ (rng.normal(size=np.sum(values > 1e-8)) / np.sqrt(values[values > 1e-8]))
        negative = vectors[:, values < -1e-8] @ (rng.normal(size=np.sum(values < -1e-8)) / np.sqrt(-values[values < -1e-8]))
        positive /= np.sqrt(positive @ quadratic @ positive)
        negative /= np.sqrt(-negative @ quadratic @ negative)
        direction = basis @ (positive + negative)
        ratios = np.where(direction > 0, (UPPER[start:stop] - BASE[start:stop]) / direction,
                          (LOWER[start:stop] - BASE[start:stop]) / direction)
        displacement[start:stop] = direction * np.min(ratios) * 0.7
    return NULL.T @ displacement

def optimize(seed, initial=None):
    rng = np.random.default_rng(seed)
    start = random_start(rng) if initial is None else NULL.T @ (initial - BASE)
    calls = 0
    last = time.monotonic()
    def objective(parameters):
        nonlocal calls, last
        result, signal, gradient = metrics(BASE + NULL @ parameters, True)
        calls += 1
        if time.monotonic() - last > 20:
            print('progress', seed, calls, result, flush=True)
            last = time.monotonic()
        return -result[0] * 10000, -10000 * (NULL.T @ gradient)
    def calibration(parameters):
        return np.array([parameters @ SINGLE_Q @ parameters, parameters @ CNOT_Q @ parameters]) / 1000
    def calibration_jac(parameters):
        return 2 * np.array([SINGLE_Q @ parameters, CNOT_Q @ parameters]) / 1000
    constraints = [LinearConstraint(NULL, LOWER - BASE, UPPER - BASE),
                   {'type': 'eq', 'fun': calibration, 'jac': calibration_jac}]
    result = minimize(objective, start, jac=True, constraints=constraints,
                      method='SLSQP', options={'maxiter': 1500, 'ftol': 1e-10, 'disp': True})
    counts = BASE + NULL @ result.x
    measured = metrics(counts)[0]
    print('RESULT', seed, result.success, result.message, measured, overlaps(counts), flush=True)
    np.save(ROOT / f'continuous_{seed}.npy', counts)
    return counts

if __name__ == '__main__':
    print('dimension', NULL.shape, 'baseline', metrics(BASE)[0], flush=True)
    print('public baseline', model.evaluate(model.baseline()), flush=True)
    rng = np.random.default_rng(99)
    point = BASE + NULL @ random_start(rng)
    result, signal, gradient = metrics(point, True)
    direction = NULL @ rng.normal(size=NULL.shape[1])
    delta = 1e-3
    finite = (metrics(point + delta * direction)[0][0] - metrics(point - delta * direction)[0][0]) / (2 * delta)
    print('gradient check', gradient @ direction, finite, flush=True)
    global_counts = np.zeros((32, 256))
    global_counts[LAYERS, LABELS] = point
    print('curve difference', np.max(np.abs(signal - model.exact_curve(global_counts))), flush=True)
    for seed in range(10):
        optimize(seed)
