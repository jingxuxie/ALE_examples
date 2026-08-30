import search as engine
import finite
from search import np,jax,jnp,json,Path,time,minimize,oracle,axes,basis,free,artifact
other=np.array([index for index in range(20) if index!=oracle.reference])
upper=np.triu_indices(6,1)

def density_state(amplitudes,multipliers):
    cluster=jnp.einsum('k,kij->ij',amplitudes,engine.generators)
    square=cluster@cluster/2
    cube=square@cluster/3
    positive=engine.identity+cluster+square+cube
    inverse=engine.identity-cluster+square-cube
    right=positive[:,oracle.reference]
    left=jnp.array(oracle.ref).at[oracle.targets].set(multipliers)@inverse
    return jnp.einsum('i,pqij,j->pq',left,engine.one,right)

def dad_response(coordinates,amplitudes,multipliers,direction,jacobian,positive,inverse):
    perturbation=jnp.einsum('k,kij->ij',direction,jnp.array(basis))
    source=(inverse@perturbation@positive)[oracle.targets,oracle.reference]
    amplitude_response=jnp.linalg.solve(jacobian,-source)
    def stationarity(point,cluster):
        _,matrix,transformed,_,_,_=finite.equations(point,cluster)
        return transformed[oracle.reference,oracle.targets]+multipliers@matrix
    lambda_source=jax.jvp(stationarity,(coordinates,amplitudes),(direction,amplitude_response))[1]
    multiplier_response=jnp.linalg.solve(jacobian.T,-lambda_source)
    density_response=jax.jvp(density_state,(amplitudes,multipliers),(amplitude_response,multiplier_response))[1]
    return jnp.linalg.norm(density_response-density_response.T)/jnp.sqrt(3)

@jax.jit
def outputs(current):
    coordinates=current[:120]
    amplitudes=current[120:138]
    multipliers=current[138:]
    residual,jacobian,transformed,positive,inverse,hamiltonian=finite.equations(coordinates,amplitudes)
    right=positive[:,oracle.reference]
    left=jnp.array(oracle.ref).at[oracle.targets].set(multipliers)@inverse
    density=jnp.einsum('i,pqij,j->pq',left,engine.one,right)
    occupations=jnp.linalg.eigvalsh((density+density.T)/2)
    gradient=jnp.einsum('i,kij,j->k',left,jnp.array(basis),right)-jnp.einsum('i,kij,j->k',right,jnp.array(basis),right)/(right@right)
    energy=transformed[oracle.reference,oracle.reference]
    shifted=hamiltonian-energy*jnp.eye(20)+10*jnp.outer(right,right)/(right@right)
    real_hessian=jnp.einsum('k,kij->ij',coordinates,jnp.array(engine.hf_real))+jnp.array(engine.hf_free[0])
    imag_hessian=jnp.einsum('k,kij->ij',coordinates,jnp.array(engine.hf_imag))+jnp.array(engine.hf_free[1])
    singular=jnp.linalg.svd(jacobian,compute_uv=False)
    response=dad_response(coordinates,amplitudes,multipliers,gradient/jnp.linalg.norm(gradient),jacobian,positive,inverse)
    constraints=jnp.array([
        .098-jnp.linalg.norm(gradient),
        1/(right@right)-.454,
        jnp.linalg.eigvalsh(shifted)[0]-.11,
        jnp.linalg.eigvalsh(real_hessian)[0]-.058,
        jnp.linalg.eigvalsh(imag_hessian)[0]-.058,
        1.248-jnp.linalg.norm(amplitudes),
        1.498-jnp.linalg.norm(multipliers),
        6.99-jnp.linalg.norm(coordinates),
        (96-singular[0]/singular[-1])/100,
        singular[-1]-.025,
        .9-response,
    ])
    return jnp.concatenate((jnp.array([occupations[0]*10]),transformed[other,oracle.reference],transformed[oracle.reference,oracle.targets]+multipliers@jacobian,(density-density.T)[upper],constraints))

jacobian=jax.jit(jax.jacfwd(outputs))

def optimize(initial,label,maxiter=1500,trust=.12):
    hamiltonian=free+np.einsum('k,kij->ij',initial[:120],basis)
    result=oracle.solve(hamiltonian,initial[120:138])
    multipliers,_,_=oracle.lambda_state(result)
    initial=np.r_[initial[:120],result.amplitudes,multipliers]
    last=[None,None,None]
    count=[0]
    started=time.time()
    def cached(current):
        if last[0] is None or not np.array_equal(last[0],current):
            last[:]=current.copy(),np.asarray(outputs(current)),np.asarray(jacobian(current))
        return last[1:]
    def callback(current):
        count[0]+=1
        if count[0]%50==0:
            values,_=cached(current)
            print('ITER',label,count[0],round(time.time()-started,2),-values[0]/10,'eq',max(abs(values[1:53])),'ineq',min(values[53:]),flush=True)
            np.savez(f'exact_live{label}.npz',variables=current)
    bounds=[(-1.498*(1 if row==column else np.sqrt(2)), 1.498*(1 if row==column else np.sqrt(2))) for row in range(15) for column in range(row,15)]+[(-1.248,1.248)]*18+[(-1.498,1.498)]*18
    if trust is not None:
        bounds=[(max(lower,center-trust),min(upper,center+trust)) for (lower,upper),center in zip(bounds,initial)]
    result=minimize(lambda current:cached(current)[0][0],initial,jac=lambda current:cached(current)[1][0],method='SLSQP',bounds=bounds,
        constraints=[{'type':'eq','fun':lambda current:cached(current)[0][1:53],'jac':lambda current:cached(current)[1][1:53]},
                     {'type':'ineq','fun':lambda current:cached(current)[0][53:],'jac':lambda current:cached(current)[1][53:]}],callback=callback,
        options={'maxiter':maxiter,'ftol':1e-11,'disp':False})
    current=result.x
    matrix=np.einsum('k,kij->ij',current[:120],axes)
    stationary=oracle.solve(free+np.einsum('k,kij->ij',current[:120],basis),current[120:138])
    Path(f'exact_{label}.json').write_text(json.dumps(artifact(matrix,stationary.amplitudes)))
    np.savez(f'exact_{label}.npz',variables=np.r_[current[:120],stationary.amplitudes])
    print('RESULT',label,result.message,np.asarray(engine.metrics(np.r_[current[:120],stationary.amplitudes])).tolist(),'ineq',min(cached(current)[0][53:]),flush=True)
    return np.r_[current[:120],stationary.amplitudes]

if __name__=='__main__':
    current=np.load('polished_mid2.npz')['variables']
    for number in range(5):
        candidate=optimize(current,'robust'+str(number),1500,.12)
        values=np.asarray(engine.metrics(candidate))
        if values[3]<.1 and abs(values[2])<1e-5 and values[4]>.9999:
            current=candidate
