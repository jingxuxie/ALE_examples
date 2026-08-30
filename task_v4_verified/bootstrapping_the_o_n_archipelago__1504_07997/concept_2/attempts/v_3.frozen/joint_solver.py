import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import sys
sys.dont_write_bytecode = True
import json
import time
import warnings
from pathlib import Path
import numpy as np
from scipy.linalg import solve
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parent
SOURCE = Path('/srv/home/xuandong/mnt/jingxu/ALE/tasks_v4/bootstrapping_the_o_n_archipelago__1504_07997/concept_2/participant/input/instances.json')
sys.path.insert(0, str(SOURCE.parent.parent / 'baseline'))
import improve
improve.ROOT = ROOT
improve.SOURCE = SOURCE
os.environ['RESULT_DIR'] = 'joint_results'
SQRT2 = np.sqrt(2.)

class Joint:
    def __init__(self, instance):
        self.instance = instance
        self.design = np.array(instance['design'])
        self.target = np.array(instance['target'])
        self.scales = np.array(instance['scales'])
        self.count = self.design.shape[1]
        self.bases = []
        self.observations = []
        for component in range(3):
            matrix = self.design / self.scales[:, component, None]
            target = self.target[:, component] / self.scales[:, component]
            if component == 1:
                target = target * SQRT2
            if component == 0:
                matrix = np.vstack((matrix, np.eye(1, self.count)))
                target = np.r_[target, instance['shared_ope_squared']]
            left, singular, right = np.linalg.svd(matrix, full_matrices=False)
            self.bases.append(right)
            self.observations.append((left.T @ target) / singular)
        self.observed = np.concatenate(self.observations)
        self.offsets = np.cumsum([0] + [len(basis) for basis in self.bases])
        self.optimizer = improve.Optimizer(instance)
        saved = improve.load_seed(instance['id'])
        if saved:
            self.optimizer.evaluate([atom['index'] for atom in saved['atoms']], np.array([atom['ope'] for atom in saved['atoms']]))
        self.rng = np.random.default_rng(20260828)

    def dual_matrix(self, dual, weights):
        values = [basis.T @ dual[self.offsets[component]:self.offsets[component + 1]] for component, basis in enumerate(self.bases)]
        if hasattr(self, 'trace_vectors'):
            values[0] += dual[-1]*self.trace_vectors[0]
            values[2] += dual[-1]*self.trace_vectors[1]
        if weights.ndim == 3:
            return weights[:, 0, 0] - values[0], weights[:, 0, 1] - values[1] / SQRT2, weights[:, 1, 1] - values[2]
        return weights - values[0], -values[1] / SQRT2, weights - values[2]

    def sdp(self, weights, minimum=1e-9):
        observed = np.r_[self.observed, self.trace_observed] if hasattr(self, 'trace_vectors') else self.observed
        dual = np.zeros(len(observed))
        started = time.monotonic()
        for barrier in np.geomspace(0.5, minimum, 23):
            for iteration in range(70):
                first, cross, second = self.dual_matrix(dual, weights)
                determinant = first * second - cross * cross
                inv_first = second / determinant
                inv_cross = -cross / determinant
                inv_second = first / determinant
                coordinates = barrier * np.array([inv_first, SQRT2 * inv_cross, inv_second])
                gradient = np.concatenate([basis @ coordinates[component] for component, basis in enumerate(self.bases)])
                if hasattr(self, 'trace_vectors'):
                    gradient = np.r_[gradient, self.trace_vectors[0] @ coordinates[0]+self.trace_vectors[1] @ coordinates[2]]
                gradient -= observed
                metric = [[inv_first**2, SQRT2*inv_first*inv_cross, inv_cross**2],
                          [SQRT2*inv_first*inv_cross, inv_first*inv_second+inv_cross**2, SQRT2*inv_cross*inv_second],
                          [inv_cross**2, SQRT2*inv_cross*inv_second, inv_second**2]]
                hessian = np.block([[barrier * (self.bases[row] * metric[row][column]) @ self.bases[column].T for column in range(3)] for row in range(3)])
                if hasattr(self, 'trace_vectors'):
                    first_trace, second_trace = self.trace_vectors
                    cross_hessian = np.concatenate([barrier*self.bases[component] @ (metric[component][0]*first_trace+metric[component][2]*second_trace) for component in range(3)])
                    trace_hessian = barrier*np.sum(metric[0][0]*first_trace**2+2*metric[0][2]*first_trace*second_trace+metric[2][2]*second_trace**2)
                    hessian = np.block([[hessian, cross_hessian[:, None]], [cross_hessian[None, :], np.array([[trace_hessian]])]])
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    try:
                        step = solve(hessian, -gradient, assume_a='pos')
                    except Exception:
                        step = np.linalg.lstsq(hessian, -gradient, rcond=1e-14)[0]
                decrement = -gradient @ step
                if decrement < 1e-17 or np.max(np.abs(gradient)) < 2e-10:
                    break
                value = -observed @ dual - barrier * np.log(determinant).sum()
                length = 1.
                while length > 1e-12:
                    trial = dual + length * step
                    trial_first, trial_cross, trial_second = self.dual_matrix(trial, weights)
                    trial_det = trial_first*trial_second-trial_cross**2
                    if np.min(trial_first) > 0 and np.min(trial_det) > 0:
                        trial_value = -observed @ trial - barrier * np.log(trial_det).sum()
                        if trial_value < value + 0.01 * length * gradient @ step:
                            break
                    length *= 0.5
                if length <= 1e-12:
                    break
                dual += length * step
            if iteration == 69:
                print('SDP_LIMIT', barrier, np.max(np.abs(gradient)), flush=True)
        first, cross, second = self.dual_matrix(dual, weights)
        determinant = first * second - cross * cross
        matrices = np.empty((self.count, 2, 2))
        matrices[:, 0, 0] = minimum * second / determinant
        matrices[:, 0, 1] = matrices[:, 1, 0] = -minimum * cross / determinant
        matrices[:, 1, 1] = minimum * first / determinant
        print('SDP', self.instance['id'], 'seconds', time.monotonic()-started, 'gradient', np.max(np.abs(gradient)), 'trace', np.trace(matrices, axis1=1, axis2=2).sum(), flush=True)
        return matrices

    def full_fit(self, support, initial, nfev=1000):
        transforms = [basis[:, support] for basis in self.bases]
        initial = np.clip(initial, -3.9, 3.9)
        initial[0, 0] = self.optimizer.shared
        count = len(support)
        def unpack(parameters):
            return np.r_[self.optimizer.shared, parameters].reshape(count, 2)
        def residual(parameters):
            vectors = unpack(parameters)
            products = improve.products(vectors)
            products[:, 1] *= SQRT2
            moments = np.concatenate([matrix @ products[:, component] for component, matrix in enumerate(transforms)]) - self.observed
            trace = np.sum(vectors**2)
            if hasattr(self, 'trace_vectors'):
                return np.r_[moments, self.trace_vectors[0][support] @ products[:, 0]+self.trace_vectors[1][support] @ products[:, 2]-self.trace_observed]
            return np.r_[moments, max(0., trace-self.instance['trace_budget'])]
        def jacobian(parameters):
            vectors = unpack(parameters)
            blocks = []
            for component, matrix in enumerate(transforms):
                block = np.zeros((len(matrix), count, 2))
                if component == 0:
                    block[:, :, 0] = 2*matrix*vectors[:, 0]
                elif component == 1:
                    block[:, :, 0] = SQRT2*matrix*vectors[:, 1]
                    block[:, :, 1] = SQRT2*matrix*vectors[:, 0]
                else:
                    block[:, :, 1] = 2*matrix*vectors[:, 1]
                blocks.append(block.reshape(len(matrix), -1)[:, 1:])
            trace_gradient = 2*vectors.ravel()[1:] if np.sum(vectors**2) > self.instance['trace_budget'] else np.zeros(2*count-1)
            if hasattr(self, 'trace_vectors'):
                trace_gradient = (2*vectors*np.column_stack((self.trace_vectors[0][support], self.trace_vectors[1][support]))).ravel()[1:]
            return np.vstack(blocks + [trace_gradient[None, :]])
        method = 'lm' if len(self.observed)+1 >= 2*count-1 else 'trf'
        solution = least_squares(residual, initial.ravel()[1:], jac=jacobian, method=method, max_nfev=nfev, ftol=1e-12, xtol=1e-12, gtol=1e-12)
        vectors = unpack(solution.x)
        if count <= self.instance['max_atoms']:
            self.optimizer.evaluate(support, vectors)
        return vectors, np.linalg.norm(solution.fun)

    def sparse_fit(self, matrices, cycle):
        eigenvalues, eigenvectors = np.linalg.eigh(matrices)
        vectors = eigenvectors[:, :, 1] * np.sqrt(np.maximum(eigenvalues[:, 1], 0))[:, None]
        vectors *= np.where(vectors[:, 0] < 0, -1., 1.)[:, None]
        magnitude = eigenvalues[:, 1]
        limit = self.instance['max_atoms']
        chosen = [0] + [int(index) for index in np.argsort(-magnitude) if index != 0][:limit-1]
        support = np.array(sorted(chosen))
        print('SUPPORT', cycle, [(int(index), round(float(magnitude[index]), 5)) for index in np.argsort(-magnitude)[:limit+8]], flush=True)
        current = vectors[support].copy()
        current[0, 0] = self.optimizer.shared
        current, cost = self.full_fit(support, current)
        print('FULL_FIT', cycle, cost, flush=True)
        for cutoff in (1e-3, 1e-5, 1e-7, 0):
            error, current, cost = self.optimizer.fit(support, current, cutoff, nfev=1500)
            if self.optimizer.best_error < 1e-8:
                return True
        if cycle % 3 == 0:
            expanded_count = min(max(limit+4, np.sum(magnitude > 1e-4)), 30)
            expanded = np.array(sorted([0] + [int(index) for index in np.argsort(-magnitude) if index != 0][:expanded_count-1]))
            current, cost = self.full_fit(expanded, vectors[expanded], nfev=600)
            while len(expanded) > limit:
                removable = np.argsort(np.sum(current[1:]**2, axis=1))[:4]+1
                proposals = []
                for position in removable:
                    chosen = np.delete(expanded, position)
                    trial, cost = self.full_fit(chosen, np.delete(current, position, axis=0), nfev=300)
                    proposals.append((cost, chosen, trial))
                cost, expanded, current = min(proposals, key=lambda item: item[0])
            print('PRUNED', cycle, cost, expanded, flush=True)
            for cutoff in (1e-4, 1e-7, 0):
                _, current, _ = self.optimizer.fit(expanded, current, cutoff, nfev=1000)
                if self.optimizer.best_error < 1e-8:
                    return True
        return False

    def recover(self, seconds=400):
        if self.optimizer.best_error < 1e-8:
            return self.optimizer.best
        deadline = time.monotonic() + seconds
        weights = np.ones(self.count)
        matrices = None
        for cycle in range(20):
            matrices = self.sdp(weights)
            np.save(ROOT / ('dense_' + self.instance['id'] + '.npy'), matrices)
            if self.sparse_fit(matrices, cycle):
                return self.optimizer.best
            magnitude = np.trace(matrices, axis1=1, axis2=2)
            epsilon = (0.03, 0.01, 0.003, 0.001)[min(cycle // 2, 3)]
            weights = 1 / np.sqrt(magnitude + epsilon)
            weights /= np.mean(weights)
            if time.monotonic() > deadline:
                break
        return self.optimizer.best

if __name__ == '__main__':
    instances = json.loads(SOURCE.read_text())['instances']
    selected = list(map(int, sys.argv[1:])) or list(range(8))
    for index in selected:
        Joint(instances[index]).recover()
