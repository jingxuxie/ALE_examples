import argparse
import json
import os
import time
from pathlib import Path

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent.parent / 'participant' / 'input' / 'instances.json'


def products(vectors):
    return np.column_stack((vectors[:, 0] ** 2, vectors[:, 0] * vectors[:, 1], vectors[:, 1] ** 2))


class Optimizer:
    def __init__(self, instance):
        self.instance = instance
        self.design = np.array(instance['design'])
        self.target = np.array(instance['target'])
        self.scales = np.array(instance['scales'])
        self.shared = np.sqrt(instance['shared_ope_squared'])
        self.best_error = np.inf
        self.best = None
        self.path = ROOT / os.environ.get('RESULT_DIR', 'improved') / (instance['id'] + '.json')
        self.path.parent.mkdir(exist_ok=True)
        self.rng = np.random.default_rng(20260828)

    def evaluate(self, support, vectors):
        error = np.max(np.abs((self.design[:, support] @ products(vectors) - self.target) / self.scales))
        valid = np.sum(vectors ** 2) <= self.instance['trace_budget'] + 1e-10 and np.max(np.abs(vectors)) <= 4
        if valid and error < self.best_error:
            self.best_error = error
            self.best = {'id': self.instance['id'], 'atoms': [{'index': int(index), 'ope': vector.tolist()} for index, vector in zip(support, vectors)]}
            self.path.write_text(json.dumps(self.best))
            print('BEST', self.instance['id'], error, 'trace', np.sum(vectors ** 2), 'support', support, flush=True)
        return error

    def fit(self, support, initial, cutoff=1e-5, nfev=800, raw=True):
        initial = np.clip(np.nan_to_num(initial, nan=0.05, posinf=3.99, neginf=-3.99), -3.99, 3.99)
        support = np.array(support, dtype=int)
        matrix = self.design[:, support]
        transforms = []
        observed = []
        for component in range(3):
            scaled = matrix / self.scales[:, component, None]
            if cutoff:
                left, singular, right = np.linalg.svd(scaled, full_matrices=False)
                weight = left.T / np.maximum(singular, singular[0] * cutoff)[:, None]
                transforms.append(weight @ scaled)
                observed.append(weight @ (self.target[:, component] / self.scales[:, component]))
            else:
                transforms.append(scaled)
                observed.append(self.target[:, component] / self.scales[:, component])
        transforms = np.array(transforms)
        observed = np.array(observed)

        def unpack(parameters):
            return np.concatenate(([self.shared], parameters)).reshape(-1, 2)

        def residual(parameters):
            return (np.einsum('crk,kc->cr', transforms, products(unpack(parameters))) - observed).ravel()

        def jacobian(parameters):
            current = unpack(parameters)
            jac = np.zeros((3, transforms.shape[1], len(support), 2))
            jac[0, :, :, 0] = 2 * transforms[0] * current[:, 0]
            jac[1, :, :, 0] = transforms[1] * current[:, 1]
            jac[1, :, :, 1] = transforms[1] * current[:, 0]
            jac[2, :, :, 1] = 2 * transforms[2] * current[:, 1]
            return jac.reshape(3 * transforms.shape[1], -1)[:, 1:]

        solution = least_squares(residual, initial.ravel()[1:], jac=jacobian, method='lm', max_nfev=nfev, ftol=1e-13, xtol=1e-13, gtol=1e-13)
        vectors = unpack(solution.x)
        if not np.isfinite(vectors).all() or np.max(np.abs(vectors)) > 100:
            vectors = initial.copy()
            vectors[0, 0] = self.shared
        error = self.evaluate(support, vectors)
        if raw and cutoff:
            error, vectors, _ = self.fit(support, vectors, cutoff=0, nfev=400, raw=False)
        return error, vectors, np.linalg.norm(solution.fun)

    def improve(self, saved, seconds):
        end = time.monotonic() + seconds
        support = [atom['index'] for atom in saved['atoms']]
        vectors = np.array([atom['ope'] for atom in saved['atoms']])
        self.evaluate(support, vectors)
        for cutoff in (1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9):
            _, vectors, cost = self.fit(support, vectors, cutoff=cutoff, nfev=2000)
            print('CONT', cutoff, cost, flush=True)
            if self.best_error < 1e-8 or time.monotonic() > end:
                return
        spins = np.array([candidate['spin'] for candidate in self.instance['candidates']])
        dimensions = np.array([candidate['dimension'] for candidate in self.instance['candidates']])
        attempts = 0
        while time.monotonic() < end and self.best_error > 1e-8:
            support = np.array([atom['index'] for atom in self.best['atoms']])
            vectors = np.array([atom['ope'] for atom in self.best['atoms']])
            replacements = 1 if attempts % 5 else 2
            for position in self.rng.choice(np.arange(1, len(support)), size=replacements, replace=False):
                candidates = np.where(spins == spins[support[position]])[0]
                candidates = candidates[~np.isin(candidates, support)]
                distances = np.abs(dimensions[candidates] - dimensions[support[position]])
                candidates = candidates[np.argsort(distances)[:(10 if attempts % 4 else len(candidates))]]
                support[position] = self.rng.choice(candidates)
            order = np.argsort(support)
            support = support[order]
            vectors = vectors[order]
            if attempts % 7 == 0:
                vectors[1:] += self.rng.normal(0, 0.1, vectors[1:].shape)
            cutoff = (1e-4, 1e-5, 1e-6, 1e-7)[attempts % 4]
            self.fit(support, vectors, cutoff=cutoff, nfev=500)
            attempts += 1
        print('DONE', self.instance['id'], attempts, self.best_error, flush=True)


def load_seed(identifier):
    sources = list(ROOT.glob('*/' + identifier + '.json'))
    sources += list((ROOT / 'output').glob('champion_work_*/' + identifier + '.json'))
    candidates = []
    for path in sources:
        if path.exists():
            try:
                candidates.append(json.loads(path.read_text()))
            except Exception:
                pass
    for path in (ROOT / 'answer.json', ROOT / 'output' / 'answer.json'):
        try:
            candidates.extend(case for case in json.loads(path.read_text())['cases'] if case['id'] == identifier and case['atoms'])
        except Exception:
            pass
    if candidates:
        instance = next(instance for instance in json.loads(SOURCE.read_text())['instances'] if instance['id'] == identifier)
        design = np.array(instance['design'])
        target = np.array(instance['target'])
        scales = np.array(instance['scales'])
        def error(case):
            support = [atom['index'] for atom in case['atoms']]
            vectors = np.array([atom['ope'] for atom in case['atoms']])
            return np.max(np.abs((design[:, support] @ products(vectors) - target) / scales))
        return min(candidates, key=error)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', type=int, nargs='+', default=list(range(8)))
    parser.add_argument('--seconds', type=float, default=120)
    args = parser.parse_args()
    instances = json.loads(SOURCE.read_text())['instances']
    for index in args.cases:
        instance = instances[index]
        seed = load_seed(instance['id'])
        if seed:
            Optimizer(instance).improve(seed, args.seconds)
        else:
            print('NO SEED', index, flush=True)


if __name__ == '__main__':
    main()
