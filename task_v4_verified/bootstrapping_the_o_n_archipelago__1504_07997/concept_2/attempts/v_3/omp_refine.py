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
from joint_solver import Joint, ROOT, SOURCE, SQRT2
import improve

def recover(variant):
    os.environ['RESULT_DIR'] = 'omp_results_' + str(variant)
    instance = json.loads(SOURCE.read_text())['instances'][0]
    with (ROOT / ('omp_' + str(variant) + '.log')).open('w', buffering=1) as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            solver = Joint(instance)
            if solver.optimizer.best_error < 1e-8:
                return solver.optimizer.best_error
            rng = np.random.default_rng(712381+variant)
            cutoff = (0., 1e-4, 1e-3)[variant]
            if cutoff:
                for component in range(3):
                    matrix = solver.design / solver.scales[:, component, None]
                    if component == 0:
                        matrix = np.vstack((matrix, np.eye(1, solver.count)))
                    singular = np.linalg.svd(matrix, compute_uv=False)
                    weighting = singular / np.maximum(singular, singular[0]*cutoff)
                    solver.bases[component] *= weighting[:, None]
                    solver.observations[component] *= weighting
                solver.observed = np.concatenate(solver.observations)
            spins = np.array([candidate['spin'] for candidate in instance['candidates']])
            dimensions = np.array([candidate['dimension'] for candidate in instance['candidates']])
            deadline = time.monotonic()+600
            visited = set()
            stagnation = 0
            support = None
            for iteration in range(1000):
                if support is None or iteration % 8 == 0:
                    saved = improve.load_seed(instance['id'])
                    support = np.array([atom['index'] for atom in saved['atoms']])
                    current = np.array([atom['ope'] for atom in saved['atoms']])
                    solver.optimizer.evaluate(support, current)
                    current, cost = solver.full_fit(support, current, nfev=2000)
                if solver.optimizer.best_error < 1e-8:
                    return solver.optimizer.best_error
                coefficients = improve.products(current)
                coefficients[:, 1] *= SQRT2
                residuals = [basis[:, support] @ coefficients[:, component] - solver.observations[component] for component, basis in enumerate(solver.bases)]
                gradients = np.column_stack([basis.T @ residuals[component] for component, basis in enumerate(solver.bases)])
                gradient_matrices = np.empty((solver.count, 2, 2))
                gradient_matrices[:, 0, 0] = gradients[:, 0]
                gradient_matrices[:, 0, 1] = gradient_matrices[:, 1, 0] = gradients[:, 1]/SQRT2
                gradient_matrices[:, 1, 1] = gradients[:, 2]
                eigenvalues, eigenvectors = np.linalg.eigh(gradient_matrices)
                directions = eigenvectors[:, :, 0]
                unit_products = improve.products(directions)
                unit_products[:, 1] *= SQRT2
                norms = sum(np.sum(basis**2, axis=0)*unit_products[:, component]**2 for component, basis in enumerate(solver.bases))
                scores = np.minimum(eigenvalues[:, 0], 0.)**2 / np.maximum(norms, 1e-20)
                scores[support] = -1
                candidates = [int(candidate) for candidate in np.argsort(-scores) if candidate not in support][:(solver.count if variant == 2 else 10)]
                for position in rng.choice(np.arange(1, len(support)), size=4, replace=False):
                    nearby = np.where((spins == spins[support[position]]) & ~np.isin(np.arange(solver.count), support))[0]
                    nearby = nearby[np.argsort(np.abs(dimensions[nearby]-dimensions[support[position]]))[:5]]
                    if len(nearby):
                        candidates.append(int(rng.choice(nearby)))
                proposals = []
                for candidate in dict.fromkeys(candidates):
                    mass = np.clip(-eigenvalues[candidate, 0]/max(norms[candidate], 1e-20), 1e-5, 1.)
                    expanded = np.r_[support, candidate]
                    initial = np.vstack((current, np.sqrt(mass)*directions[candidate]))
                    order = np.argsort(expanded)
                    expanded = expanded[order]
                    fitted, expanded_cost = solver.full_fit(expanded, initial[order], nfev=600)
                    for position in range(1, len(expanded)):
                        if expanded[position] == candidate:
                            continue
                        trial_support = np.delete(expanded, position)
                        key = tuple(trial_support)
                        if key in visited:
                            continue
                        visited.add(key)
                        trial, trial_cost = solver.full_fit(trial_support, np.delete(fitted, position, axis=0), nfev=350)
                        proposals.append((trial_cost, trial_support, trial))
                proposals.sort(key=lambda proposal: proposal[0])
                for trial_cost, trial_support, trial in proposals[:4]:
                    solver.optimizer.fit(trial_support, trial, cutoff=0, nfev=1800)
                print('OMP', iteration, 'cost', cost, 'trial', proposals[0][0] if proposals else None, 'best', solver.optimizer.best_error, 'visited', len(visited), flush=True)
                if solver.optimizer.best_error < 1e-8 or time.monotonic() > deadline:
                    return solver.optimizer.best_error
                if proposals:
                    choice = 0 if stagnation < 2 else int(rng.integers(min(6, len(proposals))))
                    next_cost, next_support, next_vectors = proposals[choice]
                    stagnation = stagnation+1 if next_cost >= cost*(1-1e-6) else 0
                    cost, support, current = next_cost, next_support, next_vectors
                else:
                    support = None
            return solver.optimizer.best_error

if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=3) as pool:
        jobs = {pool.submit(recover, variant): variant for variant in range(3)}
        for job in as_completed(jobs):
            print('OMP_DONE', jobs[job], job.result(), flush=True)
    from collect import collect
    collect()
