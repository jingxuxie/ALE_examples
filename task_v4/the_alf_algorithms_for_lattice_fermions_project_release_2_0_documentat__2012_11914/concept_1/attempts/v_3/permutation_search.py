import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import sys
import json
import time
import itertools
import numpy as np
from scipy.optimize import minimize
from gradient_search import Objective
from search import OUT,BETA,products,save

random=np.random.default_rng(int(sys.argv[1]))
started=time.time()
pairs=np.array(list(itertools.combinations(range(16),2)))
hybrid=len(sys.argv)>2

def evaluate(fields):
    eigenvalues=np.linalg.eigvals(products(fields))
    radii=np.abs(eigenvalues)
    scores=np.ones(len(eigenvalues))
    full=np.ones(len(eigenvalues))
    for fugacity in [np.exp(BETA),np.exp(-BETA)]:
        scores=np.prod((1+fugacity*eigenvalues)/(1+fugacity*radii),axis=1).real
        full*=scores
    return scores,full

def main():
    best=10
    archive=[]
    for restart in range(50000):
        if (OUT/'witness.json').exists() or (OUT/'STOP_PERMUTATION').exists():
            return
        if restart%10==0 or not archive:
            filename=['critical_best_698.json','structured_best.json','single_best_921.json','quotient_best_815.json'][(restart//10)%4]
            fields=np.array(json.loads((OUT/filename).read_text())['fields'],dtype=np.int8)
        else:
            fields=archive[int(random.integers(min(12,len(archive))))][1].copy()
        if restart:
            for swap in range(int(random.integers(1,8))):
                sites=random.choice(16,size=2,replace=False)
                if hybrid and random.random()<.5:
                    fields[sites]=fields[sites[::-1]]
                else:
                    fields[:,sites]=fields[:,sites[::-1]]
        current=evaluate(fields)[0][0]
        for iteration in range(100):
            neighbors=np.repeat(fields[None],len(pairs)*(2 if hybrid else 1),axis=0)
            for index,pair in enumerate(pairs):
                neighbors[index][:,pair]=neighbors[index][:,pair[::-1]]
                if hybrid:
                    neighbors[len(pairs)+index][pair]=neighbors[len(pairs)+index][pair[::-1]]
            values,weights=evaluate(neighbors)
            negatives=np.flatnonzero(weights<-1e-7)
            if len(negatives):
                save(neighbors[negatives[0]])
                print('FOUND',weights[negatives[0]],flush=True)
                return
            selected=np.argmin(values)
            if values[selected]>=current-1e-10:
                break
            current=values[selected]
            fields=neighbors[selected].copy()
        if hybrid and current<.3:
            result=minimize(Objective(.75,both=False),fields.ravel().astype(float),jac=True,method='L-BFGS-B',bounds=[(-1,1)]*256,
                            options={'maxiter':400,'ftol':1e-13,'gtol':1e-8})
            fields=np.where(result.x.reshape(16,16)>0,1,-1).astype(np.int8)
            values,weights=evaluate(fields)
            current=values[0]
            if weights[0]<-1e-7:
                save(fields)
                print('FOUND',weights[0],flush=True)
                return
        if current<best:
            best=current
            save(fields,'permutation_best_'+sys.argv[1]+'.json')
            print(f'{time.time()-started:.2f}s restart={restart} best={current:.12g}',flush=True)
        if all(abs(current-previous[0])>1e-8 for previous in archive):
            archive.append((current,fields.copy()))
            archive.sort(key=lambda entry:entry[0])
            archive=archive[:64]
        if restart%100==0:
            print(f'{time.time()-started:.2f}s restart={restart} value={current:.12g} archive={len(archive)}',flush=True)

if __name__=='__main__':
    main()
