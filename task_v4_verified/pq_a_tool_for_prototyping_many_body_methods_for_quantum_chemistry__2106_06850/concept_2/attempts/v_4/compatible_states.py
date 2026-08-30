import json
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
import jax
import jax.numpy as jnp
from search_model import oracle,generator_flat,identity,targets,ref,one,haxes_jax


def measurements(values):
    amplitudes=values[:18];multipliers=values[18:36]
    exact=ref.at[1:].set(values[36:55]);exact=exact/jnp.linalg.norm(exact)
    delta=values[55]*1e-4;triple_residual=values[56]*.1;left_residual=values[57]*.1
    cluster=(amplitudes@generator_flat).reshape(20,20);square=cluster@cluster/2;cube=square@cluster/3
    right=(identity+cluster+square+cube)[:,0];inverse=identity-cluster+square-cube
    normal=inverse[-1];left=ref.at[targets].set(multipliers)@inverse
    density=jnp.einsum('i,pqij,j->pq',left,one,right)
    gradient=jnp.einsum('i,kij,j->k',left,haxes_jax,right)-jnp.einsum('i,kij,j->k',exact,haxes_jax,exact)
    projected_right=right-(exact@right)*exact;projected_left=left-(exact@left)*exact
    tangent=jnp.stack((projected_right,projected_left));gram=tangent@tangent.T
    image_right=delta*right+jnp.eye(20)[-1]*triple_residual
    image_left=delta*left+normal*left_residual
    image=jnp.stack((image_right,image_left));image_gram=image@image.T
    quadratic=jnp.array([[right@image_right,delta],[delta,left@image_left]])
    lower=jnp.linalg.eigvalsh(quadratic-.1*gram)[0]
    bounded=jnp.linalg.eigvalsh(30.1*quadratic-image_gram-3*gram)[0]
    return jnp.array([jnp.linalg.norm(gradient),jnp.linalg.eigvalsh((density+density.T)/2)[0],jnp.linalg.norm(amplitudes),jnp.linalg.norm(multipliers),exact[0]**2,1-(exact@right)**2/(right@right),jnp.sqrt(jnp.sum((density-density.T)**2)/3+1e-30),lower,bounded,triple_residual*exact[-1]+delta*(exact@right),left_residual*(exact@normal)+delta*(exact@left)])


evaluate=jax.jit(measurements);derivative=jax.jit(jax.jacfwd(measurements))
matrix=np.zeros((9,11));offset=np.array([-.0201,1.25,1.5,-.45,.001,-.0007,.001,0,0])
for row,index,scale in [(0,1,-1),(1,2,-1),(2,3,-1),(3,4,1),(4,5,-1),(5,5,1),(6,6,-1),(7,7,1),(8,8,1)]:matrix[row,index]=scale
scales=np.array([10,1,1,1,100,100,100,1000,100]);matrix*=scales[:,None];offset*=scales
data=json.loads(Path('fullgradient_0.json').read_text());hamiltonian=oracle.hamiltonian(data['orbital_energies'],data['pair_matrix'])[0]
result=oracle.solve(hamiltonian,data['amplitudes']);multipliers,left,_=oracle.lambda_state(result);exact_values,exact_vectors=np.linalg.eigh(hamiltonian);exact=exact_vectors[:,0]/exact_vectors[0,0]
initial=np.concatenate((result.amplitudes,multipliers,exact[1:],[0,0,0]));rng=np.random.default_rng(7645);best=1e10;started=time.monotonic()
for trial in range(16):
    values=initial.copy();values[36:55]+=rng.normal(size=19)*.025
    exact_state=np.concatenate(([1.],values[36:55]));exact_state/=np.linalg.norm(exact_state)
    values[55]=(.3 if trial%2 else -.3)
    values[56]=-values[55]*1e-4*(exact_state@result.right)/(exact_state[-1]+1e-12)/.1
    values[57]=-values[55]*1e-4*(exact_state@left)/(exact_state@result.inverse[-1]+1e-12)/.1
    constraints=[{'type':'ineq','fun':lambda point:offset+matrix@np.array(evaluate(point)),'jac':lambda point:matrix@np.array(derivative(point))},{'type':'eq','fun':lambda point:np.array(evaluate(point))[9:]*1000,'jac':lambda point:np.array(derivative(point))[9:]*1000}]
    answer=minimize(lambda point:(float(evaluate(point)[0]),np.array(derivative(point))[0]),values,jac=True,method='SLSQP',bounds=[(-1.5,1.5)]*55+[(-.999,.999),(-10,10),(-10,10)],constraints=constraints,options={'maxiter':1600,'ftol':1e-12})
    diagnostic=np.array(evaluate(answer.x));margin=min(offset+matrix@diagnostic)
    print(trial,answer.message,diagnostic.tolist(),'margin',margin,'seconds',time.monotonic()-started,flush=True)
    if margin>-1e-7 and max(abs(diagnostic[9:]))<1e-9 and diagnostic[0]<best:
        best=diagnostic[0];np.savez('compatible_best.npz',values=answer.x[:55],metrics=diagnostic,active=np.arange(18),exact_active=np.arange(1,20));print('BEST',best,flush=True)
