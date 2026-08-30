import finite
import search as engine
from search import np,json,Path,time,minimize,oracle,axes,basis,free,artifact
from scipy.linalg import eigh

def optimize(initial,label,maxiter=1000,trust=.15):
    initial=initial[:120]
    last=[None,None,None,None]
    count=[0]
    started=time.time()
    def cached(current):
        if last[0] is None or not np.array_equal(last[0],current):
            hamiltonian=free+np.einsum('k,kij->ij',current,basis)
            energies,vectors=eigh(hamiltonian)
            right=vectors[:,0]/vectors[oracle.reference,0]
            guess=right[oracle.targets].copy()
            singles=np.einsum('k,kij->ij',guess[:9],oracle.singles)
            guess[9:]-=(singles@singles@oracle.ref)[oracle.targets[9:]]/2
            solution=oracle.solve(hamiltonian,guess,tolerance=2e-11)
            joint=np.r_[current,solution.amplitudes]
            values=np.asarray(finite.outputs(joint))
            derivatives=np.asarray(finite.jacobian(joint))
            response=np.einsum('ai,kij,j->ak',solution.inverse[oracle.targets],basis,solution.right)
            amplitude_derivatives=np.linalg.solve(solution.jacobian,-response)
            derivatives=derivatives[:,:120]+derivatives[:,120:]@amplitude_derivatives
            last[:]=current.copy(),np.r_[values[0],values[19:]],np.r_[derivatives[:1],derivatives[19:]],joint
        return last[1:]
    def callback(current):
        count[0]+=1
        if count[0]%25==0:
            values,derivatives,joint=cached(current)
            print('ITER',label,count[0],round(time.time()-started,2),'objective',-values[0]/10,'ineq',min(values[1:]),np.asarray(engine.metrics(joint)).round(9).tolist(),flush=True)
            np.savez(f'finite_implicit_live{label}.npz',variables=joint)
    bounds=[(-1.498*(1 if row==column else np.sqrt(2)), 1.498*(1 if row==column else np.sqrt(2))) for row in range(15) for column in range(row,15)]
    if trust is not None:
        bounds=[(max(lower,center-trust),min(upper,center+trust)) for (lower,upper),center in zip(bounds,initial)]
    result=minimize(lambda current:cached(current)[0][0],initial,jac=lambda current:cached(current)[1][0],method='SLSQP',bounds=bounds,
        constraints=[{'type':'ineq','fun':lambda current:cached(current)[0][1:],'jac':lambda current:cached(current)[1][1:]}],callback=callback,
        options={'maxiter':maxiter,'ftol':1e-11,'disp':False})
    values,derivatives,joint=cached(result.x)
    matrix=np.einsum('k,kij->ij',joint[:120],axes)
    Path(f'finite_implicit_{label}.json').write_text(json.dumps(artifact(matrix,joint[120:])))
    np.savez(f'finite_implicit_{label}.npz',variables=joint)
    print('RESULT',label,result.message,np.asarray(engine.metrics(joint)).tolist(),'ineq',min(values[1:]),flush=True)
    return joint

if __name__=='__main__':
    current=np.load('polished_best.npz')['variables']
    for number in range(8):
        candidate=optimize(current,str(number),700,.08)
        values=np.asarray(finite.outputs(candidate))
        if max(abs(values[1:19]))<1e-8 and min(values[19:])>-.001:
            current=candidate
