import search as engine
from search import np,jax,jnp,json,Path,time,minimize,oracle,axes,basis,free,artifact
EXTRA_AXES=()

def equations(coordinates,amplitudes):
    hamiltonian=jnp.einsum('k,kij->ij',coordinates,jnp.array(basis))+jnp.array(free)
    cluster=jnp.einsum('k,kij->ij',amplitudes,engine.generators)
    square=cluster@cluster/2
    cube=square@cluster/3
    positive=engine.identity+cluster+square+cube
    inverse=engine.identity-cluster+square-cube
    transformed=inverse@hamiltonian@positive
    column=transformed[:,oracle.reference]
    jacobian=transformed[jnp.ix_(oracle.targets,oracle.targets)]-jnp.einsum('kij,j->ik',engine.generators,column)[oracle.targets]
    return column[oracle.targets],jacobian,transformed,positive,inverse,hamiltonian

def adaptive_direction(coordinates,amplitudes):
    residual,jacobian,transformed,positive,inverse,hamiltonian=equations(coordinates,amplitudes)
    multipliers=jnp.linalg.solve(jacobian.T,-transformed[oracle.reference,oracle.targets])
    left=jnp.array(oracle.ref).at[oracle.targets].set(multipliers)@inverse
    right=positive[:,oracle.reference]
    energies,vectors=jnp.linalg.eigh(hamiltonian)
    exact=vectors[:,0]
    gradient=jnp.einsum('i,kij,j->k',left,jnp.array(basis),right)-jnp.einsum('i,kij,j->k',exact,jnp.array(basis),exact)
    return gradient/jnp.linalg.norm(gradient)

def neighboring(coordinates,amplitudes):
    for iteration in range(4):
        residual,jacobian,_,_,_,_=equations(coordinates,amplitudes)
        amplitudes=amplitudes-jnp.linalg.solve(jacobian,residual)
    return amplitudes

@jax.jit
def outputs(current,base_dad=.0002):
    coordinates=current[:120]
    amplitudes=current[120:]
    direction=adaptive_direction(coordinates,amplitudes)
    base,residual,density=engine.calculation(current)
    rows=[base]
    for sign in (1,-1):
        point=coordinates+sign*.001*direction
        perturbed=neighboring(point,amplitudes)
        rows.append(engine.calculation(jnp.concatenate((point,perturbed)))[0])
    for axis,sign in EXTRA_AXES:
        point=coordinates.at[axis].add(sign*.001)
        perturbed=neighboring(point,amplitudes)
        rows.append(engine.calculation(jnp.concatenate((point,perturbed)))[0])
    values=jnp.stack(rows)
    reference=jnp.array([.4512]+[.45005]*(len(rows)-1))
    hf=jnp.array([.0517]+[.0502]*(len(rows)-1))
    gap=jnp.array([.1013]+[.1002]*(len(rows)-1))
    dad=jnp.array([base_dad]+[.000995]*(len(rows)-1))
    constraints=jnp.concatenate((
        (.0000999-values[:,2])*1000,
        (.0000999+values[:,2])*1000,
        (dad**2-values[:,13])*100000,
        (values[:,4]-.99903)*100,
        values[:,5]-reference,
        values[:,6]-gap,
        values[:,7]-hf,
        values[:,8]-hf,
        values[:,9]-.025,
        (98-values[:,10])/100,
        1.248-values[:,11],
        1.498-values[:,12],
        (6.995-values[:,14])/10,
    ))
    return jnp.concatenate((jnp.array([-jnp.min(values[:,0])*10]),residual,constraints))

jacobian=jax.jit(jax.jacfwd(outputs))

def optimize(initial,label,maxiter=1200,trust=.15):
    initial=initial[:138]
    last=[None,None,None]
    count=[0]
    started=time.time()
    def cached(current):
        if last[0] is None or not np.array_equal(last[0],current):
            last[:]=current.copy(),np.asarray(outputs(current)),np.asarray(jacobian(current))
        return last[1:]
    def callback(current):
        count[0]+=1
        if count[0]%25==0:
            values,derivatives=cached(current)
            print('ITER',label,count[0],round(time.time()-started,2),'objective',-values[0]/10,'residual',max(abs(values[1:19])),'ineq',min(values[19:]),np.asarray(engine.metrics(current)).round(9).tolist(),flush=True)
            np.savez(f'finite_live{label}.npz',variables=current)
    bounds=[(-1.498*(1 if row==column else np.sqrt(2)), 1.498*(1 if row==column else np.sqrt(2))) for row in range(15) for column in range(row,15)]+[(-1.248,1.248)]*18
    if trust is not None:
        bounds=[(max(lower,center-trust),min(upper,center+trust)) for (lower,upper),center in zip(bounds,initial)]
    result=minimize(lambda current:cached(current)[0][0],initial,jac=lambda current:cached(current)[1][0],method='SLSQP',bounds=bounds,
        constraints=[{'type':'eq','fun':lambda current:cached(current)[0][1:19],'jac':lambda current:cached(current)[1][1:19]},
                     {'type':'ineq','fun':lambda current:cached(current)[0][19:],'jac':lambda current:cached(current)[1][19:]}],callback=callback,
        options={'maxiter':maxiter,'ftol':1e-11,'disp':False})
    current=result.x
    matrix=np.einsum('k,kij->ij',current[:120],axes)
    stationary=oracle.solve(free+np.einsum('k,kij->ij',current[:120],basis),current[120:])
    Path(f'finite_{label}.json').write_text(json.dumps(artifact(matrix,stationary.amplitudes)))
    np.savez(f'finite_{label}.npz',variables=np.r_[current[:120],stationary.amplitudes])
    print('RESULT',label,result.message,np.asarray(engine.metrics(np.r_[current[:120],stationary.amplitudes])).tolist(),'ineq',min(cached(current)[0][19:]),flush=True)
    return np.r_[current[:120],stationary.amplitudes]

if __name__=='__main__':
    current=np.load('polished_retry.npz')['variables']
    for number in range(6):
        candidate=optimize(current,str(number),800,.12)
        values=np.asarray(outputs(candidate))
        if max(abs(values[1:19]))<1e-8 and min(values[19:])>-.01:
            current=candidate
