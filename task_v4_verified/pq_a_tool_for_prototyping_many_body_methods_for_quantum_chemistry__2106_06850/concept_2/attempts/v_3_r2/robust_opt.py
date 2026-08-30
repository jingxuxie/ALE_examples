import os
os.environ['JAX_ENABLE_X64']='1'
import time
import json
import sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
import jax
import jax.numpy as jnp
import optimize as model
from api import artifact, robust_screen

oracle=model.oracle
source=Path(sys.argv[1])
name=sys.argv[2] if len(sys.argv)>2 else 'robust'
payload=json.loads(source.read_text())
initial_matrix=np.array(payload['pair_matrix'])
initial_amplitudes=jnp.array(payload['amplitudes'])
initial_coefficients=initial_matrix[model.rows,model.columns]
radius=float(sys.argv[3]) if len(sys.argv)>3 else .10
full_constraints=len(sys.argv)>4 and sys.argv[4]=='full'
displacements=np.zeros((241,120))
for index,(row,column) in enumerate(zip(model.rows,model.columns)):
    displacement=.001/(1 if row==column else np.sqrt(2))
    displacements[2*index+1,index]=displacement
    displacements[2*index+2,index]=-displacement
displacements=jnp.array(displacements)

def equations(hamiltonian,amplitudes):
    cluster=jnp.einsum('a,aij->ij',amplitudes,model.generators)
    square=cluster@cluster
    cube=square@cluster
    positive=model.identity+cluster+square/2+cube/6
    negative=model.identity-cluster+square/2-cube/6
    transformed=negative@hamiltonian@positive
    column=transformed[:,0]
    jacobian=transformed[model.targets[:,None],model.targets[None,:]]-jnp.einsum('kij,j->ik',model.generators,column)[model.targets]
    return column[model.targets],jacobian,transformed,positive,negative

def stationary(hamiltonian):
    def step(index,amplitudes):
        residual,jacobian,_,_,_=equations(hamiltonian,amplitudes)
        update=jnp.linalg.solve(jacobian,residual)
        update=update*jnp.minimum(1.,.30/(jnp.linalg.norm(update)+1e-30))
        return amplitudes-update
    amplitudes=jax.lax.stop_gradient(jax.lax.fori_loop(0,15,step,initial_amplitudes))
    residual,jacobian,_,_,_=equations(hamiltonian,amplitudes)
    return amplitudes-jnp.linalg.solve(jax.lax.stop_gradient(jacobian),residual)

def point_metrics(coefficients):
    hamiltonian=model.ham_base+jnp.einsum('a,aij->ij',coefficients,model.ham_basis)
    amplitudes=stationary(hamiltonian)
    residual,jacobian,transformed,positive,negative=equations(hamiltonian,amplitudes)
    multipliers=jnp.linalg.solve(jacobian.T,-transformed[0,model.targets])
    right=positive[:,0]
    left=model.reference.at[model.targets].set(multipliers)@negative
    density=jnp.einsum('i,pqij,j->pq',left,model.operators,right)
    occupations=jnp.linalg.eigvalsh((density+density.T)/2)
    exact_energies,exact_vectors=jnp.linalg.eigh(hamiltonian)
    overlap=(exact_vectors[:,0]@right)**2/(right@right)
    tangent=hamiltonian[model.single_targets[:,None],model.single_targets[None,:]]-hamiltonian[0,0]*jnp.eye(9)
    curvature=jnp.einsum('abi,i->ab',model.double_tangent,hamiltonian[:,0])
    hf_real=jnp.linalg.eigvalsh(2*(tangent+curvature))[0]
    hf_imaginary=jnp.linalg.eigvalsh(2*(tangent-curvature))[0]
    singular_values=jnp.linalg.svd(jacobian,compute_uv=False)
    pair_matrix=jnp.einsum('a,aij->ij',coefficients,model.pair_basis)
    energy_error=jnp.abs(transformed[0,0]-exact_energies[0])
    dad_square=jnp.sum((density-density.T)**2)/3
    return jnp.array([
        (.000095-energy_error)*1000,
        (overlap-.9991)*1000,
        exact_vectors[0,0]**2-.455,
        exact_energies[1]-exact_energies[0]-.105,
        hf_real-.06,
        hf_imaginary-.06,
        95-singular_values[0]/singular_values[-1],
        1.49**2-jnp.sum(multipliers**2),
        1.245**2-jnp.sum(amplitudes**2),
        (.00095**2-dad_square)*1e6,
        6.99**2-jnp.sum(pair_matrix**2),
        jnp.min(jnp.linalg.eigvals(jacobian).real)-.055,
        (-occupations[0]-.023)*10,
    ])

