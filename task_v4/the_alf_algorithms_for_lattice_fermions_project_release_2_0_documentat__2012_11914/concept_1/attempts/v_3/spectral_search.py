import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import json
import sys
import time
import numpy as np
from scipy.optimize import minimize
from search import OUT,COUPLING,PROPAGATOR,products,evaluate,save

random=np.random.default_rng(int(sys.argv[1]))
started=time.time()

class Found(Exception):
    pass

def check(flat):
    rounded=np.where(flat.reshape(16,16)>0,1,-1)
    weight=evaluate(rounded)[0]
    if weight < -1e-5:
        save(rounded)
        print('FOUND',weight,flush=True)
        raise Found

def objective(flat):
    fields=flat.reshape(16,16)
    matrices=PROPAGATOR[None]*np.exp(COUPLING*fields[:,None,:])
    product=np.eye(16)
    prefixes=[]
    for matrix in matrices:
        prefixes.append(product)
        product=matrix@product
    eigenvalues,vectors=np.linalg.eig(product)
    inverse=np.linalg.inv(vectors)
    scores=eigenvalues.real+3*np.abs(eigenvalues.imag)
    selected=np.argmin(scores)
    coefficient=1-3j*np.sign(eigenvalues[selected].imag)
    row=(coefficient*np.outer(vectors[:,selected],inverse[selected])).real
    gradient=np.empty((16,16))
    for time_index in range(15,-1,-1):
        row=row@matrices[time_index]
        gradient[time_index]=COUPLING*np.einsum('ij,ji->i',prefixes[time_index],row)
    return scores[selected],gradient.ravel()

def main():
    best=0
    archive=[]
    for restart in range(20000):
        if (OUT/'witness.json').exists() or (OUT/'STOP_SPECTRAL').exists():
            return
        if not archive or random.random()<.2:
            fields=np.array(json.loads((OUT/'structured_best.json').read_text())['fields'],dtype=float)
        else:
            fields=archive[int(random.integers(min(16,len(archive))))][1].copy()
        if restart:
            candidates=np.repeat(fields[None],128,axis=0)
            for index in range(len(candidates)):
                if random.random()<.5:
                    positions=random.choice(256,size=int(random.integers(1,30)),replace=False)
                    candidates[index].ravel()[positions]*=-1
                else:
                    for change in range(int(random.integers(1,6))):
                        site=int(random.integers(16))
                        candidates[index,:,site]=np.roll(candidates[index,:,site],int(random.choice([-2,-1,1,2])))
            eigenvalues=np.linalg.eigvals(products(candidates))
            scores=np.min(eigenvalues.real+3*np.abs(eigenvalues.imag),axis=1)
            legal=np.flatnonzero(scores<-.01)
            if not len(legal):
                continue
            fields=candidates[random.choice(legal)]
        result=minimize(objective,fields.ravel(),jac=True,callback=check,method='L-BFGS-B',bounds=[(-1,1)]*256,
                        options={'maxiter':500,'ftol':1e-13,'gtol':1e-8,'maxls':30})
        fields=result.x.reshape(16,16)
        rounded=np.where(fields>0,1,-1)
        check(rounded.ravel())
        score=objective(rounded.ravel())[0]
        if score<best:
            best=score
            save(rounded,'spectral_best_'+sys.argv[1]+'.json')
            print(f'{time.time()-started:.2f}s restart={restart} best={score:.12g} continuous={result.fun:.12g}',flush=True)
        if all(abs(score-previous[0])>1e-7 for previous in archive):
            archive.append((score,fields.copy()))
            archive.sort(key=lambda entry:entry[0])
            archive=archive[:64]
        if restart%50==0:
            print(f'{time.time()-started:.2f}s restart={restart} score={score:.12g} archive={len(archive)}',flush=True)

if __name__=='__main__':
    try:
        main()
    except Found:
        pass
