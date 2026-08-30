import search as engine
from search import np, jax, jnp, json, Path, time, minimize, oracle, axes, basis, free, artifact, endpoint_failures
import sys

@jax.jit
def outputs(variables, settings):
    values, residual, density = engine.calculation(variables)
    violation = jnp.maximum(values[0], values[1])
    objective = values[13] * settings[0] - violation * settings[1] + values[3]**2 * settings[2]
    constraints = jnp.array([
        settings[3] - values[3],
        (values[4] - 0.99915)*100,
        values[5] - 0.455,
        values[6] - 0.115,
        values[7] - 0.065,
        values[8] - 0.065,
        values[9] - 0.03,
        (95 - values[10])/100,
        1.245 - values[11],
        1.495 - values[12],
        (settings[4]**2-values[13])*100,
        (6.98-values[14])/10,
        (violation-settings[5])*10,
    ])
    return jnp.concatenate((jnp.array([objective]), residual, jnp.array([values[2]]), constraints))

jacobian = jax.jit(jax.jacfwd(outputs,argnums=0))

def refine(variables, settings, label, maxiter=500):
    last = [None,None,None]
    count = [0]
    started = time.time()
    def cached(current):
        if last[0] is None or not np.array_equal(last[0],current):
            last[:] = current.copy(), np.asarray(outputs(current,settings)), np.asarray(jacobian(current,settings))
        return last[1:]
    def callback(current):
        count[0] += 1
        if count[0]%25 == 0:
            values, derivatives = cached(current)
            print('ITER',label,count[0],round(time.time()-started,2),np.asarray(engine.metrics(current)).round(8).tolist(),'res',max(abs(values[1:20])),'ineq',min(values[20:]),flush=True)
            np.savez(f'live_{label}.npz',variables=current)
    bounds = [(-1.498*(1 if row==column else np.sqrt(2)), 1.498*(1 if row==column else np.sqrt(2))) for row in range(15) for column in range(row,15)] + [(-1.245,1.245)]*18
    result = minimize(lambda current:cached(current)[0][0],variables,jac=lambda current:cached(current)[1][0],method='SLSQP',bounds=bounds,
        constraints=[{'type':'eq','fun':lambda current:cached(current)[0][1:20],'jac':lambda current:cached(current)[1][1:20]},
                     {'type':'ineq','fun':lambda current:cached(current)[0][20:],'jac':lambda current:cached(current)[1][20:]}],
        callback=callback,options={'maxiter':maxiter,'ftol':1e-11,'disp':False})
    current=result.x
    np.savez(f'refine_{label}.npz',variables=current)
    interaction=np.einsum('k,kij->ij',current[:120],axes)
    hamiltonian=free+np.einsum('k,kij->ij',current[:120],basis)
    stationary=oracle.solve(hamiltonian,current[120:])
    diagnostics=oracle.diagnostics(hamiltonian,stationary)
    Path(f'refine_{label}.json').write_text(json.dumps(artifact(interaction,stationary.amplitudes)))
    summary={'success':bool(result.success),'message':result.message,'metrics':np.asarray(engine.metrics(current)).tolist(),'res':float(max(abs(cached(current)[0][1:20]))),'ineq':float(min(cached(current)[0][20:])), 'diagnostics':diagnostics,'failures':endpoint_failures(diagnostics)}
    Path(f'refine_{label}.report.json').write_text(json.dumps(summary,indent=2))
    print('RESULT',label,json.dumps(summary),flush=True)
    return current

if __name__=='__main__':
    initial=np.load('random.npz')['variables'][0]
    rng=np.random.default_rng(7821)
    for number in range(20):
        if number==0:
            current=initial.copy()
        else:
            current=initial+rng.normal(0,.06,138)
        current=refine(current,np.array([10.,0.,0.,1.,1.,.024]),f'{number}a',400)
        current=refine(current,np.array([10.,0.,0.05,.095,1.,.023]),f'{number}b',400)
        current=refine(current,np.array([0.,1.,0.,.085,.0006,.021]),f'{number}c',400)
