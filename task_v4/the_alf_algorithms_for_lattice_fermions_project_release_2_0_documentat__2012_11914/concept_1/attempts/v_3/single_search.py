import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import json
import time
import sys
import numpy as np
from scipy.optimize import minimize
from gradient_search import Objective
from search import OUT, evaluate, save

random = np.random.default_rng(int(sys.argv[1]))
started = time.time()

def main():
    best = 10
    archive = []
    for restart in range(20000):
        if (OUT/'witness.json').exists() or (OUT/'STOP_SINGLE').exists():
            return
        if not archive or restart%4==0:
            filename = ['structured_best.json','reduced_best.json','gradient_best_619.json','angle_best.json'][(restart//4)%4]
            fields = np.array(json.loads((OUT/filename).read_text())['fields'],dtype=float)
        else:
            fields = archive[int(random.integers(min(16,len(archive))))][1].copy()
        if restart:
            for change in range(int(random.integers(1,13))):
                site = int(random.integers(16))
                fields[:,site] = np.roll(fields[:,site],int(random.choice([-3,-2,-1,1,2,3])))
            if random.random()<.3:
                fields *= random.choice([-1,1],size=fields.shape,p=[.15,.85])
        path = [(.75,1.0)]
        if restart%3==0:
            path = [(.75,scale) for scale in [1.6,1.35,1.15,1.05,1.0]]
        elif restart%3==1:
            path = [(beta,1.0) for beta in [1.1,.95,.85,.8,.775,.75]]
        for beta,scale in path:
            objective = Objective(beta,both=False,coupling_scale=scale)
            result = minimize(objective,fields.ravel(),jac=True,method='L-BFGS-B',bounds=[(-1,1)]*256,
                              options={'maxiter':500,'ftol':1e-13,'gtol':1e-8,'maxls':30})
            fields = result.x.reshape(16,16)
        rounded = np.where(fields>0,1,-1)
        score = Objective(.75,both=False)(rounded.ravel())[0]
        weight = evaluate(rounded)[0]
        if score < best:
            best = score
            save(rounded,'single_best_'+sys.argv[1]+'.json')
            print(f'{time.time()-started:.2f}s restart={restart} best={score:.12g} weight={weight:.12g} continuous={result.fun:.12g}',flush=True)
        if weight < -1e-5:
            save(rounded)
            print('FOUND',flush=True)
            return
        if all(abs(score-previous[0])>1e-7 for previous in archive):
            archive.append((score,fields.copy()))
            archive.sort(key=lambda entry:entry[0])
            archive=archive[:64]
        if restart%20==0:
            print(f'{time.time()-started:.2f}s restart={restart} score={score:.12g} archive={len(archive)}',flush=True)

if __name__ == '__main__':
    main()
