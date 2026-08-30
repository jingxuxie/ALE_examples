import search as engine
from search import np, time, oracle, basis, free

rng=np.random.default_rng(619238)
rows=[]
started=time.time()
for trial in range(150000):
    coordinates=rng.normal(0,rng.uniform(.25,.63),120)
    if np.linalg.norm(coordinates)>6.95:continue
    real=engine.hf_free[0]+np.einsum('k,kij->ij',coordinates,engine.hf_real)
    if np.linalg.eigvalsh(real)[0]<.015:continue
    imag=engine.hf_free[1]+np.einsum('k,kij->ij',coordinates,engine.hf_imag)
    if np.linalg.eigvalsh(imag)[0]<.015:continue
    hamiltonian=free+np.einsum('k,kij->ij',coordinates,basis)
    result=oracle.solve(hamiltonian)
    if not result.converged or np.linalg.norm(result.amplitudes)>1.4:continue
    energies,vectors=np.linalg.eigh(hamiltonian)
    overlap=(vectors[:,0]@result.right)**2/(result.right@result.right)
    if overlap<.98 or vectors[oracle.reference,0]**2<.4:continue
    if np.linalg.cond(result.jacobian)>150:continue
    multipliers,left,_=oracle.lambda_state(result)
    if np.linalg.norm(multipliers)>1.5:continue
    density=oracle.rdm(left,result.right)
    occupations=np.linalg.eigvalsh((density+density.T)/2)
    violation=max(-occupations[0],occupations[-1]-1)
    if violation<.0001:continue
    values=[violation,result.energy-energies[0],overlap,np.linalg.norm(density-density.T)/np.sqrt(3)]
    rows.append((violation,np.r_[coordinates,result.amplitudes],values))
    rows.sort(key=lambda row:row[0],reverse=True)
    rows=rows[:150]
    np.savez('samples.npz',variables=np.array([row[1] for row in rows]),values=np.array([row[2] for row in rows]))
    print('FOUND',trial,'seconds',round(time.time()-started,1),'count',len(rows),values,flush=True)
print('DONE',time.time()-started,flush=True)
