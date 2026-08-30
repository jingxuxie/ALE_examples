import search as engine
from search import np,jax,jnp,time,oracle,basis,minimize
from kinematics import calculate

other=np.array([index for index in range(20) if index!=oracle.reference])

@jax.jit
def outputs(variables):
    amplitudes=variables[:18]
    multipliers=variables[18:36]
    cluster=jnp.einsum('k,kij->ij',amplitudes,engine.generators)
    square=cluster@cluster/2
    cube=square@cluster/3
    positive=engine.identity+cluster+square+cube
    inverse=engine.identity-cluster+square-cube
    right=positive[:,oracle.reference]
    left=jnp.array(oracle.ref).at[oracle.targets].set(multipliers)@inverse
    exact=jnp.array(oracle.ref).at[other].set(variables[36:55])
    exact=exact/jnp.linalg.norm(exact)
    density=jnp.einsum('i,pqij,j->pq',left,engine.one,right)
    occupations=jnp.linalg.eigvalsh((density+density.T)/2)
    gradient=jnp.einsum('i,kij,j->k',left,jnp.array(basis),right)-jnp.einsum('i,kij,j->k',exact,jnp.array(basis),exact)
    cosine=exact@right/jnp.linalg.norm(right)
    difference=exact[-1]-cosine*right[-1]/jnp.linalg.norm(right)
    budget=variables[55]
    required=.1*(1-cosine**2)*jnp.sqrt(exact[-1]**2+1e-24)
    available=budget*.001*jnp.sqrt(difference**2+1e-24)
    return jnp.array([budget+jnp.linalg.norm(gradient),-occupations[0]-.0202,
        .00001-jnp.linalg.norm(density-density.T)/jnp.sqrt(3),
        (cosine**2-.99905)*100,exact[0]**2-.451,
        1.248-jnp.linalg.norm(amplitudes),1.498-jnp.linalg.norm(multipliers),
        (available-required)*100000])

jacobian=jax.jit(jax.jacfwd(outputs))

def optimize(initial,label):
    count=[0]
    def callback(current):
        count[0]+=1
        if count[0]%100==0:print('ITER',label,count[0],np.asarray(outputs(current)).tolist(),flush=True)
    result=minimize(lambda current:float(outputs(current)[0]),initial,jac=lambda current:np.asarray(jacobian(current))[0],method='SLSQP',bounds=[(None,None)]*55+[(0,1)],
        constraints=[{'type':'ineq','fun':lambda current:np.asarray(outputs(current))[1:],'jac':lambda current:np.asarray(jacobian(current))[1:]}],callback=callback,options={'maxiter':2000,'ftol':1e-12})
    print('RESULT',label,result.message,np.asarray(outputs(result.x)).tolist(),flush=True)
    np.savez(f'general{label}.npz',variables=result.x)
    return result.x

if __name__=='__main__':
    initial=np.load('kinematic0.npz')['variables']
    positive,_=oracle.exponentials(initial[:18])
    current=np.r_[initial,positive[other,oracle.reference],.001]
    optimize(current,'a')
