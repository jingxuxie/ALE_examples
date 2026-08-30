import os
os.environ['JAX_ENABLE_X64'] = 'true'
os.environ['XLA_FLAGS'] = '--xla_cpu_multi_thread_eigen=false intra_op_parallelism_threads=1'
os.environ['JAX_PLATFORM_NAME'] = 'cpu'
import json
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.linalg import eigh
from oracle import DeterminantCC
from api import CONSTRAINTS, artifact, endpoint_failures, check_continuation
import jax
import jax.numpy as jnp

oracle = DeterminantCC()
axes = []
for row in range(15):
    for column in range(row, 15):
        axis = np.zeros((15, 15))
        axis[row, column] = axis[column, row] = 1 if row == column else 1 / np.sqrt(2)
        axes.append(axis)
axes = np.array(axes)
basis = np.array([oracle.hamiltonian(np.zeros(6), axis)[0] for axis in axes])
free = oracle.hamiltonian(CONSTRAINTS['orbital_energies'], np.zeros((15, 15)))[0]
hf_real = np.array([oracle.hf_stability(matrix)[0] for matrix in basis])
hf_imag = np.array([oracle.hf_stability(matrix)[1] for matrix in basis])
hf_free = oracle.hf_stability(free)
generators = jnp.array(oracle.generators)
targets = oracle.targets
one = jnp.array(oracle.one)
reference = oracle.reference
identity = jnp.eye(20)

def calculation(variables):
    coordinates = variables[:120]
    amplitudes = variables[120:]
    hamiltonian = jnp.einsum('k,kij->ij', coordinates, jnp.array(basis)) + jnp.array(free)
    cluster = jnp.einsum('k,kij->ij', amplitudes, generators)
    square = cluster @ cluster / 2
    cube = square @ cluster / 3
    positive = identity + cluster + square + cube
    inverse = identity - cluster + square - cube
    transformed = inverse @ hamiltonian @ positive
    right = positive[:, reference]
    column = transformed[:, reference]
    jacobian = transformed[jnp.ix_(targets, targets)] - jnp.einsum('kij,j->ik', generators, column)[targets]
    multipliers = jnp.linalg.solve(jacobian.T, -transformed[reference, targets])
    left_row = jnp.array(oracle.ref).at[targets].set(multipliers)
    left = left_row @ inverse
    density = jnp.einsum('i,pqij,j->pq', left, one, right)
    occupations = jnp.linalg.eigvalsh((density + density.T) / 2)
    energies, vectors = jnp.linalg.eigh(hamiltonian)
    exact = vectors[:, 0]
    energy_error = column[reference] - energies[0]
    gradient = jnp.einsum('i,kij,j->k', left, jnp.array(basis), right) - jnp.einsum('i,kij,j->k', exact, jnp.array(basis), exact)
    overlap = (exact @ right)**2 / (right @ right)
    real_hessian = jnp.einsum('k,kij->ij', coordinates, jnp.array(hf_real)) + jnp.array(hf_free[0])
    imag_hessian = jnp.einsum('k,kij->ij', coordinates, jnp.array(hf_imag)) + jnp.array(hf_free[1])
    singular = jnp.linalg.svd(jacobian, compute_uv=False)
    dad_square = jnp.sum((density-density.T)**2) / 3
    metrics = jnp.array([
        -occupations[0], occupations[-1]-1, energy_error,
        jnp.linalg.norm(gradient), overlap, exact[reference]**2,
        energies[1]-energies[0], jnp.linalg.eigvalsh(real_hessian)[0],
        jnp.linalg.eigvalsh(imag_hessian)[0], singular[-1],
        singular[0]/singular[-1], jnp.linalg.norm(amplitudes),
        jnp.linalg.norm(multipliers), dad_square, jnp.linalg.norm(coordinates)
    ])
    return metrics, column[targets], density

@jax.jit
def metrics(variables):
    return calculation(variables)[0]

@jax.jit
def outputs(variables):
    values, residual, density = calculation(variables)
    violation = jnp.maximum(values[0], values[1])
    constraints = jnp.array([
        (0.075 - values[3]),
        (values[4] - 0.9992)*100,
        values[5] - 0.46,
        values[6] - 0.12,
        values[7] - 0.075,
        values[8] - 0.075,
        values[9] - 0.04,
        (90 - values[10])/100,
        1.24 - values[11],
        1.49 - values[12],
        (0.00065**2-values[13])*10000,
        (6.95-values[14])/10,
    ])
    return jnp.concatenate((jnp.array([-violation]), residual, jnp.array([values[2]]), constraints))

