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
import improve

def recover(variant):
    if variant < 2:
        from dense_refine import recover as dense_recover
        return dense_recover(variant)
    os.environ['RESULT_DIR'] = 'focused_results_' + str(variant)
    instance = json.loads(SOURCE.read_text())['instances'][0]
    with (ROOT / ('focused_' + str(variant) + '.log')).open('w', buffering=1) as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            solver = Joint(instance)
            solver.rng = np.random.default_rng(652994+variant)
            if solver.optimizer.best_error < 1e-8:
                return solver.optimizer.best_error
            deadline = time.monotonic()+float(os.environ.get('FOCUSED_SECONDS', '420'))
            matrices = None
            for cycle in range(1000):
                saved = improve.load_seed(instance['id'])
                support = [atom['index'] for atom in saved['atoms']]
                vectors = np.array([atom['ope'] for atom in saved['atoms']])
                solver.optimizer.evaluate(support, vectors)
                if solver.optimizer.best_error < 1e-8:
                    return solver.optimizer.best_error
                reference = np.zeros((solver.count, 2, 2))
                for index, vector in zip(support, vectors):
                    reference[index] = np.outer(vector, vector)
                if cycle % 10 == 0:
                    matrices = reference.copy()
                else:
                    matrices = 0.7*matrices + 0.3*reference
                eigenvalues, eigenvectors = np.linalg.eigh(matrices)
                epsilon = (0.01, 0.003, 0.001, 0.0003, 0.0001)[min(cycle % 10, 4)]
                power = (0.5, 0.8, 1.2, 1.5)[variant]
                penalty = np.maximum(eigenvalues+epsilon, epsilon)**(-power)
                weights = np.einsum('nij,nj,nkj->nik', eigenvectors, penalty, eigenvectors)
                weights /= np.trace(weights, axis1=1, axis2=2).mean()/2
                weights *= solver.rng.lognormal(0., 0.03+0.02*(cycle//10 % 4), solver.count)[:, None, None]
                if variant >= 2:
                    direction = vectors[0]/np.linalg.norm(vectors[0])
                    perpendicular = np.array([-direction[1], direction[0]])
                    weights[0] += (1000 if variant == 2 else 10000)*np.outer(perpendicular, perpendicular)
                matrices = solver.sdp(weights)
                matrices *= instance['trace_budget'] * 0.97 / np.trace(matrices, axis1=1, axis2=2).sum()
                print('FOCUSED', cycle, solver.optimizer.best_error, flush=True)
                if solver.sparse_fit(matrices, cycle):
                    return solver.optimizer.best_error
                if time.monotonic() > deadline:
                    return solver.optimizer.best_error
            return solver.optimizer.best_error

if __name__ == '__main__':
    selected = list(map(int, sys.argv[1:])) or list(range(4))
    with ProcessPoolExecutor(max_workers=len(selected)) as pool:
        jobs = {pool.submit(recover, variant): variant for variant in selected}
        for job in as_completed(jobs):
            print('FOCUSED_DONE', jobs[job], job.result(), flush=True)
    from collect import collect
    collect()
