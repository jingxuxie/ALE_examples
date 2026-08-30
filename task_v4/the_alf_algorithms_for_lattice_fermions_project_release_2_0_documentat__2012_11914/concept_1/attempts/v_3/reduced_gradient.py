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
from blocks_search import mapping, kinetic

random = np.random.default_rng(int(sys.argv[1]))
started = time.time()

def main():
    best = 10
    archive = []
    for restart in range(20000):
        if (OUT/'witness.json').exists() or (OUT/'STOP_REDUCED').exists():
            return
        if not archive or random.random() < .3:
            fields = random.choice([-1,1],size=(16,4)).astype(float)
        else:
            fields = archive[int(random.integers(min(16,len(archive))))][1].copy()
            if random.random() < .5:
                for site in random.choice(4,size=int(random.integers(1,5)),replace=False):
                    fields[:,site] = np.roll(fields[:,site],int(random.integers(1,16)))
            else:
                fields *= random.choice([-1,1],size=fields.shape,p=[.2,.8])
        if restart == 0:
            fields = np.array(json.loads((OUT/'structured_best.json').read_text())['fields'],dtype=float)[:,:4]
        scales = [1.0] if restart%3 else [2.0,1.6,1.3,1.15,1.05,1.0]
        for scale in scales:
            objective = Objective(.75,both=False,kinetic=kinetic,coupling_scale=scale)
            result = minimize(objective,fields.ravel(),jac=True,method='L-BFGS-B',bounds=[(-1,1)]*64,
                              options={'maxiter':500,'ftol':1e-13,'gtol':1e-8,'maxls':30})
            fields = result.x.reshape(16,4)
        rounded = np.where(fields>0,1,-1)
        full = rounded[:,mapping]
        score = Objective(.75,both=False,kinetic=kinetic)(rounded.ravel())[0]
        weight = evaluate(full)[0]
        if score < best:
            best = score
            save(full,'reduced_best.json')
            print(f'{time.time()-started:.2f}s restart={restart} best={score:.12g} weight={weight:.12g} continuous={result.fun:.12g}',flush=True)
        if weight < -1e-5:
            save(full)
            print('FOUND',flush=True)
            return
        if all(abs(score-previous[0])>1e-8 for previous in archive):
            archive.append((score,fields.copy()))
            archive.sort(key=lambda entry:entry[0])
            archive=archive[:64]
        if restart%100==0:
            print(f'{time.time()-started:.2f}s restart={restart} score={score:.12g} archive={len(archive)}',flush=True)

if __name__ == '__main__':
    main()
