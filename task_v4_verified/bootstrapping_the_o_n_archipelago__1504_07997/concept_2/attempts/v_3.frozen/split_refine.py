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
os.environ['RESULT_DIR'] = 'split_results'

def recover(index):
    instance = json.loads(SOURCE.read_text())['instances'][index]
    with (ROOT / ('split_' + str(index) + '.log')).open('w', buffering=1) as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            solver = Joint(instance)
            if solver.optimizer.best_error < 1e-8:
                return solver.optimizer.best_error
            deadline = time.monotonic()+240
            spins = np.array([candidate['spin'] for candidate in instance['candidates']])
            dimensions = np.array([candidate['dimension'] for candidate in instance['candidates']])
            column_scales = np.array([candidate['column_scale'] for candidate in instance['candidates']])
            sources = [solver.sdp(np.ones(solver.count)), np.load(ROOT / ('dense_' + instance['id'] + '.npy'))]
            for attempt in range(500):
                matrices = sources[attempt % len(sources)].copy()
                matrices *= instance['trace_budget'] * 0.97 / np.trace(matrices, axis1=1, axis2=2).sum()
                eigenvalues, eigenvectors = np.linalg.eigh(matrices)
                threshold = (1e-5, 1e-4, 1e-3, 1e-2)[attempt % 4]
                primary = [int(position) for position in np.argsort(-eigenvalues[:, 1]) if eigenvalues[position, 1] > threshold][:26]
                if 0 not in primary:
                    primary.append(0)
                chosen = primary.copy()
                vectors = [eigenvectors[position, :, 1]*np.sqrt(max(eigenvalues[position, 1], 0.)) for position in chosen]
                for position in np.argsort(-eigenvalues[:, 0]):
                    if eigenvalues[position, 0] < threshold or len(chosen) >= 29:
                        break
                    candidates = np.where((spins == spins[position]) & (np.arange(solver.count) != 0))[0]
                    candidates = candidates[~np.isin(candidates, chosen)]
                    if not len(candidates):
                        continue
                    distances = np.abs(dimensions[candidates]-dimensions[position])
                    nearby = candidates[np.argsort(distances)[:(2 if attempt < 10 else 5)]]
                    selected = int(nearby[0] if attempt < 2 else solver.rng.choice(nearby))
                    chosen.append(selected)
                    vector = eigenvectors[position, :, 0]*np.sqrt(eigenvalues[position, 0]*column_scales[selected]/column_scales[position])
                    vectors.append(vector)
                while len(chosen) < instance['max_atoms']:
                    available = np.array([position for position in range(1, solver.count) if position not in chosen])
                    selected = int(solver.rng.choice(available))
                    chosen.append(selected)
                    vectors.append(solver.rng.normal(0, 0.005, 2))
                order = np.argsort(chosen)
                support = np.array(chosen)[order]
                current = np.array(vectors)[order]
                current, cost = solver.full_fit(support, current, nfev=1500)
                while len(support) > instance['max_atoms']:
                    proposals = []
                    for position in np.argsort(np.sum(current[1:]**2, axis=1))[:4]+1:
                        trial_support = np.delete(support, position)
                        trial, cost = solver.full_fit(trial_support, np.delete(current, position, axis=0), nfev=500)
                        proposals.append((cost, trial_support, trial))
                    cost, support, current = min(proposals, key=lambda proposal: proposal[0])
                print('SPLIT', attempt, cost, support, flush=True)
                for cutoff in (1e-4, 1e-6, 0):
                    _, current, _ = solver.optimizer.fit(support, current, cutoff, nfev=1800)
                    if solver.optimizer.best_error < 1e-8:
                        return solver.optimizer.best_error
                if time.monotonic() > deadline:
                    return solver.optimizer.best_error
            return solver.optimizer.best_error

if __name__ == '__main__':
    selected = list(map(int, sys.argv[1:])) or [0, 1, 4, 5, 6]
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(recover, index): index for index in selected}
        for job in as_completed(jobs):
            print('SPLIT_DONE', jobs[job], job.result(), flush=True)
    from collect import collect
    collect()
