import os
import json
import time
import contextlib
import numpy as np
from joint_solver import Joint, ROOT, SOURCE
import improve

def recover(variant=0):
    os.environ['RESULT_DIR'] = 'dense_results_' + str(variant)
    instance = json.loads(SOURCE.read_text())['instances'][0]
    with (ROOT / ('dense_refine_' + str(variant) + '.log')).open('w', buffering=1) as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            solver = Joint(instance)
            solver.rng = np.random.default_rng(672134+variant)
            deadline = time.monotonic()+float(os.environ.get('FOCUSED_SECONDS', '240'))
            matrices = np.load(ROOT / ('dense_' + instance['id'] + '.npy'))
            if variant:
                matrices = solver.sdp(np.ones(solver.count))
            eigenvalues, eigenvectors = np.linalg.eigh(matrices)
            base = eigenvectors[:, :, 1]*np.sqrt(np.maximum(eigenvalues[:, 1], 0))[:, None]
            for attempt in range(100):
                saved = improve.load_seed(instance['id'])
                solver.optimizer.evaluate([atom['index'] for atom in saved['atoms']], np.array([atom['ope'] for atom in saved['atoms']]))
                if solver.optimizer.best_error < 1e-8:
                    return solver.optimizer.best_error
                support = np.arange(solver.count)
                vectors = base.copy()+solver.rng.normal(0, 0.01 if attempt % 2 else 0.06, base.shape)
                if attempt % 3 == 1:
                    vectors = solver.rng.normal(0, 0.02, base.shape)
                    for atom in saved['atoms']:
                        vectors[atom['index']] = atom['ope']
                vectors, cost = solver.full_fit(support, vectors, nfev=1500)
                while len(support) > 24:
                    count = max(24, int(len(support)*0.75))
                    keep = np.r_[0, np.argsort(-np.sum(vectors[1:]**2, axis=1))[:count-1]+1]
                    keep = np.sort(keep)
                    support = support[keep]
                    vectors, cost = solver.full_fit(support, vectors[keep], nfev=1200)
                while len(support) > instance['max_atoms']:
                    proposals = []
                    for position in range(1, len(support)):
                        trial_support = np.delete(support, position)
                        trial, trial_cost = solver.full_fit(trial_support, np.delete(vectors, position, axis=0), nfev=600)
                        proposals.append((trial_cost, trial_support, trial))
                    proposals.sort(key=lambda item: item[0])
                    choice = 0 if attempt % 3 else int(solver.rng.integers(min(3, len(proposals))))
                    cost, support, vectors = proposals[choice]
                for cutoff in (1e-3, 1e-5, 1e-7, 0):
                    _, vectors, _ = solver.optimizer.fit(support, vectors, cutoff, nfev=1500)
                    if solver.optimizer.best_error < 1e-8:
                        return solver.optimizer.best_error
                print('DENSE', attempt, cost, solver.optimizer.best_error, flush=True)
                if time.monotonic() > deadline:
                    return solver.optimizer.best_error
            return solver.optimizer.best_error
