from kinematics import calculate
from search import np,jax,jnp,time,minimize,oracle

@jax.jit
def outputs(current):
    values,density=calculate(current)
    return jnp.array([values[2]**2,jnp.maximum(values[0],values[1])-.0201,.0003-values[3],values[4]-.4501,1.249-values[5],1.499-values[6]])

jacobian=jax.jit(jax.jacfwd(outputs))

rng=np.random.default_rng(121901)
best=1e10
for number in range(80):
    amplitudes=rng.normal(size=18)
    amplitudes*=rng.uniform(.3,1.05)/np.linalg.norm(amplitudes)
    positive,inverse=oracle.exponentials(amplitudes)
    right=positive[:,0]
    multipliers=(right@positive)[oracle.targets]/(right@right)+rng.normal(0,.12,18)
    initial=np.r_[amplitudes,multipliers]
    result=minimize(lambda current:float(outputs(current)[0]),initial,jac=lambda current:np.asarray(jacobian(current))[0],method='SLSQP',
        constraints=[{'type':'ineq','fun':lambda current:np.asarray(outputs(current))[1:],'jac':lambda current:np.asarray(jacobian(current))[1:]}],options={'maxiter':700,'ftol':1e-11})
    values=np.asarray(outputs(result.x))
    feasible=min(values[1:])> -1e-7
    print('RESULT',number,'feasible',feasible,'gradient',np.sqrt(values[0]),'constraints',values[1:].tolist(),flush=True)
    if feasible and values[0]<best:
        best=values[0]
        np.savez('global_kinematic_best.npz',variables=result.x)
        print('BEST',number,np.sqrt(best),flush=True)
