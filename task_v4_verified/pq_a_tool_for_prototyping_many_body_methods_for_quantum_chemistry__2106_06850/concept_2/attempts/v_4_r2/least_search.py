import search as engine
from search import np, jax, jnp, json, Path, time, oracle, axes, basis, free, artifact, endpoint_failures
from scipy.optimize import least_squares
upper=np.triu_indices(6,1)

@jax.jit
def residuals(variables,settings):
    values,residual,density=engine.calculation(variables)
    violation=jnp.maximum(values[0],values[1])
    constraints=jnp.array([
        values[3]-settings[0]*1000,
        (.99905-values[4])*100,
        .451-values[5],
        .106-values[6],
        .057-values[7],
        .057-values[8],
        .025-values[9],
        (values[10]-98)/100,
        values[11]-1.248,
        values[12]-1.498,
        (values[14]-6.99)/10,
    ])
    return jnp.concatenate((residual*settings[2],(density-density.T)[upper]*settings[2],jnp.array([values[2]*settings[2]*1000]),jnp.maximum(constraints,0)*settings[2],jnp.array([jnp.maximum(settings[1]-violation,0)*100])))

jacobian=jax.jit(jax.jacfwd(residuals,argnums=0))

def optimize(initial,label,target=.0205,weight=100,maximum=1500):
    settings=np.array([.000094,target,weight])
    count=[0]
    started=time.time()
    def function(current):
        count[0]+=1
        if count[0]%100==0:
            print('ITER',label,count[0],round(time.time()-started,2),np.asarray(engine.metrics(current)).round(9).tolist(),'cost',np.linalg.norm(residuals(current,settings)),flush=True)
            np.savez(f'live_{label}.npz',variables=current)
        return np.asarray(residuals(current,settings))
    bounds=[(-1.498*(1 if row==column else np.sqrt(2)), 1.498*(1 if row==column else np.sqrt(2))) for row in range(15) for column in range(row,15)]+[(-1.248,1.248)]*18
    bounds=np.array(bounds).T
    initial=np.clip(initial[:138],bounds[0]+1e-10,bounds[1]-1e-10)
    result=least_squares(function,initial,jac=lambda current:np.asarray(jacobian(current,settings)),bounds=bounds,ftol=1e-12,xtol=1e-12,gtol=1e-12,max_nfev=maximum,verbose=0)
    current=result.x
    np.savez(f'least_{label}.npz',variables=current)
    interaction=np.einsum('k,kij->ij',current[:120],axes)
    hamiltonian=free+np.einsum('k,kij->ij',current[:120],basis)
    stationary=oracle.solve(hamiltonian,current[120:])
    diagnostics=oracle.diagnostics(hamiltonian,stationary)
    Path(f'least_{label}.json').write_text(json.dumps(artifact(interaction,stationary.amplitudes)))
    summary={'success':bool(result.success),'message':result.message,'metrics':np.asarray(engine.metrics(current)).tolist(),'cost':result.cost,'optimality':result.optimality,'diagnostics':diagnostics,'failures':endpoint_failures(diagnostics)}
    Path(f'least_{label}.report.json').write_text(json.dumps(summary,indent=2))
    print('RESULT',label,json.dumps(summary),flush=True)
    return current

if __name__=='__main__':
    initial=np.load('refine_0a.npz')['variables']
    current=optimize(initial,'first',weight=100,maximum=2000)
    current=optimize(current,'second',weight=1000,maximum=2000)
