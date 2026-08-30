import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import ctypes
import json
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from threadpoolctl import threadpool_limits
from search import baseline, write_submission, evaluate, ROOT
threadpool_limits(1)

library = ctypes.CDLL(str(ROOT / 'tensor.so'))
library.tensor.argtypes = [np.ctypeslib.ndpointer(np.int32, flags='C_CONTIGUOUS'), np.ctypeslib.ndpointer(np.float64, flags='C_CONTIGUOUS'), np.ctypeslib.ndpointer(np.float64, flags='C_CONTIGUOUS'), np.ctypeslib.ndpointer(np.float64, flags='C_CONTIGUOUS')]


def tensor(word, values):
    residual = np.zeros(125)
    jacobian = np.zeros((125, 17))
    library.tensor(np.ascontiguousarray(word, dtype=np.int32), np.ascontiguousarray(values), residual, jacobian)
    return residual, jacobian


def optimize_word(word, gram, initial=None, maxiter=100):
    counts = np.bincount(word, minlength=5)
    if np.any(counts == 0):
        return None
    constraint = (np.arange(5)[:, None] == word).astype(float)
    if initial is None:
        initial = .5 / counts[word]
    def objective(values):
        residual, jacobian = tensor(word, values)
        mapped = gram @ residual
        return residual @ mapped, 2 * jacobian.T @ mapped
    result = minimize(objective, initial, jac=True, method='SLSQP', bounds=[(1e-5 if index != 16 else 5e-6, .5) for index in range(17)], constraints={'type': 'eq', 'fun': lambda values: constraint @ values - .5, 'jac': lambda values: constraint}, options={'ftol': 2e-10, 'maxiter': maxiter})
    return result


def full(word, values):
    return np.concatenate([word, word[-2::-1]]), np.concatenate([values[:16], [2 * values[16]], values[15::-1]])


def search(seconds, seed):
    points = np.load(ROOT / 'gram.npz')['points']
    families = points.reshape(8, -1, 125, 125).mean(axis=1)
    gram = families.mean(axis=0)
    rng = np.random.default_rng(seed)
    start = time.time()
    population = []
    best = 1e6
    iteration = 0
    baseline_word, baseline_coeff = baseline()
    if seed in [90, 91]:
        baseline_values = baseline_coeff[:17].copy()
        baseline_values[-1] /= 2
        direction = tensor(baseline_word[:17], baseline_values)[0]
        mapped = gram @ direction
        strength = 3 if seed == 90 else 10
        gram = (1 + strength) * gram - strength * np.outer(mapped, mapped) / (direction @ mapped)
    initial_words = [baseline_word[:17]]
    if seed in [90, 91]:
        for filename in ['population_10.json', 'population_20.json', 'prunepopulation_99.json']:
            initial_words.extend(np.array(record[1]) for record in json.loads((ROOT / filename).read_text()))
    for repeat in range(40):
        mapping = rng.permutation(5)
        initial_words.append(mapping[baseline_word[:17]])
    for repeat in range(40):
        sequence = rng.permutation(5)
        initial_words.append(np.resize(sequence, 17))
    while time.time() - start < seconds:
        if iteration < len(initial_words):
            word = initial_words[iteration].copy()
        elif not population or rng.random() < .08:
            word = rng.integers(5, size=17)
        else:
            parent = population[int(rng.integers(min(15, len(population))))]
            word = np.array(parent[1]).copy()
            for mutation in range(1 if rng.random() < .75 else rng.integers(2, 5)):
                method = rng.integers(4)
                first, second = sorted(rng.choice(17, size=2, replace=False))
                if method == 0:
                    word[first], word[second] = word[second], word[first]
                elif method == 1:
                    word[first] = rng.integers(5)
                elif method == 2:
                    word[first:second+1] = np.roll(word[first:second+1], 1)
                else:
                    word[first:second+1] = word[first:second+1][::-1]
        iteration += 1
        if np.any(word[:-1] == word[1:]) or len(set(word)) < 5:
            continue
        result = optimize_word(word, gram)
        if result is None or not np.isfinite(result.fun):
            continue
        value = float(result.fun)
        if not any(np.array_equal(word, member[1]) for member in population):
            population.append((value, word.tolist(), result.x.tolist()))
            population.sort(key=lambda member: member[0])
            population = population[:30]
        if value < best:
            best = value
            residual, _ = tensor(word, result.x)
            family_scores = 1 / np.sqrt(np.einsum('a,fab,b->f', residual, families, residual))
            print(iteration, round(time.time() - start, 2), best, ''.join(map(str, word)), family_scores.round(3), flush=True)
            write_submission(*full(word, result.x), name=f'best_{seed}.json')
            (ROOT / f'population_{seed}.json').write_text(json.dumps(population))
        if iteration % 100 == 0:
            (ROOT / f'population_{seed}.json').write_text(json.dumps(population))
    (ROOT / f'population_{seed}.json').write_text(json.dumps(population))
    print('finished', iteration, time.time() - start, flush=True)


if __name__ == '__main__':
    import sys
    search(float(sys.argv[1]), int(sys.argv[2]))
