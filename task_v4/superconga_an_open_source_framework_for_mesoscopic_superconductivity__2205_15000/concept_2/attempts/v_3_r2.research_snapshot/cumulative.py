import os

os.environ['OPENBLAS_NUM_THREADS']='1'

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path

import numpy as np

from discrete import Discrete
from optimize import OUTPUT,response,discrepancies,validate_design


class Cumulative(Discrete):
    def residual(self,observed):
        residual=(observed-self.target)/self.scale
        if not self.sigma:
            return residual
        cumulative=np.cumsum(residual,axis=-1)/np.sqrt(residual.shape[-1])
        return np.concatenate([cumulative,residual/self.sigma],axis=-1)


def descend(job):
    seed,pattern=job
    model=Cumulative()
    best=np.inf
    best_pattern=pattern
    start=time.time()
    for weight in [20,10,4,2,0]:
        model.sigma=weight
        for iteration in range(30):
            proposed,loss,observed,previous=model.search(pattern,96)
            metrics=discrepancies(model.config,observed,model.target)
            if metrics['relative_rmse']<best:
                best=metrics['relative_rmse']
                best_pattern=proposed.copy()
                (OUTPUT/f'cumulative_best_{seed}.json').write_text(json.dumps({'pattern':proposed.tolist()}))
            if metrics['core_score']>=.96 and metrics['worst_family_score']>=.94:
                (OUTPUT/'enumeration_found.json').write_text(json.dumps({'pattern':proposed.tolist()}))
                (OUTPUT/'design.json').write_text(json.dumps({'pattern':proposed.tolist()}))
                os.chmod(OUTPUT/'design.json',0o444)
                return seed,best,time.time()-start
            if np.array_equal(pattern,proposed):
                break
            pattern=proposed
    return seed,best,time.time()-start


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    arguments=parser.parse_args()
    model=Cumulative()
    random=np.random.default_rng(888)
    if arguments.check:
        while True:
            truth=np.zeros(144,dtype=int);truth[random.choice(144,54,replace=False)]=1
            try:validate_design(model.config,truth);break
            except ValueError:pass
        model.target=response(model.config,truth)
        model.scale=np.maximum(np.sqrt(np.mean(model.target**2,axis=2,keepdims=True)),.02)
        while True:
            pattern=truth.copy();pattern[random.choice(np.flatnonzero(truth),2,False)]=0;pattern[random.choice(np.flatnonzero(1-truth),2,False)]=1
            try:validate_design(model.config,pattern);break
            except ValueError:pass
        for weight in [20,10,4,2,0]:
            model.sigma=weight
            for iteration in range(20):
                proposed,loss,observed,previous=model.search(pattern,128)
                print(weight,iteration,loss,'distance',sum(proposed!=truth),flush=True)
                if np.array_equal(pattern,proposed):break
                pattern=proposed
    else:
        patterns=[]
        for source in ['evolve_best_601.json','evolve_best_602.json','evolve_best_603.json','discrete_best_103.json']:
            original=np.array(json.loads((OUTPUT/source).read_text())['pattern'])
            patterns.append(original)
            for repeat in range(5):
                while True:
                    pattern=original.copy()
                    count=random.integers(2,9)
                    pattern[random.choice(np.flatnonzero(original),count,False)]=0
                    pattern[random.choice(np.flatnonzero(1-original),count,False)]=1
                    try:validate_design(model.config,pattern);break
                    except ValueError:pass
                patterns.append(pattern)
        with ProcessPoolExecutor(max_workers=16) as executor:
            futures=[executor.submit(descend,(800+index,pattern)) for index,pattern in enumerate(patterns)]
            for future in as_completed(futures):
                print('RESULT',future.result(),flush=True)
