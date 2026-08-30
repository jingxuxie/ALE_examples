import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['JAX_ENABLE_X64'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import sys
import time
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
import jax
import jax.numpy as jnp
from oracle import DeterminantCC
from api import CONSTRAINTS, artifact, endpoint_failures

oracle = DeterminantCC()
energies = CONSTRAINTS['orbital_energies']
rows, columns = np.triu_indices(15)
directions = np.zeros((120,15,15))
for index, (row,column) in enumerate(zip(rows,columns)):
    directions[index,row,column] = 1
    directions[index,column,row] = 1
ham_zero = oracle.hamiltonian(energies,np.zeros((15,15)))[0]
ham_directions = np.array([oracle.hamiltonian(energies,direction)[0]-ham_zero for direction in directions])
generators = jnp.array(oracle.generators)
targets = jnp.array(oracle.targets)
single_targets = jnp.array(oracle.single_targets)
reference = jnp.array(oracle.ref)
identity = jnp.eye(20)
operators = jnp.array(oracle.one)
double_tangent = np.einsum('aij,bj->abi',oracle.singles,oracle.singles@oracle.ref)
double_tangent = jnp.array(double_tangent)
ham_base = jnp.array(ham_zero)
ham_basis = jnp.array(ham_directions)
pair_basis = jnp.array(directions)

def evaluate(variables):
    coefficients = variables[:120]
    amplitudes = variables[120:138]
    multipliers = variables[138:156]
    hamiltonian = ham_base + jnp.einsum('a,aij->ij',coefficients,ham_basis)
    cluster = jnp.einsum('a,aij->ij',amplitudes,generators)
    square = cluster@cluster
    cube = square@cluster
    positive = identity+cluster+square/2+cube/6
    negative = identity-cluster+square/2-cube/6
    transformed = negative@hamiltonian@positive
    column = transformed[:,0]
    jacobian = transformed[targets[:,None],targets[None,:]]-jnp.einsum('kij,j->ik',generators,column)[targets]
    residual = column[targets]
    gradient = transformed[0,targets]
    lambda_residual = gradient+jacobian.T@multipliers
    right = positive[:,0]
    left = (reference.at[targets].set(multipliers))@negative
    density = jnp.einsum('i,pqij,j->pq',left,operators,right)
    occupations = jnp.linalg.eigvalsh((density+density.T)/2)
    exact_energies,exact_vectors = jnp.linalg.eigh(hamiltonian)
    overlap = (exact_vectors[:,0]@right)**2/(right@right)
    tangent = hamiltonian[single_targets[:,None],single_targets[None,:]]-hamiltonian[0,0]*jnp.eye(9)
    curvature = jnp.einsum('abi,i->ab',double_tangent,hamiltonian[:,0])
    hf_real = jnp.linalg.eigvalsh(2*(tangent+curvature))[0]
    hf_imaginary = jnp.linalg.eigvalsh(2*(tangent-curvature))[0]
    singular_values = jnp.linalg.svd(jacobian,compute_uv=False)
    pair_matrix = jnp.einsum('a,aij->ij',coefficients,pair_basis)
    energy_difference = column[0]-exact_energies[0]
    dad_square = jnp.sum((density-density.T)**2)/3
    inequalities = jnp.array([
        (0.000065-energy_difference)*1000,
        (0.000065+energy_difference)*1000,
        (overlap-0.9993)*1000,
        exact_vectors[0,0]**2-0.46,
        exact_energies[1]-exact_energies[0]-0.115,
        hf_real-0.065,
        hf_imaginary-0.065,
        85-singular_values[0]/singular_values[-1],
        1.46**2-jnp.sum(multipliers**2),
        1.23**2-jnp.sum(amplitudes**2),
        (0.00065**2-dad_square)*1e6,
        6.97**2-jnp.sum(pair_matrix**2),
        jnp.min(jnp.linalg.eigvals(jacobian).real)-0.07,
        -occupations[0]-0.035,
    ])
    objective = 0.0001*jnp.sum(pair_matrix**2)+0.001*(jnp.sum(amplitudes**2)+jnp.sum(multipliers**2))
    return jnp.concatenate((jnp.array([objective]),residual,lambda_residual,inequalities))

compiled_value = jax.jit(evaluate)
compiled_jacobian = jax.jit(jax.jacrev(evaluate))

class Evaluator:
    def __init__(self):
        self.current = None
        self.values = None
        self.derivatives = None
    def update(self,variables):
        if self.current is None or not np.array_equal(self.current,variables):
            self.current = variables.copy()
            self.values = np.asarray(compiled_value(variables))
            self.derivatives = None
    def value(self,variables):
        self.update(variables)
        return self.values
    def jacobian(self,variables):
        self.update(variables)
        if self.derivatives is None:
            self.derivatives = np.asarray(compiled_jacobian(variables))
        return self.derivatives

def initial_state(rng,scale):
    matrix = rng.normal(size=(15,15))*scale
    matrix = (matrix+matrix.T)/np.sqrt(2)
    hamiltonian = oracle.hamiltonian(energies,matrix)[0]
    result = oracle.solve(hamiltonian)
    if not result.converged:
        return initial_state(rng,scale*.9)
    multipliers,_,_ = oracle.lambda_state(result)
    return np.concatenate((matrix[rows,columns],result.amplitudes,multipliers))

def save(variables,name):
    matrix = np.einsum('a,aij->ij',variables[:120],directions)
    result = oracle.solve(oracle.hamiltonian(energies,matrix)[0],variables[120:138],tolerance=2e-12)
    diagnostics = oracle.diagnostics(oracle.hamiltonian(energies,matrix)[0],result)
    diagnostics['failures'] = endpoint_failures(diagnostics)
    Path(name+'.json').write_text(json.dumps(artifact(matrix,result.amplitudes),indent=2))
    Path(name+'.diagnostics.json').write_text(json.dumps(diagnostics,indent=2))
    np.save(name+'.npy',variables)
    return diagnostics

def run(seed,seconds):
    rng = np.random.default_rng(seed)
    began = time.time()
    best = 0
    attempt = 0
    evaluator = Evaluator()
    if len(sys.argv)>3:
        start_state = np.load(sys.argv[3])
    else:
        start_state = None
    while time.time()-began < seconds:
        variables = initial_state(rng,float(rng.uniform(.12,.4))) if start_state is None else start_state
        start_state = None
        iteration = 0
        def callback(current):
            nonlocal iteration,best
            iteration += 1
            values = evaluator.value(current)
            if iteration%25==0:
                print(json.dumps({'seed':seed,'attempt':attempt,'iteration':iteration,'seconds':time.time()-began,'objective':float(values[0]),'equality':float(np.max(np.abs(values[1:37]))),'inequality':float(np.min(values[37:]))}),flush=True)
                np.save('latest_'+str(seed)+'.npy',current)
            if np.max(np.abs(values[1:37])) < 1e-7 and np.min(values[37:]) > -1e-6:
                diagnostics = save(current,'candidate_'+str(seed))
                if not diagnostics['failures']:
                    best = diagnostics['occupation_violation']
                    print('SAVED',seed,best,diagnostics['rdm_dad'],flush=True)
            if time.time()-began>seconds:
                raise TimeoutError()
        try:
            answer = minimize(lambda current:evaluator.value(current)[0],variables,
                jac=lambda current:evaluator.jacobian(current)[0],method='SLSQP',
                bounds=[(-1.498,1.498)]*120+[(-1.25,1.25)]*18+[(-1.5,1.5)]*18,
                constraints=[{'type':'eq','fun':lambda current:evaluator.value(current)[1:37],
                              'jac':lambda current:evaluator.jacobian(current)[1:37]},
                             {'type':'ineq','fun':lambda current:evaluator.value(current)[37:],
                              'jac':lambda current:evaluator.jacobian(current)[37:]}],
                callback=callback,options={'maxiter':650,'ftol':1e-11,'disp':False})
            print('END',seed,attempt,answer.success,answer.message,answer.fun,flush=True)
            np.save('last_'+str(seed)+'.npy',answer.x)
            if np.max(np.abs(evaluator.value(answer.x)[1:37]))<1e-6:
                save(answer.x,'end_'+str(seed))
        except TimeoutError:
            break
        attempt+=1

if __name__ == '__main__':
    run(int(sys.argv[1]) if len(sys.argv)>1 else 10,float(sys.argv[2]) if len(sys.argv)>2 else 900)
