import argparse
import json
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
import jax
import jax.numpy as jnp
from search_model import oracle, axes, hbase, haxes_jax, hfbase, hfaxes, equations, targets, ref, one, structured, paired_amplitudes, bounds
from api import artifact

parser=argparse.ArgumentParser()
parser.add_argument('--seed',default='fullgradient_0.json')
parser.add_argument('--prefix',default='state')
parser.add_argument('--full',action='store_true')
parser.add_argument('--iterations',type=int,default=2500)
parser.add_argument('--population',type=float,default=.0201)
parser.add_argument('--error',type=float,default=.00009)
parser.add_argument('--dad',type=float,default=.0009)
parser.add_argument('--eommax',type=float,default=100)
parser.add_argument('--infidmin',type=float,default=0)
parser.add_argument('--exactnoise',type=float,default=0)
arguments=parser.parse_args()
selection=np.arange(120) if arguments.full else np.array(structured)
active=np.arange(18) if arguments.full else paired_amplitudes
exact_active=np.arange(1,20) if arguments.full else np.array(sorted(list(oracle.targets[active])+[19]))
coefficient_count=len(selection); amplitude_count=len(active)


def compute(values):
    coefficients=jnp.zeros(120).at[selection].set(values[:coefficient_count])
    amplitudes=jnp.zeros(18).at[active].set(values[coefficient_count:coefficient_count+amplitude_count])
    multipliers=jnp.zeros(18).at[active].set(values[coefficient_count+amplitude_count:coefficient_count+2*amplitude_count])
    exact=ref.at[exact_active].set(values[coefficient_count+2*amplitude_count:])
    exact=exact/jnp.linalg.norm(exact)
    hamiltonian=jnp.array(hbase)+jnp.einsum('k,kij->ij',coefficients,haxes_jax)
    residual,jacobian,transformed,positive,inverse=equations(hamiltonian,amplitudes)
    right=positive[:,0]
    left=ref.at[targets].set(multipliers)@inverse
    density=jnp.einsum('i,pqij,j->pq',left,one,right)
    occupations=jnp.linalg.eigvalsh((density+density.T)/2)
    exact_energy=exact@hamiltonian@exact
    gradient=jnp.einsum('i,kij,j->k',left,haxes_jax,right)-jnp.einsum('i,kij,j->k',exact,haxes_jax,exact)
    real_hf,imag_hf=jnp.array(hfbase)+jnp.einsum('k,kbij->bij',coefficients,jnp.array(hfaxes))
    singular=jnp.linalg.svd(jacobian,compute_uv=False)
    lifted=hamiltonian-exact_energy*jnp.eye(20)+20*jnp.outer(exact,exact)
    diagnostic=jnp.array([
        occupations[0],occupations[-1]-1,transformed[0,0]-exact_energy,jnp.linalg.norm(gradient),
        1-(exact@right)**2/(right@right),exact[0]**2,jnp.linalg.eigvalsh(lifted)[0],
        jnp.linalg.eigvalsh(real_hf)[0],jnp.linalg.eigvalsh(imag_hf)[0],singular[0]/singular[-1],
        jnp.linalg.norm(multipliers),jnp.linalg.norm(amplitudes),jnp.sqrt(jnp.sum((density-density.T)**2)/3+1e-30),
        jnp.linalg.norm(coefficients),jnp.min(jnp.linalg.eigvals(jacobian).real),singular[-1],
    ])
    lambda_residual=transformed[0,targets]+jacobian.T@multipliers
    exact_residual=hamiltonian@exact-exact_energy*exact
    return jnp.concatenate((diagnostic,residual[active],lambda_residual[active],exact_residual[exact_active]))


metric_function=jax.jit(compute)
gradient_function=jax.jit(jax.jacfwd(compute))
last_values=None
cached=None


def evaluate(values):
    global last_values,cached
    if last_values is None or not np.array_equal(values,last_values):
        cached=np.array(metric_function(values)),np.array(gradient_function(values))
        last_values=values.copy()
    return cached


