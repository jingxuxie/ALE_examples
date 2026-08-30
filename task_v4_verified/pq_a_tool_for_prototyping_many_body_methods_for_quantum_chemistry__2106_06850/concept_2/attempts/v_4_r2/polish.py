import quiet
import search as engine
from search import np,jax,jnp,json,Path,time,minimize,oracle,axes,basis,free,artifact
import sys

def polish(filename,label,population=.0048,reference=.454,gradient=.096):
    data=json.loads(Path(filename).read_text())
    initial=np.r_[np.einsum('kij,ij->k',axes,np.array(data['pair_matrix'])),data['amplitudes']]
    settings=np.array([0.,0.,gradient,population])
    def values(current):
        result=np.array(quiet.outputs(current,settings))
        result[37]-=reference-.451
        return result
    def derivatives(current):return np.asarray(quiet.jacobian(current,settings))
    result=minimize(lambda current:np.sum((current-initial)**2),initial,jac=lambda current:2*(current-initial),method='SLSQP',
        constraints=[{'type':'eq','fun':lambda current:values(current)[1:35],'jac':lambda current:derivatives(current)[1:35]},
                     {'type':'ineq','fun':lambda current:values(current)[35:],'jac':lambda current:derivatives(current)[35:]}],
        options={'maxiter':1000,'ftol':1e-13})
    current=result.x
    matrix=np.einsum('k,kij->ij',current[:120],axes)
    stationary=oracle.solve(free+np.einsum('k,kij->ij',current[:120],basis),current[120:])
    Path(f'{label}.json').write_text(json.dumps(artifact(matrix,stationary.amplitudes),indent=2))
    np.savez(f'{label}.npz',variables=np.r_[current[:120],stationary.amplitudes])
    print('RESULT',result.message,np.asarray(engine.metrics(np.r_[current[:120],stationary.amplitudes])).tolist(),'eq',max(abs(values(current)[1:35])),'ineq',min(values(current)[35:]),flush=True)

if __name__=='__main__':
    polish('quiet_path7.json','polished')
