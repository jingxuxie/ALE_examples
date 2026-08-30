import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import sys
from pathlib import Path
import json
import time
import numpy as np
from scipy.linalg import null_space, qr
from scipy.optimize import minimize, LinearConstraint, Bounds

PARTICIPANT = Path(__file__).resolve().parents[2] / 'participant'
sys.path.insert(0, str(PARTICIPANT / 'workspace'))
import model

SIZES = [len(support) for support in model.SUPPORTS]
OFFSETS = np.cumsum([0] + SIZES)
ROWS = np.repeat(np.arange(32), SIZES)
LABELS = np.concatenate(model.SUPPORTS)
BASE = np.concatenate(model.rows_of(model.baseline())).astype(float)
LOWER = np.repeat([2] * 24 + [1] * 8, SIZES)
UPPER = np.repeat([42] * 24 + [21] * 8, SIZES)
CHAR = model.CHARACTERS[LABELS, 1:].astype(float) / 3000
PERM = model.PERMUTATIONS[:, 1:] - 1
IPERM = PERM[model.INVERSE]
ROWGRID = np.arange(32)[:, None]
PROBS = model.WEIGHTS[:, None] / 40
ALLA = np.zeros((32 + 256, len(BASE)))
ALLA[ROWS, np.arange(len(BASE))] = 1
ALLA[32 + LABELS, np.arange(len(BASE))] = model.WEIGHTS[ROWS]
_, triangular, selected = qr(ALLA.T, mode='economic', pivoting=True)
RANK = np.linalg.matrix_rank(ALLA)
A = ALLA[selected[:RANK]]
N = null_space(A)
LOOKUP = {(int(row), int(label)): index for index, (row, label) in enumerate(zip(ROWS, LABELS))}
Q = np.zeros((len(BASE), len(BASE)))
for index, (row, label) in enumerate(zip(ROWS, LABELS)):
    other = LOOKUP[(int(model.INVERSE[row]), int(model.PERMUTATIONS[model.INVERSE[row], label]))]
    Q[index, other] = model.WEIGHTS[row]
assert np.array_equal(Q, Q.T)


def artifact(vector):
    values = np.rint(vector).astype(int)
    return {'single': values[:72].reshape(4, 6, 3).tolist(),
            'cx': values[72:].reshape(8, 15).tolist()}


def curve(vector, history=False):
    eigen = np.empty((32, 255))
    for row in range(32):
        segment = slice(OFFSETS[row], OFFSETS[row + 1])
        eigen[row] = .98 + vector[segment] @ CHAR[segment]
    transformed = eigen[ROWGRID, PERM]
    weights = PROBS * eigen[model.INVERSE] * transformed
    vectors = np.ones((129, 255))
    for depth in range(128):
        vectors[depth + 1] = np.sum(weights * vectors[depth][PERM], axis=0)
    signal = vectors.mean(axis=1)
    if history:
        return signal, vectors, eigen, transformed, weights
    return signal


def fit(signal, gradient=False):
    depths = model.DEPTHS
    decay = .0198
    for iteration in range(10):
        shape = np.exp(-depths * decay)
        first = -depths * shape
        second = depths ** 2 * shape
        amplitude = (shape @ signal) / (shape @ shape)
        residual = amplitude * shape - signal
        haa = shape @ shape
        hat = (2 * amplitude * shape - signal) @ first
        htt = amplitude ** 2 * (first @ first) + amplitude * (residual @ second)
        derivative = amplitude * (residual @ first)
        step = derivative / (htt - hat * hat / haa)
        decay -= step
        if abs(step) < 1e-14:
            break
    bias = 1 + (255 / 256 / .02) * np.expm1(-decay)
    metrics = dict(relative_bias=bias, max_residual=np.abs(residual).max(),
                   amplitude=amplitude, decay=decay, depth_256_polarization=signal[-1])
    if not gradient:
        return metrics
    dt_dsignal = (amplitude * first - hat / haa * shape) / (htt - hat * hat / haa)
    db_dsignal = -(255 / 256 / .02) * np.exp(-decay) * dt_dsignal
    return metrics, db_dsignal


def objective(vector, gradient=True):
    signal, vectors, eigen, transformed, weights = curve(vector, True)
    metrics, db_dsignal = fit(signal, True)
    if not gradient:
        return -1000 * metrics['relative_bias']
    adjoint = np.full(255, db_dsignal[-1] / 255)
    dweights = np.zeros_like(weights)
    for depth in range(128, 0, -1):
        dweights += adjoint[None, :] * vectors[depth - 1][PERM]
        adjoint = (weights * adjoint)[ROWGRID, IPERM].sum(axis=0) + db_dsignal[depth - 1] / 255
    deigen = (PROBS * dweights * transformed)[model.INVERSE]
    deigen += (PROBS * dweights * eigen[model.INVERSE])[ROWGRID, IPERM]
    gradient_vector = np.empty_like(vector)
    for row in range(32):
        segment = slice(OFFSETS[row], OFFSETS[row + 1])
        gradient_vector[segment] = CHAR[segment] @ deigen[row]
    return -1000 * metrics['relative_bias'], -1000 * gradient_vector


def optimize(seed, iterations):
    rng = np.random.default_rng(seed)
    eigenvalues, eigenvectors = np.linalg.eigh(N.T @ Q @ N)
    direction = N @ eigenvectors[:, 0]
    initial = N @ rng.normal(size=N.shape[1])
    roots = np.roots([direction @ Q @ direction, 2 * initial @ Q @ direction, initial @ Q @ initial])
    initial += roots[np.argmin(np.abs(roots))].real * direction
    initial *= min(1, .9 * np.min(np.where(initial > 0, (UPPER - BASE) / (initial + 1e-30), (LOWER - BASE) / (initial - 1e-30))))
    start = BASE + initial
    constraint = {'type': 'eq', 'fun': lambda vector: (vector @ Q @ vector - 32640) / 1000,
                  'jac': lambda vector: 2 * Q @ vector / 1000}
    linear = LinearConstraint(A, A @ BASE, A @ BASE)
    counter = [0]
    started = time.monotonic()
    def callback(vector):
        counter[0] += 1
        if counter[0] % 25 == 0:
            print(seed, counter[0], fit(curve(vector)), 'overlap', vector @ Q @ vector,
                  'elapsed', time.monotonic() - started, flush=True)
            np.save(f'continuous_{seed}.npy', vector)
    result = minimize(objective, start, jac=True, method='SLSQP', bounds=Bounds(LOWER, UPPER),
                      constraints=[linear, constraint], callback=callback,
                      options={'maxiter': iterations, 'ftol': 1e-10, 'disp': True})
    np.save(f'continuous_{seed}.npy', result.x)
    print('RESULT', seed, result.message, fit(curve(result.x)), 'overlap', result.x @ Q @ result.x, flush=True)


if __name__ == '__main__':
    print('variables/rank/null', len(BASE), RANK, N.shape[1], flush=True)
    print('baseline', fit(curve(BASE)), flush=True)
    rng = np.random.default_rng(22)
    test = BASE + N @ rng.normal(size=N.shape[1])
    value, gradient_vector = objective(test)
    delta = N @ rng.normal(size=N.shape[1])
    finite = (objective(test + 1e-3 * delta, False) - objective(test - 1e-3 * delta, False)) / 2e-3
    print('gradient', gradient_vector @ delta, finite, flush=True)
    optimize(int(sys.argv[1]) if len(sys.argv) > 1 else 0, int(sys.argv[2]) if len(sys.argv) > 2 else 1000)
