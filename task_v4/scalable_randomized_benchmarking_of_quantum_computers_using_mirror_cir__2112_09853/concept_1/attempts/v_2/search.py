import ctypes
import json
import os
import sys
import time
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np
from scipy.linalg import null_space, qr
from scipy.optimize import minimize, minimize_scalar

ROOT = Path(__file__).resolve().parent
PARTICIPANT = ROOT.parent.parent / 'participant'
sys.path.insert(0, str(PARTICIPANT / 'workspace'))
import model

LAYERS = np.repeat(np.arange(32), [3] * 24 + [15] * 8)
PAULIS = np.concatenate(model.SUPPORTS)
BASE = np.array([20.] * 72 + [4.] * 120)
LOWER = np.array([2.] * 72 + [1.] * 120) - BASE
UPPER = np.array([42.] * 72 + [21.] * 120) - BASE
LOOKUP = {(int(layer), int(pauli)): index for index, (layer, pauli) in enumerate(zip(LAYERS, PAULIS))}
PARTNER = np.array([LOOKUP[model.INVERSE[layer], model.PERMUTATIONS[model.INVERSE[layer], pauli]]
                    for layer, pauli in zip(LAYERS, PAULIS)])
ROW_MATRIX = (np.arange(32)[:, None] == LAYERS).astype(float)
MARGINAL_MATRIX = (np.unique(PAULIS)[:, None] == PAULIS) * model.WEIGHTS[LAYERS]
LINEAR_FULL = np.vstack([ROW_MATRIX, MARGINAL_MATRIX])
_, triangular, pivots = qr(LINEAR_FULL.T, pivoting=True, mode='economic')
RANK = np.sum(np.abs(np.diag(triangular)) > 1e-9)
LINEAR = LINEAR_FULL[pivots[:RANK]]
NULL = null_space(LINEAR)
CHARACTERS = model.CHARACTERS.astype(float)
PERM = np.ascontiguousarray(model.PERMUTATIONS[:, 1:] - 1, dtype=np.int32)
PROB = model.WEIGHTS[:, None] / 40.
DEPTHS = model.DEPTHS

LIB = ctypes.CDLL(str(ROOT / 'engine.so'))
DOUBLE = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
INTEGER = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
LIB.forward.argtypes = [DOUBLE, INTEGER, DOUBLE, DOUBLE]
LIB.backward.argtypes = [DOUBLE, INTEGER, DOUBLE, DOUBLE, DOUBLE]


def artifact(deviation):
    counts = np.rint(deviation + BASE).astype(int)
    return {'single': counts[:72].reshape(4, 6, 3).tolist(), 'cx': counts[72:].reshape(8, 15).tolist()}


def overlaps(deviation):
    products = deviation * deviation[PARTNER]
    return np.array([products[:72].sum(), products[72:].sum()])


def overlap_jac(deviation):
    gradient = np.zeros((2, 192))
    gradient[0, :72] = 2 * deviation[PARTNER[:72]]
    gradient[1, 72:] = 2 * deviation[PARTNER[72:]]
    return gradient


