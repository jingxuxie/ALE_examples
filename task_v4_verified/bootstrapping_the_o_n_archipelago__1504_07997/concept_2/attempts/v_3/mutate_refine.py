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
    os.environ['RESULT_DIR'] = 'mutate_results_' + str(variant)
    instance = json.loads(SOURCE.read_text())['instances'][0]
    with (ROOT / ('mutate_' + str(variant) + '.log')).open('w', buffering=1) as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            solver = Joint(instance)
            rng = np.random.default_rng(710224+variant)
            deadline = time.monotonic()+420
            scaled = solver.design / np.linalg.norm(solver.design, axis=0)
            distances = np.sum((scaled[:, :, None]-scaled[:, None, :])**2, axis=0)
            spins = np.array([candidate['spin'] for candidate in instance['candidates']])
            dimensions = np.array([candidate['dimension'] for candidate in instance['candidates']])
            beam = []
            visited = set()
            for attempt in range(100000):
                if attempt % 20 == 0:
                    saved = improve.load_seed(instance['id'])
                    support = np.array([atom['index'] for atom in saved['atoms']])
                    vectors = np.array([atom['ope'] for atom in saved['atoms']])
                    solver.optimizer.evaluate(support, vectors)
                    if solver.optimizer.best_error < 1e-8:
                        return solver.optimizer.best_error
                    beam.append((solver.optimizer.best_error, support, vectors))
                    beam.sort(key=lambda item: item[0])
                    beam = beam[:12]
                selected = 0 if attempt % 3 else int(rng.integers(len(beam)))
                _, support, vectors = beam[selected]
                support = support.copy()
                vectors = vectors.copy()
                replacements = 1 if attempt % 3 else (2 if attempt % 9 else 3)
                for position in rng.choice(np.arange(1, len(support)), size=replacements, replace=False):
                    available = np.array([candidate for candidate in range(1, solver.count) if candidate not in support])
                    if attempt % 5 == 0:
                        nearest = available[np.argsort(distances[support[position], available])[:25]]
                    elif attempt % 5 in (1, 2):
                        same = available[spins[available] == spins[support[position]]]
                        nearest = same[np.argsort(np.abs(dimensions[same]-dimensions[support[position]]))[:10]] if len(same) else available
                    else:
                        nearest = available
                    support[position] = rng.choice(nearest)
                order = np.argsort(support)
                support = support[order]
                vectors = vectors[order]
                key = tuple(support)
                if key in visited and attempt % 7:
                    continue
                visited.add(key)
                if attempt % 7 == 0:
                    vectors[1:] += rng.normal(0, 0.08, vectors[1:].shape)
                cutoff = (1e-3, 1e-4, 1e-5, 1e-6, 1e-7)[(attempt+variant) % 5]
                error, vectors, _ = solver.optimizer.fit(support, vectors, cutoff, nfev=500)
                feasible = np.sum(vectors**2) <= instance['trace_budget'] and np.max(np.abs(vectors)) <= 4
                if feasible and error < solver.optimizer.best_error * 4:
                    beam.append((error, support, vectors))
                    beam.sort(key=lambda item: item[0])
                    beam = beam[:12]
                if attempt % 100 == 0:
                    print('MUTATE', attempt, solver.optimizer.best_error, len(visited), flush=True)
                if solver.optimizer.best_error < 1e-8 or time.monotonic() > deadline:
                    return solver.optimizer.best_error
            return solver.optimizer.best_error

if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=2) as pool:
        jobs = {pool.submit(recover, variant): variant for variant in range(2)}
        for job in as_completed(jobs):
            print('MUTATE_DONE', jobs[job], job.result(), flush=True)
    from collect import collect
    collect()