def margins(diagnostic):
    minimum,maximum,error,gradient,infidelity,reference,gap,real_hf,imag_hf,condition,multiplier,amplitude,dad,norm,eom,singular=diagnostic[:16]
    return np.array([
        10*(-arguments.population-minimum),
        (arguments.error-error)/.001,(arguments.error+error)/.001,
        (.000999-infidelity)/.01,reference-.4501,gap-.1005,real_hf-.0505,imag_hf-.0505,
        (99-condition)/100,1.499-multiplier,1.249-amplitude,(arguments.dad-dad)/.01,(6.998-norm)/7,eom-.0501,singular-.0201,arguments.eommax-eom,
        (infidelity-arguments.infidmin)/.01,
    ])


matrix=np.zeros((17,16+2*amplitude_count+len(exact_active)))
for row,index,scale in [(0,0,-10),(1,2,-1000),(2,2,1000),(3,4,-100),(4,5,1),(5,6,1),(6,7,1),(7,8,1),(8,9,-.01),(9,10,-1),(10,11,-1),(11,12,-100),(12,13,-1/7),(13,14,1),(14,15,1),(15,14,-1)]:
    matrix[row,index]=scale
matrix[16,4]=100


def save(values,filename):
    coefficients=np.zeros(120);coefficients[selection]=values[:coefficient_count]
    amplitudes=np.zeros(18);amplitudes[active]=values[coefficient_count:coefficient_count+amplitude_count]
    pair_matrix=np.einsum('k,kij->ij',coefficients,axes)
    Path(filename).write_text(json.dumps(artifact(pair_matrix,amplitudes),indent=2))


seed_data=json.loads(Path(arguments.seed).read_text())
filenames=[entry[1] for entry in seed_data] if isinstance(seed_data,list) else [arguments.seed]
started=time.monotonic();best=np.inf
for start,filename in enumerate(filenames):
    data=json.loads(Path(filename).read_text());pair_matrix=np.array(data['pair_matrix'])
    coefficients=np.einsum('kij,ij->k',axes,pair_matrix)[selection]
    hamiltonian=oracle.hamiltonian(data['orbital_energies'],pair_matrix)[0]
    result=oracle.solve(hamiltonian,data['amplitudes']);multipliers=oracle.lambda_state(result)[0]
    _,vectors=np.linalg.eigh(hamiltonian);exact=vectors[:,0]/vectors[0,0]
    exact[exact_active]+=np.random.default_rng(348+start).normal(size=len(exact_active))*arguments.exactnoise
    initial=np.concatenate((coefficients,result.amplitudes[active],multipliers[active],exact[exact_active]))
    iteration=[0]

    def callback(values):
        global best
        iteration[0]+=1;diagnostic,_=evaluate(values)
        margin=min(min(margins(diagnostic)),-max(abs(diagnostic[16:])))
        if margin>-1e-8 and diagnostic[3]<best:
            best=diagnostic[3];save(values,f'{arguments.prefix}_best.json')
            print('BEST',start,iteration[0],diagnostic[:16].tolist(),flush=True)
        if iteration[0]%50==0:
            save(values,f'{arguments.prefix}_current.json')
            print('progress',start,iteration[0],diagnostic[:16].tolist(),'margin',margin,'seconds',time.monotonic()-started,flush=True)

    constraints=[{'type':'ineq','fun':lambda values:margins(evaluate(values)[0]),'jac':lambda values:matrix@evaluate(values)[1]}, {'type':'eq','fun':lambda values:evaluate(values)[0][16:],'jac':lambda values:evaluate(values)[1][16:]}]
    answer=minimize(lambda values:(evaluate(values)[0][3],evaluate(values)[1][3]),initial,jac=True,method='SLSQP',bounds=bounds(selection)+[(-1.5,1.5)]*(2*amplitude_count+len(exact_active)),constraints=constraints,callback=callback,options={'maxiter':arguments.iterations,'ftol':1e-12})
    callback(answer.x);save(answer.x,f'{arguments.prefix}_{start}.json')
    print('END',start,answer.message,evaluate(answer.x)[0][:16].tolist(),'margin',min(margins(evaluate(answer.x)[0])),flush=True)
