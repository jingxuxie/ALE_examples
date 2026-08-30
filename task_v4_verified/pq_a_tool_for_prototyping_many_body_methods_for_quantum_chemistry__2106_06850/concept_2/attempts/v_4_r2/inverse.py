import search as engine
from search import np, jax, jnp, json, Path, time, minimize, oracle, axes, basis, free, artifact, endpoint_failures
from scipy.linalg import null_space
import sys

def design(kinematic,label,initial=None,gap=.108):
    amplitudes=kinematic[:18]
    multipliers=kinematic[18:]
    positive,inverse=oracle.exponentials(amplitudes)
    right=positive[:,oracle.reference]
    left_row=oracle.ref.copy()
    left_row[oracle.targets]=multipliers
    left=left_row@inverse
    other=[index for index in range(20) if index!=oracle.reference]
    complement=null_space(right[None,:])
    def linear(matrix):
        residual,jacobian,transformed,_,_=oracle.equations(matrix,amplitudes)
        return np.r_[transformed[other,oracle.reference],transformed[oracle.reference,oracle.targets]+multipliers@jacobian]
    constant=linear(free)
    linear_basis=np.array([linear(matrix) for matrix in basis]).T
    left_singular,singular,right_singular=np.linalg.svd(linear_basis,full_matrices=True)
    rank=sum(singular>1e-10)
    particular=np.linalg.lstsq(linear_basis,-constant,rcond=1e-10)[0]
    remaining=right_singular[rank:].T
    print('SYSTEM',label,'rank',rank,'res',np.linalg.norm(linear_basis@particular+constant),'xnorm',np.linalg.norm(particular), 'remaining',remaining.shape,flush=True)
    energies=np.array([(inverse@matrix@positive)[oracle.reference,oracle.reference] for matrix in basis])
    energy_free=(inverse@free@positive)[oracle.reference,oracle.reference]
    reduced_free=complement.T@(free-energy_free*np.eye(20))@complement
    reduced_basis=np.array([complement.T@(matrix-energy*np.eye(20))@complement for matrix,energy in zip(basis,energies)])
    @jax.jit
    def outputs(variables):
        coordinates=jnp.array(particular)+jnp.array(remaining)@variables
        real_hessian=jnp.einsum('k,kij->ij',coordinates,jnp.array(engine.hf_real))+jnp.array(engine.hf_free[0])
        imag_hessian=jnp.einsum('k,kij->ij',coordinates,jnp.array(engine.hf_imag))+jnp.array(engine.hf_free[1])
        reduced=jnp.einsum('k,kij->ij',coordinates,jnp.array(reduced_basis))+jnp.array(reduced_free)
        entries=jnp.einsum('k,kij->ij',coordinates,jnp.array(axes)).ravel()
        return jnp.concatenate((jnp.array([jnp.sum(coordinates**2)/100]),jnp.linalg.eigvalsh(real_hessian)-.058,jnp.linalg.eigvalsh(imag_hessian)-.058,jnp.linalg.eigvalsh(reduced)-gap,1.498-entries,1.498+entries,jnp.array([6.99-jnp.linalg.norm(coordinates)])))
    derivatives=jax.jit(jax.jacfwd(outputs))
    last=[None,None,None]
    count=[0]
    def cached(current):
        if last[0] is None or not np.array_equal(last[0],current):
            last[:]=current.copy(),np.asarray(outputs(current)),np.asarray(derivatives(current))
        return last[1:]
    def callback(current):
        count[0]+=1
        if count[0]%50==0:print('ITER',label,count[0],cached(current)[0][0],min(cached(current)[0][1:]),flush=True)
    start=np.zeros(remaining.shape[1]) if initial is None else remaining.T@(initial-particular)
    result=minimize(lambda current:cached(current)[0][0],start,jac=lambda current:cached(current)[1][0],method='SLSQP',
        constraints=[{'type':'ineq','fun':lambda current:cached(current)[0][1:],'jac':lambda current:cached(current)[1][1:]}],callback=callback,options={'maxiter':1000,'ftol':1e-11})
    coordinates=particular+remaining@result.x
    interaction=np.einsum('k,kij->ij',coordinates,axes)
    stationary=oracle.solve(free+np.einsum('k,kij->ij',coordinates,basis),amplitudes)
    diagnostics=oracle.diagnostics(free+np.einsum('k,kij->ij',coordinates,basis),stationary)
    print('RESULT',label,result.message,'norm',np.linalg.norm(coordinates),'ineq',min(cached(result.x)[0][1:]),'metrics',np.asarray(engine.metrics(np.r_[coordinates,stationary.amplitudes])).tolist(),flush=True)
    Path(f'inverse_{label}.json').write_text(json.dumps(artifact(interaction,stationary.amplitudes)))
    np.savez(f'inverse_{label}.npz',variables=np.r_[coordinates,stationary.amplitudes])
    return coordinates

if __name__=='__main__':
    for number in [0,9]:
        design(np.load(f'kinematic{number}.npz')['variables'],str(number))
