import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import json
import time
from pathlib import Path
import numpy as np
from scipy.linalg import expm
from scipy.special import expit
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parents[1] / 'participant' / 'input'
NAMES = ['X0', 'X1', 'Y0', 'Y1', 'V']


def baseline():
    word, coeff = [], []
    for repeat in range(4):
        for index, component in enumerate([0, 1, 2, 3, 4, 3, 2, 1, 0]):
            value = .25 if index == 4 else .125
            if word and word[-1] == component:
                coeff[-1] += value
            else:
                word.append(component)
                coeff.append(value)
    return np.array(word), np.array(coeff)


def load_instances():
    data = json.loads((INPUT / 'training_instances.json').read_text())
    result = []
    for record in data['instances']:
        size = np.prod(record['shape'])
        matrices = np.zeros((5, size, size), dtype=complex)
        for component, source, target, amplitude, phase in record['bonds']:
            value = amplitude * np.exp(1j * phase)
            matrices[NAMES.index(component), source, target] = value
            matrices[NAMES.index(component), target, source] = value.conjugate()
        matrices[4] = np.diag(-np.array(record['site_potential']))
        result.append((record['id'], record['family'], matrices))
    return result


def stage_exp(matrices, component, value):
    matrix = matrices[component]
    if component == 4:
        return np.diag(np.exp(value * matrix.diagonal().real))
    amplitude = np.sqrt(np.sum(np.abs(matrix) ** 2, axis=0))
    return np.diag(np.cosh(value * amplitude)) + matrix * (np.sinh(value * amplitude) / amplitude)[None, :]


def evaluate(word, coefficients, instances=None, verbose=False):
    if instances is None:
        instances = load_instances()
    baseline_word, baseline_coeff = baseline()
    errors = []
    for identity, family, matrices in instances:
        eigval, eigvec = np.linalg.eigh(matrices.sum(axis=0))
        instance_errors = []
        for step in [.4, .6, .8, 1.]:
            products = []
            decompositions = []
            for current_word, current_coeff in [(word, coefficients), (baseline_word, baseline_coeff)]:
                left = np.eye(len(eigval), dtype=complex)
                for index in range(17):
                    left = left @ stage_exp(matrices, current_word[index], step * current_coeff[index] * (.5 if index == 16 else 1.))
                vectors, singular, _ = np.linalg.svd(left)
                products.append(left @ left.conj().T)
                decompositions.append((vectors, np.log(singular) * 2))
            for repetitions in [1, 4]:
                exact_prop = (eigvec * np.exp(repetitions * step * eigval)) @ eigvec.conj().T
                exact_green = (eigvec * expit(-repetitions * step * eigval)) @ eigvec.conj().T
                pair = []
                for product, (vectors, logvalues) in zip(products, decompositions):
                    propagator = np.linalg.matrix_power(product, repetitions)
                    green = (vectors * expit(-repetitions * logvalues)) @ vectors.conj().T
                    pair.append([np.linalg.norm(propagator - exact_prop) / np.linalg.norm(exact_prop), np.linalg.norm(green - exact_green) / np.linalg.norm(exact_green)])
                instance_errors.extend(np.maximum(pair[0], 1e-14) / np.maximum(pair[1], 1e-14))
        errors.append(instance_errors)
    ratios = np.array(errors)
    scores = 1 / np.sqrt(np.mean(ratios.reshape(8, -1) ** 2, axis=1))
    summary = {'core': float(np.exp(np.mean(np.log(scores)))), 'worst': float(scores.min()), 'max': float(ratios.max()), 'families': scores.tolist()}
    if verbose:
        print(json.dumps(summary), flush=True)
        worst = np.unravel_index(np.argmax(ratios), ratios.shape)
        print('worst point', instances[worst[0]][0], worst[1], ratios[worst], flush=True)
    return summary, ratios


def write_submission(word, coefficients, name='submission.json'):
    artifact = {'schema_version': 1, 'stages': [{'component': NAMES[int(component)], 'coefficient': float(value)} for component, value in zip(word, coefficients)]}
    (ROOT / name).write_text(json.dumps(artifact, indent=2) + '\n')


def build_gram():
    start = time.time()
    instances = load_instances()
    baseline_word, baseline_coeff = baseline()
    grams = []
    for identity, family, matrices in instances:
        eigenvalues, eigenvectors = np.linalg.eigh(matrices.sum(axis=0))
        centered = matrices.copy()
        centered[4] -= np.eye(len(eigenvalues)) * np.trace(centered[4]) / len(eigenvalues)
        triples = np.array([first @ second @ third for first in centered for second in centered for third in centered])
        triples = (triples + triples.conj().transpose(0, 2, 1)) / 2
        transformed = eigenvectors.conj().T @ triples @ eigenvectors
        instance_grams = []
        for step in [.4, .6, .8, 1.]:
            left = np.eye(len(eigenvalues), dtype=complex)
            for index in range(17):
                left = left @ stage_exp(matrices, baseline_word[index], step * baseline_coeff[index] * (.5 if index == 16 else 1.))
            vectors, singular, _ = np.linalg.svd(left)
            product = left @ left.conj().T
            for repetitions in [1, 4]:
                times = repetitions * step
                differences = times * (eigenvalues[:, None] - eigenvalues[None, :])
                for observable in [0, 1]:
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
                    weighted = (transformed * (repetitions * step ** 3 * divided)[None]).reshape(125, -1) / denominator
                    instance_grams.append((weighted.conj() @ weighted.T).real)
        grams.append(instance_grams)
        print('gram', identity, round(time.time() - start, 2), flush=True)
    np.savez(ROOT / 'gram.npz', points=np.array(grams))


if __name__ == '__main__':
    import sys
    if sys.argv[1] == 'gram':
        build_gram()
    elif sys.argv[1] == 'baseline':
        write_submission(*baseline())
        evaluate(*baseline(), verbose=True)
    elif sys.argv[1] == 'evaluate':
        artifact = json.loads(Path(sys.argv[2]).read_text())
        evaluate(np.array([NAMES.index(stage['component']) for stage in artifact['stages']]), np.array([stage['coefficient'] for stage in artifact['stages']]), verbose=True)
