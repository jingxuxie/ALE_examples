import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import json
import time
import sys
import numpy as np
from scipy.optimize import minimize
from gradient_search import Objective
from search import OUT,evaluate,save

random=np.random.default_rng(int(sys.argv[1]))
started=time.time()
mappings=[np.array([4*(site//4%2)+site%4 for site in range(16)]),
          np.array([4*(site//4%2)+(site%4-2*(site//8))%4 for site in range(16)]),
          np.array([4*(site//4%2)+(site//4+site%4)%4 for site in range(16)])]

def main():
    best=10
    archives=[[] for mapping in mappings]
    for restart in range(20000):
        if (OUT/'witness.json').exists() or (OUT/'STOP_QUOTIENT').exists():
            return
        mode=restart%len(mappings)
        mapping=mappings[mode]
        archive=archives[mode]
        if not archive or random.random()<.4:
            offsets=random.integers(0,16,size=8)
            durations=random.integers(3,14,size=8)
            fields=np.where((np.arange(16)[:,None]-offsets[None])%16<durations[None],1.,-1.)
        else:
            fields=archive[int(random.integers(min(16,len(archive))))][1].copy()
            for site in random.choice(8,size=int(random.integers(1,7)),replace=False):
                if random.random()<.5:
                    fields[:,site]=np.roll(fields[:,site],int(random.integers(1,16)))
                else:
                    begin=int(random.integers(16))
                    duration=int(random.integers(3,14))
                    fields[:,site]=np.where((np.arange(16)-begin)%16<duration,1.,-1.)
        if restart%9<3:
            path=[(.75,chemical) for chemical in [0.,.4,.7,1.]]
        elif restart%9<6:
            path=[(beta,1.) for beta in [1.2,1.,.85,.8,.75]]
        else:
            path=[(.75,1.)]
        for beta,chemical in path:
            full_objective=Objective(beta,both=False)
            full_objective.fugacities=[np.exp(-beta*chemical)]
            def objective(flat):
                full=flat.reshape(16,8)[:,mapping]
                value,gradient=full_objective(full.ravel())
                gradient=gradient.reshape(16,16)
                reduced=np.stack([gradient[:,mapping==site].sum(axis=1) for site in range(8)],axis=1)
                return value,reduced.ravel()
            result=minimize(objective,fields.ravel(),jac=True,method='L-BFGS-B',bounds=[(-1,1)]*128,
                            options={'maxiter':500,'ftol':1e-13,'gtol':1e-8,'maxls':30})
            fields=result.x.reshape(16,8)
        rounded=np.where(fields>0,1,-1)
        full=rounded[:,mapping]
        score=Objective(.75,both=False)(full.ravel())[0]
        weight=evaluate(full)[0]
        if score<best:
            best=score
            save(full,'quotient_best_'+sys.argv[1]+'.json')
            print(f'{time.time()-started:.2f}s restart={restart} mode={mode} best={score:.12g} weight={weight:.12g}',flush=True)
        if weight < -1e-5:
            save(full)
            print('FOUND',flush=True)
            return
        if all(abs(score-previous[0])>1e-7 for previous in archive):
            archive.append((score,fields.copy()))
            archive.sort(key=lambda entry:entry[0])
            archives[mode]=archive[:64]
        if restart%50==0:
            print(f'{time.time()-started:.2f}s restart={restart} mode={mode} score={score:.12g} archive={len(archive)}',flush=True)

if __name__=='__main__':
    main()
