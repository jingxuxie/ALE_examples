import search as engine
from search import np, jax, jnp, json, Path, time, minimize, oracle, axes, basis, free, artifact, endpoint_failures

@jax.jit
def calculate(variables):
    amplitudes=variables[:18]
    multipliers=variables[18:]
    cluster=jnp.einsum('k,kij->ij',amplitudes,engine.generators)
    square=cluster@cluster/2
    cube=square@cluster/3
    positive=engine.identity+cluster+square+cube
    inverse=engine.identity-cluster+square-cube
    right=positive[:,engine.reference]
    left_row=jnp.array(oracle.ref).at[engine.targets].set(multipliers)
    left=left_row@inverse
    density=jnp.einsum('i,pqij,j->pq',left,engine.one,right)
    occupations=jnp.linalg.eigvalsh((density+density.T)/2)
    gradient=jnp.einsum('i,kij,j->k',left,jnp.array(basis),right)-jnp.einsum('i,kij,j->k',right,jnp.array(basis),right)/(right@right)
    return jnp.array([-occupations[0], occupations[-1]-1, jnp.linalg.norm(gradient), jnp.linalg.norm(density-density.T)/jnp.sqrt(3), 1/(right@right), jnp.linalg.norm(amplitudes), jnp.linalg.norm(multipliers)]), density

@jax.jit
def outputs(variables, target):
    values,density=calculate(variables)
    return jnp.array([values[2]**2, jnp.maximum(values[0],values[1])-target, .00002-values[3], values[4]-.455, 1.24-values[5], 1.49-values[6]])

jacobian=jax.jit(jax.jacfwd(outputs,argnums=0))

def optimize(initial,number,target=.0204):
    last=[None,None,None]
    count=[0]
    def cached(current):
        if last[0] is None or not np.array_equal(last[0],current):
            last[:]=current.copy(),np.asarray(outputs(current,target)),np.asarray(jacobian(current,target))
        return last[1:]
    def callback(current):
        count[0]+=1
        if count[0]%50==0:
            print('ITER',number,count[0],np.asarray(calculate(current)[0]).tolist(),flush=True)
    result=minimize(lambda current:cached(current)[0][0],initial,jac=lambda current:cached(current)[1][0],method='SLSQP',
        constraints=[{'type':'ineq','fun':lambda current:cached(current)[0][1:],'jac':lambda current:cached(current)[1][1:]}],callback=callback,
        options={'maxiter':1000,'ftol':1e-12,'disp':False})
    print('RESULT',number,str(result.message),np.asarray(calculate(result.x)[0]).tolist(),flush=True)
    np.savez(f'kinematic{number}.npz',variables=result.x)
    return result.x

if __name__=='__main__':
    current=np.load('refine_0a.npz')['variables']
    hamiltonian=free+np.einsum('k,kij->ij',current[:120],basis)
    result=oracle.solve(hamiltonian,current[120:])
    multipliers,_,_=oracle.lambda_state(result)
    initial=np.r_[result.amplitudes,multipliers]
    rng=np.random.default_rng(98513)
    for number in range(20):
        optimize(initial if number==0 else initial+rng.normal(0,.1,36),number)
