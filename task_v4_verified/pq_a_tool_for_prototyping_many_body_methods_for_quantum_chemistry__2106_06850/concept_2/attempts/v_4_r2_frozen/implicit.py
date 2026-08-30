import search as engine
import robust_opt as full
from search import np, json, Path, time, minimize, oracle, axes, basis, free, artifact, endpoint_failures
from scipy.linalg import eigh

def optimize(initial,settings,label,maxiter=1000,trust=None):
    initial=np.asarray(initial)
    amplitudes=initial[120:138].copy()
    initial=np.r_[initial[:120], abs(float(engine.metrics(initial[:138])[2]))+1e-9]
    previous=[amplitudes]
    last=[None,None,None,None]
    count=[0]
    started=time.time()
    def cached(current):
        if last[0] is None or not np.array_equal(last[0],current):
            hamiltonian=free+np.einsum('k,kij->ij',current[:120],basis)
            energies,vectors=eigh(hamiltonian)
            right=vectors[:,0]/vectors[oracle.reference,0]
            guess=right[oracle.targets].copy()
            singles=np.einsum('k,kij->ij',guess[:9],oracle.singles)
            guess[9:]-=(singles@singles@oracle.ref)[oracle.targets[9:]]/2
            solution=oracle.solve(hamiltonian,guess,tolerance=2e-11)
            if not solution.converged:
                solution=oracle.solve(hamiltonian,previous[0],tolerance=2e-11)
            previous[0]=solution.amplitudes.copy()
            joint=np.r_[current[:120],solution.amplitudes,current[120]]
            values=np.asarray(full.outputs(joint,settings))
            derivatives=np.asarray(full.jacobian(joint,settings))
            response=np.einsum('ai,kij,j->ak',solution.inverse[oracle.targets],basis,solution.right)
            amplitude_derivatives=np.linalg.solve(solution.jacobian,-response)
            derivatives=np.c_[derivatives[:,:120]+derivatives[:,120:138]@amplitude_derivatives,derivatives[:,138]]
            last[:]=current.copy(),np.r_[values[0],values[19:]],np.r_[derivatives[:1],derivatives[19:]],joint
        return last[1:]
    def callback(current):
        count[0]+=1
        if count[0]%20==0:
            values,derivatives,joint=cached(current)
            print('ITER',label,count[0],round(time.time()-started,2),np.asarray(engine.metrics(joint[:138])).round(9).tolist(),'epi',current[120],'ineq',min(values[1:]),flush=True)
            np.savez(f'live_{label}.npz',variables=joint)
    bounds=[(-1.498*(1 if row==column else np.sqrt(2)), 1.498*(1 if row==column else np.sqrt(2))) for row in range(15) for column in range(row,15)]+[(0,1)]
    if trust is not None:
        bounds=[(max(lower,center-trust),min(upper,center+trust)) for (lower,upper),center in zip(bounds[:120],initial[:120])]+[bounds[-1]]
    result=minimize(lambda current:cached(current)[0][0],initial,jac=lambda current:cached(current)[1][0],method='SLSQP',bounds=bounds,
        constraints=[{'type':'ineq','fun':lambda current:cached(current)[0][1:],'jac':lambda current:cached(current)[1][1:]}],callback=callback,
        options={'maxiter':maxiter,'ftol':1e-11,'disp':False})
    values,derivatives,joint=cached(result.x)
    np.savez(f'implicit_{label}.npz',variables=joint)
    interaction=np.einsum('k,kij->ij',joint[:120],axes)
    hamiltonian=free+np.einsum('k,kij->ij',joint[:120],basis)
    stationary=oracle.solve(hamiltonian,joint[120:138])
    diagnostics=oracle.diagnostics(hamiltonian,stationary)
    Path(f'implicit_{label}.json').write_text(json.dumps(artifact(interaction,stationary.amplitudes)))
    summary={'success':bool(result.success),'message':result.message,'metrics':np.asarray(engine.metrics(joint[:138])).tolist(),'epi':float(joint[138]),'ineq':float(min(values[1:])), 'diagnostics':diagnostics,'failures':endpoint_failures(diagnostics)}
    Path(f'implicit_{label}.report.json').write_text(json.dumps(summary,indent=2))
    print('RESULT',label,json.dumps(summary),flush=True)
    return joint

if __name__=='__main__':
    initial=np.load('refine_0a.npz')['variables']
    current=optimize(initial,np.array([1.,0.,1.,.0001,.0202]),'min',1000,trust=.5)
    current=optimize(current,np.array([0.,1.,.095,.0001,0.]),'max',1000,trust=.5)
