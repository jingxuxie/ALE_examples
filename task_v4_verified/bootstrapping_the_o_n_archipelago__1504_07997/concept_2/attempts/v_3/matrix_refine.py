import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import sys
sys.dont_write_bytecode = True
import json
import time
import contextlib
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
from joint_solver import Joint, ROOT, SOURCE
os.environ['RESULT_DIR'] = 'matrix_results'

def recover(index):
    instance = json.loads(SOURCE.read_text())['instances'][index]
    with (ROOT / ('matrix_' + str(index) + '.log')).open('w', buffering=1) as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            solver = Joint(instance)
            deadline = time.monotonic() + 300
            if solver.optimizer.best_error < 1e-8:
                return solver.optimizer.best_error
            saved = solver.optimizer.best
            if saved:
                support = np.array([atom['index'] for atom in saved['atoms']])
                vectors = np.array([atom['ope'] for atom in saved['atoms']])
                for cutoff in (0, 1e-4, 1e-6, 0):
                    _, vectors, _ = solver.optimizer.fit(support, vectors, cutoff, nfev=8000)
                    if solver.optimizer.best_error < 1e-8:
                        return solver.optimizer.best_error
            initial = np.load(ROOT / ('dense_' + instance['id'] + '.npy'))
            for restart in range(100):
                if restart % 3 == 1:
                    matrices = np.zeros_like(initial)
                    saved = solver.optimizer.best
                    for atom in saved['atoms']:
                        vector = np.array(atom['ope'])
                        matrices[atom['index']] = np.outer(vector, vector)
                elif restart % 3 == 0:
                    matrices = initial.copy()
                else:
                    weights = np.repeat(np.eye(2)[None], solver.count, axis=0)
                    weights *= solver.rng.lognormal(0., 0.05, solver.count)[:, None, None]
                    matrices = solver.sdp(weights)
                for cycle in range(7):
                    trace = np.trace(matrices, axis1=1, axis2=2).sum()
                    matrices = matrices * (instance['trace_budget'] * 0.97 / trace)
                    eigenvalues, eigenvectors = np.linalg.eigh(matrices)
                    epsilon = (0.1, 0.03, 0.01, 0.003, 0.001, 0.0003, 0.0001)[cycle]
                    power = (0.5, 0.75, 1.0)[restart % 3]
                    penalty = np.maximum(eigenvalues + epsilon, epsilon) ** (-power)
                    weights = np.einsum('nij,nj,nkj->nik', eigenvectors, penalty, eigenvectors)
                    weights /= np.trace(weights, axis1=1, axis2=2).mean() / 2
                    weights *= solver.rng.lognormal(0., 0.01 if restart else 0., solver.count)[:, None, None]
                    matrices = solver.sdp(weights)
                    matrices *= instance['trace_budget'] * 0.97 / np.trace(matrices, axis1=1, axis2=2).sum()
                    print('MATRIX_CYCLE', restart, cycle, flush=True)
                    if solver.sparse_fit(matrices, cycle):
                        return solver.optimizer.best_error
                    if time.monotonic() > deadline:
                        return solver.optimizer.best_error
            return solver.optimizer.best_error

if __name__ == '__main__':
    selected = list(map(int, sys.argv[1:])) or [0, 1, 4, 5, 6]
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(recover, index): index for index in selected}
        for job in as_completed(jobs):
            print('MATRIX_DONE', jobs[job], job.result(), flush=True)
    from collect import collect
    collect()
