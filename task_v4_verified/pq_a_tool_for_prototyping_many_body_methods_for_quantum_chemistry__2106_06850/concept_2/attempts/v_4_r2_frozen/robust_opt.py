import search as engine
from search import np, jax, jnp, json, Path, time, minimize, oracle, axes, basis, free, artifact, endpoint_failures

@jax.jit
def outputs(variables,settings):
    values,residual,density=engine.calculation(variables[:138])
    epigraph=variables[138]
    violation=jnp.maximum(values[0],values[1])
    robust=epigraph*1000+values[3]
    objective=settings[0]*robust-settings[1]*violation
    constraints=jnp.array([
        (epigraph-values[2])*1000,
        (epigraph+values[2])*1000,
        settings[2]-robust,
        (values[4]-.99905)*100,
        values[5]-.451,
        values[6]-.106,
        values[7]-.057,
        values[8]-.057,
        values[9]-.025,
        (98-values[10])/100,
        1.248-values[11],
        1.498-values[12],
        (settings[3]-jnp.sqrt(values[13]+1e-30))*10,
        (6.995-values[14])/10,
        (violation-settings[4])*10,
    ])
    return jnp.concatenate((jnp.array([objective]),residual,constraints))

jacobian=jax.jit(jax.jacfwd(outputs,argnums=0))

def optimize(initial,settings,label,maxiter=1500):
    if len(initial)==138:
        initial=np.r_[initial,abs(float(engine.metrics(initial)[2]))+1e-9]
    last=[None,None,None]
    count=[0]
    started=time.time()
    def cached(current):
        if last[0] is None or not np.array_equal(last[0],current):
            last[:]=current.copy(),np.asarray(outputs(current,settings)),np.asarray(jacobian(current,settings))
        return last[1:]
    def callback(current):
        count[0]+=1
        if count[0]%50==0:
            values,derivatives=cached(current)
            print('ITER',label,count[0],round(time.time()-started,2),np.asarray(engine.metrics(current[:138])).round(9).tolist(),'epi',current[138],'res',max(abs(values[1:19])),'ineq',min(values[19:]),flush=True)
            np.savez(f'live_{label}.npz',variables=current)
    bounds=[(-1.498*(1 if row==column else np.sqrt(2)), 1.498*(1 if row==column else np.sqrt(2))) for row in range(15) for column in range(row,15)]+[(-1.248,1.248)]*18+[(0,1)]
    result=minimize(lambda current:cached(current)[0][0],initial,jac=lambda current:cached(current)[1][0],method='SLSQP',bounds=bounds,
        constraints=[{'type':'eq','fun':lambda current:cached(current)[0][1:19],'jac':lambda current:cached(current)[1][1:19]},
                     {'type':'ineq','fun':lambda current:cached(current)[0][19:],'jac':lambda current:cached(current)[1][19:]}],callback=callback,
        options={'maxiter':maxiter,'ftol':1e-11,'disp':False})
    current=result.x
    np.savez(f'robust_{label}.npz',variables=current)
    interaction=np.einsum('k,kij->ij',current[:120],axes)
    hamiltonian=free+np.einsum('k,kij->ij',current[:120],basis)
    stationary=oracle.solve(hamiltonian,current[120:138])
    diagnostics=oracle.diagnostics(hamiltonian,stationary)
    Path(f'robust_{label}.json').write_text(json.dumps(artifact(interaction,stationary.amplitudes)))
    summary={'success':bool(result.success),'message':result.message,'metrics':np.asarray(engine.metrics(current[:138])).tolist(),'epi':current[138],'res':float(max(abs(cached(current)[0][1:19]))),'ineq':float(min(cached(current)[0][19:])), 'diagnostics':diagnostics,'failures':endpoint_failures(diagnostics)}
    Path(f'robust_{label}.report.json').write_text(json.dumps(summary,indent=2))
    print('RESULT',label,json.dumps(summary),flush=True)
    return current

if __name__=='__main__':
    initial=np.load('refine_0a.npz')['variables']
    current=optimize(initial,np.array([1.,0.,1.,.0001,.0202]),'min',1500)
    current=optimize(current,np.array([0.,1.,.095,.0001,0.]),'max',1500)