class Objective:
    def __init__(self):
        self.last = None
        self.calls = 0

    def calculate(self, deviation):
        if self.last is not None and np.array_equal(self.last, deviation):
            return self.value, self.gradient
        self.last = deviation.copy()
        counts = np.zeros((32, 256))
        counts[LAYERS, PAULIS] = BASE + deviation
        eigenvalues = 0.98 + counts @ CHARACTERS / 3000.
        transformed = np.take_along_axis(eigenvalues, model.PERMUTATIONS, axis=1)
        weights = np.ascontiguousarray((PROB * eigenvalues[model.INVERSE] * transformed)[:, 1:])
        vectors = np.empty((129, 255))
        signal = np.empty(129)
        LIB.forward(weights, PERM, vectors, signal)

        def loss(decay):
            shape = np.exp(-decay * DEPTHS)
            amplitude = np.dot(shape, signal) / np.dot(shape, shape)
            return np.sum((amplitude * shape - signal) ** 2)

        result = minimize_scalar(loss, bounds=(0.018, 0.022), method='bounded', options={'xatol': 1e-14})
        decay = result.x
        shape = np.exp(-decay * DEPTHS)
        amplitude = np.dot(shape, signal) / np.dot(shape, shape)
        residual = amplitude * shape - signal
        jac = np.array([shape, -amplitude * DEPTHS * shape]).T
        hessian = jac.T @ jac
        cross = np.dot(residual, -DEPTHS * shape)
        hessian[0, 1] += cross
        hessian[1, 0] += cross
        hessian[1, 1] += np.dot(residual, amplitude * DEPTHS ** 2 * shape)
        signal_gradient = np.ascontiguousarray(np.linalg.solve(hessian, jac.T)[1] * 1e6)
        weight_gradient = np.empty((32, 255))
        LIB.backward(weights, PERM, vectors, signal_gradient, weight_gradient)
        eigengrad = np.zeros((32, 256))
        for layer in range(32):
            weighted = weight_gradient[layer] * PROB[layer, 0]
            eigengrad[model.INVERSE[layer], 1:] += weighted * transformed[layer, 1:]
            eigengrad[layer, model.PERMUTATIONS[layer, 1:]] += weighted * eigenvalues[model.INVERSE[layer], 1:]
        self.value = decay * 1e6
        self.gradient = np.einsum('ij,ij->i', eigengrad[LAYERS], CHARACTERS[PAULIS]) / 3000.
        self.metrics = {'bias': 1 - (255 / 256) * (-np.expm1(-decay)) / .02,
                        'residual': float(np.max(np.abs(residual))), 'tail': float(signal[-1]),
                        'amplitude': float(amplitude)}
        self.calls += 1
        return self.value, self.gradient


def continuous(seed=0, previous=None):
    rng = np.random.default_rng(seed)
    objective = Objective()
    if previous is None:
        start = NULL @ rng.normal(0, 2., NULL.shape[1])
    else:
        start = previous + NULL @ rng.normal(0, 0.5, NULL.shape[1])
    counter = 0
    started = time.monotonic()

    def callback(deviation):
        nonlocal counter
        counter += 1
        if counter % 20 == 0:
            objective.calculate(deviation)
            print('iter', seed, counter, objective.metrics, 'q', overlaps(deviation),
                  'elapsed', time.monotonic() - started, flush=True)
            np.save(ROOT / f'progress_{seed}.npy', deviation)

    result = minimize(objective.calculate, start, jac=True, method='SLSQP',
                      bounds=list(zip(LOWER, UPPER)),
                      constraints=[{'type': 'eq', 'fun': lambda deviation: LINEAR @ deviation,
                                    'jac': lambda deviation: LINEAR},
                                   {'type': 'eq', 'fun': lambda deviation: overlaps(deviation) / 1000.,
                                    'jac': lambda deviation: overlap_jac(deviation) / 1000.}],
                      callback=callback, options={'maxiter': 500, 'ftol': 1e-10, 'disp': True})
    np.save(ROOT / f'continuous_{seed}.npy', result.x)
    objective.calculate(result.x)
    print('RESULT', seed, result.success, objective.metrics, 'q', overlaps(result.x), flush=True)
    return result.x


if __name__ == '__main__':
    print('rank', RANK, 'null', NULL.shape, flush=True)
    objective = Objective()
    started = time.monotonic()
    objective.calculate(np.zeros(192))
    print('baseline', objective.metrics, 'time', time.monotonic() - started, flush=True)
    test = NULL @ np.random.default_rng(4).normal(size=NULL.shape[1])
    value, gradient = objective.calculate(test)
    direction = NULL[:, 0]
    difference = (objective.calculate(test + direction * .001)[0] - objective.calculate(test - direction * .001)[0]) / .002
    print('gradient', difference, gradient @ direction, flush=True)
    for seed in range(5):
        continuous(seed)
