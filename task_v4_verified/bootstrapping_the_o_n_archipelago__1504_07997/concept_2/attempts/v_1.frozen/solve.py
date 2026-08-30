import json
import os
import sys
import time
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import numpy as np
from scipy.optimize import least_squares, nnls

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent.parent / 'participant' / 'input' / 'instances.json'


def products(vectors):
    return np.column_stack((vectors[:, 0] ** 2, vectors[:, 0] * vectors[:, 1], vectors[:, 1] ** 2))


class Solver:
    def __init__(self, instance):
        self.instance = instance
        self.design = np.asarray(instance['design'])
        self.target = np.asarray(instance['target'])
        self.scales = np.asarray(instance['scales'])
        self.shared = instance['shared_ope_squared']
        self.limit = instance['max_atoms']
        self.best = None
        self.best_error = np.inf
        self.tried = set()

    def evaluate(self, support, vectors):
        error = np.max(np.abs((self.design[:, support] @ products(vectors) - self.target) / self.scales))
        trace = np.sum(vectors ** 2)
        feasible = trace <= self.instance['trace_budget'] + 1e-10 and np.max(np.abs(vectors)) <= 4
        if feasible and error < self.best_error:
            self.best_error = error
            self.best = {'id': self.instance['id'], 'atoms': [{'index': int(index), 'ope': vector.tolist()} for index, vector in zip(support, vectors)]}
            print(self.instance['id'], 'best', error, 'trace', trace, 'support', support, flush=True)
            (ROOT / (self.instance['id'] + '.json')).write_text(json.dumps(self.best) + '\n')
        return error

    def fit(self, support, initial=None):
        support = [0] + sorted(int(index) for index in support if index != 0)
        support = list(dict.fromkeys(support))
        key = tuple(support)
        if key in self.tried and initial is None:
            return np.inf, None
        self.tried.add(key)
        matrix = self.design[:, support]
        coefficients = np.column_stack([np.linalg.lstsq(matrix / self.scales[:, component, None], self.target[:, component] / self.scales[:, component], rcond=1e-14)[0] for component in range(3)])
        vectors = np.zeros((len(support), 2))
        for position, row in enumerate(coefficients):
            eigenvalues, eigenvectors = np.linalg.eigh([[row[0], row[1]], [row[1], row[2]]])
            vectors[position] = eigenvectors[:, -1] * np.sqrt(max(eigenvalues[-1], 1e-10))
            if vectors[position, 0] < 0:
                vectors[position] *= -1
        vectors[0, 0] = np.sqrt(self.shared)
        if initial is not None:
            vectors = initial.copy()
        vectors = np.clip(vectors, -3.99, 3.99)
        shared_first = np.sqrt(self.shared)

        def unpack(parameters):
            return np.concatenate(([shared_first], parameters)).reshape(-1, 2)

        def residual(parameters):
            current = unpack(parameters)
            return ((matrix @ products(current) - self.target) / self.scales).ravel()

        def jacobian(parameters):
            current = unpack(parameters)
            jac = np.zeros((matrix.shape[0], 3, len(support), 2))
            jac[:, 0, :, 0] = 2 * matrix * current[:, 0]
            jac[:, 1, :, 0] = matrix * current[:, 1]
            jac[:, 1, :, 1] = matrix * current[:, 0]
            jac[:, 2, :, 1] = 2 * matrix * current[:, 1]
            return (jac / self.scales[:, :, None, None]).reshape(matrix.shape[0] * 3, -1)[:, 1:]

        optimized = least_squares(residual, vectors.ravel()[1:], jac=jacobian, method='lm', max_nfev=600, ftol=1e-14, xtol=1e-14, gtol=1e-14)
        vectors = unpack(optimized.x)
        error = self.evaluate(support, vectors)
        return error, vectors

    def recover(self):
        for cutoff in (1e-7, 1e-9, 1e-5, 1e-11, 1e-3, 1e-13, 1.0):
            diagonal = []
            for component in (0, 2):
                matrix = self.design / self.scales[:, component, None]
                target = self.target[:, component] / self.scales[:, component]
                if component == 0:
                    target = target - matrix[:, 0] * self.shared
                    matrix = matrix[:, 1:]
                left, singular, right = np.linalg.svd(matrix, full_matrices=False)
                weights = 1 / np.maximum(singular, singular[0] * cutoff)
                transformed = (left.T @ matrix) * weights[:, None]
                observed = (left.T @ target) * weights
                try:
                    values, cost = nnls(transformed, observed, maxiter=10000, atol=1e-14)
                except Exception:
                    from scipy.optimize import lsq_linear
                    values = lsq_linear(transformed, observed, bounds=(0, np.inf), tol=1e-13, max_iter=1000).x
                if component == 0:
                    values = np.concatenate(([self.shared], values))
                diagonal.append(values)
            magnitude = diagonal[0] + diagonal[1]
            support = [0] + [int(index) for index in np.argsort(-magnitude) if index != 0][:self.limit-1]
            print('seed', self.instance['id'], cutoff, [(int(index), round(float(magnitude[index]), 7)) for index in np.argsort(-magnitude)[:self.limit+5]], flush=True)
            self.fit(support)
            if self.best_error < 1e-9:
                return self.best
        return self.best


def main():
    instances = json.loads(INPUT.read_text())['instances']
    selected = set(sys.argv[1:])
    for instance in instances:
        if selected and instance['id'] not in selected:
            continue
        solver = Solver(instance)
        solver.recover()
    cases = []
    for instance in instances:
        path = ROOT / (instance['id'] + '.json')
        if path.exists():
            cases.append(json.loads(path.read_text()))
    (ROOT / 'answer.json').write_text(json.dumps({'cases': cases}, indent=2) + '\n')


if __name__ == '__main__':
    main()
