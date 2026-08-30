import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import sys
import time
import numpy as np
from scipy.optimize import minimize
from gradient_search import Objective
from search import OUT,evaluate,save

random=np.random.default_rng(int(sys.argv[1]))
started=time.time()
gray=[0,1,3,2]
labels=np.array([gray[site//4]+4*gray[site%4] for site in range(16)])
subgroups=[[0,7,9,14],[0,7],[0,7,8,15],[0,1],[0,3,5,6],[0,3,12,15],[0,1,2,3]]
mappings=[]
for subgroup in subgroups:
    representatives=np.min(labels[:,None]^np.array(subgroup)[None],axis=1)
    mappings.append(np.unique(representatives,return_inverse=True)[1])

def main():
    best=10
    archives=[[] for mapping in mappings]
    for restart in range(30000):
        if (OUT/'witness.json').exists() or (OUT/'STOP_LINEAR').exists():
            return
        mode=restart%len(mappings)
        mapping=mappings[mode]
        sites=int(mapping.max())+1
        archive=archives[mode]
        if not archive or random.random()<.4:
            offsets=random.integers(0,16,size=sites)
            durations=random.integers(3,14,size=sites)
            fields=np.where((np.arange(16)[:,None]-offsets[None])%16<durations[None],1.,-1.)
        else:
            fields=archive[int(random.integers(min(16,len(archive))))][1].copy()
            for site in random.choice(sites,size=int(random.integers(1,sites+1)),replace=False):
                if random.random()<.6:
                    fields[:,site]=np.roll(fields[:,site],int(random.integers(1,16)))
                else:
                    begin=int(random.integers(16))
                    duration=int(random.integers(3,14))
                    fields[:,site]=np.where((np.arange(16)-begin)%16<duration,1.,-1.)
        path=[(1.,1.),(.85,1.),(.75,1.)] if restart%14<7 else [(.75,1.)]
        for beta,chemical in path:
            full_objective=Objective(beta,both=bool(restart%2))
            def objective(flat):
                full=flat.reshape(16,sites)[:,mapping]
                value,gradient=full_objective(full.ravel())
                gradient=gradient.reshape(16,16)
                reduced=np.stack([gradient[:,mapping==site].sum(axis=1) for site in range(sites)],axis=1)
                return value,reduced.ravel()
            result=minimize(objective,fields.ravel(),jac=True,method='L-BFGS-B',bounds=[(-1,1)]*(16*sites),
                            options={'maxiter':500,'ftol':1e-13,'gtol':1e-8,'maxls':30})
            fields=result.x.reshape(16,sites)
        rounded=np.where(fields>0,1,-1)
        full=rounded[:,mapping]
        score=evaluate(full)[0]
        if score<best:
            best=score
            save(full,'linear_best_'+sys.argv[1]+'.json')
            print(f'{time.time()-started:.2f}s restart={restart} mode={mode} best={score:.12g}',flush=True)
        if score < -1e-5:
            save(full)
            print('FOUND',flush=True)
            return
        if all(abs(score-previous[0])>1e-7 for previous in archive):
            archive.append((score,fields.copy()))
            archive.sort(key=lambda entry:entry[0])
            archives[mode]=archive[:64]
        if restart%70==0:
            print(f'{time.time()-started:.2f}s restart={restart} mode={mode} score={score:.12g} archive={len(archive)}',flush=True)

if __name__=='__main__':
    main()
