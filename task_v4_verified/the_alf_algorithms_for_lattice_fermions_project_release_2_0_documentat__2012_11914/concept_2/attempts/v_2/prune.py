import ctypes
import json
import time
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp, softmax
from optimize import ROOT
from search import write_submission

library = ctypes.CDLL(str(ROOT / 'tensor_generic.so'))
library.tensor_generic.argtypes = [ctypes.c_int, np.ctypeslib.ndpointer(np.int32, flags='C_CONTIGUOUS'), np.ctypeslib.ndpointer(np.float64, flags='C_CONTIGUOUS'), np.ctypeslib.ndpointer(np.float64, flags='C_CONTIGUOUS'), np.ctypeslib.ndpointer(np.float64, flags='C_CONTIGUOUS')]
data = np.load(ROOT / 'riskgram.npz')
projection, points = data['projection'], data['points']
mean_gram = points.mean(axis=0)
public_gram = projection.T @ np.load(ROOT / 'gram.npz')['points'].mean(axis=(0, 1)) @ projection
CORE_GUARD = False


def tensor(word, values):
    count = len(word)
    residual = np.zeros(125)
    jacobian = np.zeros((125, count))
    library.tensor_generic(count, np.ascontiguousarray(word, dtype=np.int32), np.ascontiguousarray(values), residual, jacobian)
    return residual @ projection, projection.T @ jacobian


def optimize(word, initial=None, maxiter=100):
    count = len(word)
    counts = np.bincount(word, minlength=5)
    constraint = (np.arange(5)[:, None] == word).astype(float)
    if initial is None:
        initial = .5 / counts[word]
    def objective(values):
        residual, jacobian = tensor(word, values)
        mapped = points @ residual
        losses = mapped @ residual
        weights = softmax(losses / .02) + .3 / len(losses)
        value = .02 * logsumexp(losses / .02) + .3 * losses.mean()
        gradient = 2 * jacobian.T @ (weights @ mapped)
        if CORE_GUARD:
            public_mapped = public_gram @ residual
            public_loss = residual @ public_mapped
            excess = max(public_loss - .27, 0)
            value += 100 * excess ** 2
            gradient += 400 * excess * jacobian.T @ public_mapped
        return value, gradient
    return minimize(objective, initial, jac=True, method='SLSQP', bounds=[(1e-5 if index != count - 1 else 5e-6, .5) for index in range(count)], constraints={'type': 'eq', 'fun': lambda values: constraint @ values - .5, 'jac': lambda values: constraint}, options={'ftol': 1e-9, 'maxiter': maxiter})


def merge(word, values):
    new_word, new_values = [], []
    for component, value in zip(word, values):
        if new_word and new_word[-1] == component:
            new_values[-1] += value
        else:
            new_word.append(component)
            new_values.append(value)
    count = (len(new_word) + 1) // 2
    new_word, new_values = np.array(new_word[:count]), np.array(new_values[:count])
    new_values[-1] /= 2
    for component in range(5):
        mask = new_word == component
        if mask.any():
            new_values[mask] *= .5 / new_values[mask].sum()
    return new_word, new_values


def expand(word, values):
    return np.r_[word, word[-2::-1]], np.r_[values[:-1], values[-1] * 2, values[-2::-1]]


def run(seed, width=10):
    rng = np.random.default_rng(seed)
    start = time.time()
    frontier = {count: [] for count in range(17, 26)}
    seen = set()
    for repeat in range(35):
        order = rng.permutation(5)
        if repeat < 25:
            word, values = [], []
            for substep in range(6):
                word.extend(list(order) + list(order[-2::-1]))
                values.extend([1 / 12] * 4 + [1 / 6] + [1 / 12] * 4)
            word, values = merge(word, values)
        else:
            word = np.resize(order, 25)
            values = .5 / np.bincount(word)[word]
        result = optimize(word, values)
        frontier[len(word)].append((float(result.fun), word.tolist(), result.x.tolist()))
    for count in range(25, 17, -1):
        frontier[count].sort()
        current = frontier[count][:width]
        print('LEVEL', count, len(frontier[count]), current[0][0] if current else None, round(time.time() - start, 2), flush=True)
        for _, half_word, half_values in current:
            full_word, full_values = expand(np.array(half_word), np.array(half_values))
            for removed in range(count):
                mask = np.ones(2 * count - 1, dtype=bool)
                mask[removed] = False
                mask[2 * count - 2 - removed] = False
                word, values = merge(full_word[mask], full_values[mask])
                if len(word) < 17 or len(set(word)) < 5 or tuple(word) in seen:
                    continue
                seen.add(tuple(word))
                result = optimize(word, values)
                if not result.success:
                    result = optimize(word, result.x, maxiter=200)
                frontier[len(word)].append((float(result.fun), word.tolist(), result.x.tolist()))
        frontier[17].sort()
        if frontier[17]:
            value, word, values = frontier[17][0]
            residual, _ = tensor(np.array(word), np.array(values))
            losses = (points @ residual) @ residual
            print('FINAL BEST', value, np.sqrt(losses.max()), losses.mean(), ''.join(map(str, word)), flush=True)
            write_submission(*expand(np.array(word), np.array(values)), name=f'prunebest_{seed}.json')
            (ROOT / f'prunepopulation_{seed}.json').write_text(json.dumps(frontier[17][:30]))
    print('finished', time.time() - start, flush=True)


if __name__ == '__main__':
    import sys
    CORE_GUARD = int(sys.argv[1]) != 99
    run(int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 10)