def evaluate(coefficients):
    point_values=jax.vmap(point_metrics)(coefficients[None,:]+displacements)
    worst=point_values.reshape(-1) if full_constraints else jnp.min(point_values,axis=0)
    objective=.0001*jnp.sum(coefficients**2)
    return jnp.concatenate((jnp.array([objective]),worst))

values_compiled=jax.jit(evaluate)
if full_constraints:
    def derivatives(coefficients):
        point_derivatives=jax.vmap(jax.jacrev(point_metrics))(coefficients[None,:]+displacements)
        return jnp.concatenate((.0002*coefficients[None,:],point_derivatives.reshape(-1,120)),axis=0)
    jacobian_compiled=jax.jit(derivatives)
else:
    jacobian_compiled=jax.jit(jax.jacrev(evaluate))

def summary(values):
    return np.concatenate((values[:1],values[1:].reshape(-1,13).min(axis=0))) if full_constraints else values

class Evaluator:
    def __init__(self):
        self.current=None
        self.values=None
        self.derivatives=None
    def value(self,current):
        if self.current is None or not np.array_equal(current,self.current):
            self.current=current.copy()
            self.values=np.array(values_compiled(current))
            self.derivatives=None
        return self.values
    def jacobian(self,current):
        self.value(current)
        if self.derivatives is None:
            self.derivatives=np.array(jacobian_compiled(current))
        return self.derivatives

def save(coefficients,suffix):
    matrix=np.einsum('a,aij->ij',coefficients,model.directions)
    result=oracle.solve(oracle.hamiltonian(model.energies,matrix)[0],np.array(initial_amplitudes),tolerance=2e-12)
    Path(name+suffix+'.json').write_text(json.dumps(artifact(matrix,result.amplitudes),indent=2))
    return matrix,result.amplitudes

if __name__=='__main__':
    evaluator=Evaluator()
    started=time.time()
    iteration=0
    print('INITIAL',summary(evaluator.value(initial_coefficients)),time.time()-started,flush=True)
    print('JACOBIAN',evaluator.jacobian(initial_coefficients).shape,time.time()-started,flush=True)
    class Found(Exception):
        pass
    def callback(current):
        global iteration
        iteration+=1
        values=evaluator.value(current)
        if iteration%5==0:
            print('ITERATION',iteration,'seconds',time.time()-started,'metrics',summary(values),flush=True)
            np.save(name+'_latest.npy',current)
            save(current,'_latest')
        if np.min(values[1:])>=-1e-8:
            matrix,amplitudes=save(current,'_feasible')
            result=robust_screen(matrix,amplitudes,oracle,check_paths=False)
            print('FEASIBLE',{key:value for key,value in result.items() if key!='points'},flush=True)
            if result['endpoint_feasible']:
                raise Found()
    try:
        answer=minimize(lambda current:evaluator.value(current)[0],initial_coefficients,
            jac=lambda current:evaluator.jacobian(current)[0],method='SLSQP',
            bounds=list(zip(np.maximum(-1.498,initial_coefficients-radius),np.minimum(1.498,initial_coefficients+radius))),
            constraints=[{'type':'ineq','fun':lambda current:evaluator.value(current)[1:],
                          'jac':lambda current:evaluator.jacobian(current)[1:]}],
            callback=callback,options={'maxiter':450,'ftol':1e-11,'disp':True})
        save(answer.x,'_end')
        print('END',answer.message,time.time()-started,flush=True)
    except Found:
        print('SUCCESS',time.time()-started,flush=True)