jacobian_outputs = jax.jit(jax.jacfwd(outputs))

class Cached:
    def __init__(self):
        self.variables = None
        self.values = None
        self.derivatives = None

    def get(self, variables):
        if self.variables is None or not np.array_equal(variables, self.variables):
            self.variables = variables.copy()
            self.values = np.asarray(outputs(variables))
            self.derivatives = np.asarray(jacobian_outputs(variables))
        return self.values, self.derivatives

def solve_seed(variables, number, maxiter=300):
    cached = Cached()
    start = time.time()
    count = [0]
    def callback(current):
        count[0] += 1
        if count[0] % 20 == 0:
            values, derivatives = cached.get(current)
            print('ITER', number, count[0], round(time.time()-start,2), np.asarray(metrics(current)).round(7).tolist(), 'res',max(abs(values[1:20])), 'ineq',min(values[20:]), flush=True)
            np.savez('current.npz', variables=current)
    bounds = [( -1.495*(1 if row==column else np.sqrt(2)), 1.495*(1 if row==column else np.sqrt(2))) for row in range(15) for column in range(row,15)] + [(-1.24,1.24)]*18
    result = minimize(lambda current: cached.get(current)[0][0], variables,
        jac=lambda current: cached.get(current)[1][0], method='SLSQP', bounds=bounds,
        constraints=[{'type':'eq','fun':lambda current:cached.get(current)[0][1:20], 'jac':lambda current:cached.get(current)[1][1:20]},
                     {'type':'ineq','fun':lambda current:cached.get(current)[0][20:], 'jac':lambda current:cached.get(current)[1][20:]}],
        callback=callback, options={'maxiter':maxiter,'ftol':1e-10,'disp':False})
    current = result.x
    values = np.asarray(metrics(current))
    interaction = np.einsum('k,kij->ij',current[:120],axes)
    stationary = oracle.solve(free+np.einsum('k,kij->ij',current[:120],basis), current[120:])
    diagnostics = oracle.diagnostics(free+np.einsum('k,kij->ij',current[:120],basis),stationary)
    record = {'message':str(result.message), 'metrics':values.tolist(), 'diagnostics':diagnostics,'failures':endpoint_failures(diagnostics),'time':time.time()-start}
    Path(f'seed{number}.json').write_text(json.dumps(artifact(interaction,stationary.amplitudes)))
    Path(f'seed{number}.report.json').write_text(json.dumps(record,indent=2))
    np.savez(f'seed{number}.npz',variables=np.r_[current[:120],stationary.amplitudes])
    print('RESULT',number,json.dumps(record),flush=True)
    return result

def main():
    rng = np.random.default_rng(8632)
    candidates = []
    print('COMPILING',flush=True)
    initial = np.r_[rng.normal(0,.15,120),rng.normal(0,.05,18)]
    print(np.asarray(outputs(initial)),flush=True)
    print('JAC',np.asarray(jacobian_outputs(initial)).shape,flush=True)
    started = time.time()
    for trial in range(3000):
        coordinates = rng.normal(0, rng.uniform(.1,.5),120)
        if np.linalg.norm(coordinates)>6.8:continue
        hamiltonian = free+np.einsum('k,kij->ij',coordinates,basis)
        result = oracle.solve(hamiltonian)
        if not result.converged or np.linalg.norm(result.amplitudes)>1.2:continue
        variables = np.r_[coordinates,result.amplitudes]
        values = np.asarray(metrics(variables))
        if values[4]<.99 or values[5]<.45 or min(values[7:9])<.04 or values[10]>100:continue
        score = max(values[:2])
        candidates.append((score, variables, values))
    candidates.sort(key=lambda item:item[0],reverse=True)
    print('RANDOM',len(candidates),'time',time.time()-started,[(row[0], row[2].tolist()) for row in candidates[:8]],flush=True)
    np.savez('random.npz', variables=np.array([row[1] for row in candidates]),metrics=np.array([row[2] for row in candidates]))
    for number,(_,variables,values) in enumerate(candidates[:20]):
        solve_seed(variables, number)

if __name__ == '__main__':
    main()
