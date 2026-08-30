import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import sys
import time
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logsumexp, softmax
from optimize import tensor, full, optimize_word
from search import ROOT, baseline, load_instances, stage_exp, write_submission
from validate import generate


def basis():
    vectors = []
    for first in range(5):
        for second in range(5):
            for third in range(second + 1, 5):
                vector = np.zeros((5, 5, 5))
                vector[first, second, third] += 1
                vector[first, third, second] -= 1
                vector[second, third, first] -= 1
                vector[third, second, first] += 1
                vectors.append(vector.ravel())
    vectors, singular, _ = np.linalg.svd(np.array(vectors).T, full_matrices=False)
    return vectors[:, singular > 1e-10]


def build():
    projection = basis()
    public = load_instances()
    synthetic = generate(30, seed=932112)
    instances = []
    for family in range(8):
        instances.extend(public[family * 6:(family + 1) * 6])
        instances.extend(synthetic[family * 30:(family + 1) * 30])
    baseline_word, baseline_coeff = baseline()
    grams = []
    start = time.time()
    for identity, _, matrices in instances:
        eigenvalues, eigenvectors = np.linalg.eigh(matrices.sum(axis=0))
        centered = matrices.copy()
        centered[4] -= np.eye(len(eigenvalues)) * np.trace(centered[4]) / len(eigenvalues)
        triples = np.array([first @ second @ third for first in centered for second in centered for third in centered])
        triples = (triples + triples.conj().transpose(0, 2, 1)) / 2
        transformed = eigenvectors.conj().T @ triples @ eigenvectors
        transformed = np.einsum('af,aij->fij', projection, transformed)
        for step, repetitions, observable in [(.4, 1, 1), (1., 4, 0), (1., 4, 1)]:
            left = np.eye(len(eigenvalues), dtype=complex)
            for index in range(17):
                left = left @ stage_exp(matrices, baseline_word[index], step * baseline_coeff[index] * (.5 if index == 16 else 1.))
            vectors, singular, _ = np.linalg.svd(left)
            product = left @ left.conj().T
            times = repetitions * step
            differences = times * (eigenvalues[:, None] - eigenvalues[None, :])
            if observable == 0:
                values = np.exp(times * eigenvalues)
                derivative = values
                approximation = np.linalg.matrix_power(product, repetitions)
            else:
                values = expit(-times * eigenvalues)
                derivative = -values * (1 - values)
                approximation = (vectors * expit(-2 * repetitions * np.log(singular))) @ vectors.conj().T
            exact = (eigenvectors * values) @ eigenvectors.conj().T
            denominator = np.linalg.norm(approximation - exact)
            with np.errstate(divide='ignore', invalid='ignore'):
                divided = (values[:, None] - values[None, :]) / differences
            np.fill_diagonal(divided, derivative)
            weighted = (transformed * (repetitions * step ** 3 * divided)[None]).reshape(40, -1) / denominator
            grams.append((weighted.conj() @ weighted.T).real)
    np.savez(ROOT / 'riskgram.npz', points=np.array(grams), projection=projection)
    print('built', len(grams), time.time() - start, flush=True)


def optimize(word, points, projection, initial=None, mode='penalty'):
    counts = np.bincount(word, minlength=5)
    constraint = (np.arange(5)[:, None] == word).astype(float)
    if initial is None:
        initial = optimize_word(word, projection @ points.mean(axis=0) @ projection.T).x
    def objective(values):
        residual, jacobian = tensor(word, values)
        residual = residual @ projection
        jacobian = projection.T @ jacobian
        mapped = points @ residual
        losses = mapped @ residual
        if mode == 'max':
            weights = softmax(losses / .02) + .3 / len(losses)
            value = .02 * logsumexp(losses / .02) + .3 * losses.mean()
        else:
            excess = np.maximum(losses - .58, 0)
            weights = (1 + 100 * excess) / len(losses)
            value = losses.mean() + 50 * np.mean(excess ** 2)
        gradient = 2 * jacobian.T @ (weights @ mapped)
        return value, gradient
    return minimize(objective, initial, jac=True, method='SLSQP', bounds=[(1e-5 if index != 16 else 5e-6, .5) for index in range(17)], constraints={'type': 'eq', 'fun': lambda values: constraint @ values - .5, 'jac': lambda values: constraint}, options={'ftol': 1e-9, 'maxiter': 90})


def search(seconds, seed):
    data = np.load(ROOT / 'riskgram.npz')
    points, projection = data['points'], data['projection']
    rng = np.random.default_rng(seed)
    population = []
    initial_words = []
    if seed in [60, 70]:
        count = 2 if seed == 60 else 3
        for repeat in range(200):
            sequence = list(np.resize(rng.permutation(4), 17 - count))
            for location in sorted(rng.choice(17, size=count, replace=False)):
                sequence.insert(int(location), 4)
            initial_words.append(np.array(sequence))
    if seed == 40:
        import itertools
        permutations = list(itertools.permutations(range(4)))
        for first in permutations:
            for second in permutations:
                first = list(first)
                second = list(second)
                initial_words.append(np.array([4] + first + first[-2::-1] + [4] + second + second[-2::-1] + [4]))
        rng.shuffle(initial_words)
    for filename in ['population_10.json', 'population_20.json']:
        if (ROOT / filename).exists():
            initial_words.extend(np.array(record[1]) for record in json.loads((ROOT / filename).read_text()))
    for repeat in range(20):
        initial_words.append(rng.permutation(5)[baseline()[0][:17]])
        initial_words.append(np.resize(rng.permutation(5), 17))
    start = time.time()
    iteration = 0
    best = 1e6
    while time.time() - start < seconds and not (ROOT / f'stop_{seed}').exists():
        if iteration < len(initial_words):
            word = initial_words[iteration].copy()
        elif rng.random() < .05:
            word = rng.integers(5, size=17)
        else:
            word = np.array(population[int(rng.integers(min(12, len(population))))][1]).copy()
            for mutation in range(1 if rng.random() < .85 else rng.integers(2, 5)):
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
        if seed in [60, 70] and (np.sum(word == 4) != (2 if seed == 60 else 3) or word[-1] == 4):
            continue
        if any(np.array_equal(word, member[1]) for member in population):
            continue
        result = optimize(word, points, projection, mode='max' if seed >= 70 else 'penalty')
        if not np.isfinite(result.fun):
            continue
        value = float(result.fun)
        population.append((value, word.tolist(), result.x.tolist()))
        population.sort(key=lambda record: record[0])
        population = population[:30]
        if value < best:
            best = value
            residual = tensor(word, result.x)[0] @ projection
            losses = (points @ residual) @ residual
            print(iteration, round(time.time() - start, 2), value, ''.join(map(str, word)), 'mean', losses.mean(), 'max', np.sqrt(losses.max()), flush=True)
            write_submission(*full(word, result.x), name=f'riskbest_{seed}.json')
            (ROOT / f'riskpopulation_{seed}.json').write_text(json.dumps(population))
        if iteration % 100 == 0:
            (ROOT / f'riskpopulation_{seed}.json').write_text(json.dumps(population))
    (ROOT / f'riskpopulation_{seed}.json').write_text(json.dumps(population))
    print('finished', iteration, time.time() - start, flush=True)


if __name__ == '__main__':
    if sys.argv[1] == 'build':
        build()
    else:
        search(float(sys.argv[1]), int(sys.argv[2]))
