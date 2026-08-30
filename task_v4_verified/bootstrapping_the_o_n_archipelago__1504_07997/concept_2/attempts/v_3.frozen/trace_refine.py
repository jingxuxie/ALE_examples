import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import sys
sys.dont_write_bytecode = True
import json
import time
import numpy as np
from joint_solver import Joint, ROOT, SOURCE
import improve
os.environ['RESULT_DIR'] = 'trace_results'

instance = json.loads(SOURCE.read_text())['instances'][0]
solver = Joint(instance)
if solver.optimizer.best_error < 1e-8:
    raise SystemExit(0)
trace_target = instance['trace_budget']/1.03
projections = [solver.bases[component] @ np.ones(solver.count) for component in (0, 2)]
trace_vectors = [np.ones(solver.count)-solver.bases[component].T @ projections[position] for position, component in enumerate((0, 2))]
normalization = np.sqrt(sum(vector @ vector for vector in trace_vectors))
solver.trace_vectors = [vector/normalization for vector in trace_vectors]
solver.trace_observed = (trace_target-projections[0] @ solver.observations[0]-projections[1] @ solver.observations[2])/normalization
print('TRACE', trace_target, normalization, solver.trace_observed, flush=True)
weights = np.ones(solver.count)
deadline = time.monotonic()+360
for cycle in range(300):
    if cycle % 10 == 0:
        weights = np.ones(solver.count)*solver.rng.lognormal(0., 0.01, solver.count)
    matrices = solver.sdp(weights)
    matrices *= trace_target/np.trace(matrices, axis1=1, axis2=2).sum()
    print('TRACE_CYCLE', cycle, flush=True)
    if solver.sparse_fit(matrices, cycle):
        break
    eigenvalues, eigenvectors = np.linalg.eigh(matrices)
    epsilon = (0.03, 0.01, 0.003, 0.001)[min(cycle % 10, 3)]
    penalty = np.maximum(eigenvalues+epsilon, epsilon)**(-0.75)
    weights = np.einsum('nij,nj,nkj->nik', eigenvectors, penalty, eigenvectors)
    weights /= np.trace(weights, axis1=1, axis2=2).mean()/2
    if cycle % 10 >= 5:
        saved = improve.load_seed(instance['id'])
        matrices = np.zeros_like(matrices)
        for atom in saved['atoms']:
            vector = np.array(atom['ope'])
            matrices[atom['index']] = np.outer(vector, vector)
        eigenvalues, eigenvectors = np.linalg.eigh(matrices)
        penalty = np.maximum(eigenvalues+epsilon, epsilon)**(-0.75)
        weights = np.einsum('nij,nj,nkj->nik', eigenvectors, penalty, eigenvectors)
        weights /= np.trace(weights, axis1=1, axis2=2).mean()/2
        weights *= solver.rng.lognormal(0., 0.05, solver.count)[:, None, None]
    if time.monotonic() > deadline:
        break
from collect import collect
collect()
