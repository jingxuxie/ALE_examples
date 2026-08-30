import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import time
import sys
import numpy as np
from scipy.optimize import minimize
from gradient_search import Objective
from search import OUT,evaluate,save

random = np.random.default_rng(int(sys.argv[1]))
started = time.time()

def main():
    best=10
    archive=[]
    for restart in range(20000):
        if (OUT/'witness.json').exists() or (OUT/'STOP_COHERENT').exists():
            return
        if not archive or random.random()<.5:
            offsets=random.integers(0,16,size=16)
            durations=random.integers(3,14,size=16)
            fields=np.where((np.arange(16)[:,None]-offsets[None])%16<durations[None],1.,-1.)
        else:
            fields=archive[int(random.integers(min(24,len(archive))))][1].copy()
            for change in range(int(random.integers(1,9))):
                site=int(random.integers(16))
                if random.random()<.5:
                    fields[:,site]=np.roll(fields[:,site],int(random.integers(1,16)))
                else:
                    begin=int(random.integers(16))
                    duration=int(random.integers(3,14))
                    fields[:,site]=np.where((np.arange(16)-begin)%16<duration,1.,-1.)
        if restart%3==0:
            path=[(.75,chemical) for chemical in [0.,.3,.6,.8,1.]]
        elif restart%3==1:
            path=[(beta,1.) for beta in [1.3,1.05,.9,.8,.75]]
        else:
            path=[(.75,1.)]
        for beta,chemical in path:
            objective=Objective(beta,both=False)
            objective.fugacities=[np.exp(-beta*chemical)]
            result=minimize(objective,fields.ravel(),jac=True,method='L-BFGS-B',bounds=[(-1,1)]*256,
                            options={'maxiter':500,'ftol':1e-13,'gtol':1e-8,'maxls':30})
            fields=result.x.reshape(16,16)
        rounded=np.where(fields>0,1,-1)
        score=Objective(.75,both=False)(rounded.ravel())[0]
        weight=evaluate(rounded)[0]
        if score<best:
            best=score
            save(rounded,'coherent_best_'+sys.argv[1]+'.json')
            print(f'{time.time()-started:.2f}s restart={restart} best={score:.12g} weight={weight:.12g}',flush=True)
        if weight < -1e-5:
            save(rounded)
            print('FOUND',flush=True)
            return
        if all(abs(score-previous[0])>1e-7 for previous in archive):
            archive.append((score,fields.copy()))
            archive.sort(key=lambda entry:entry[0])
            archive=archive[:64]
        if restart%50==0:
            print(f'{time.time()-started:.2f}s restart={restart} score={score:.12g} archive={len(archive)}',flush=True)

if __name__=='__main__':
    main()
