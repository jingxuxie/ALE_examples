import os

os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'

import json
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from optimize import Model,OUTPUT,response,discrepancies,validate_design


def evaluate(pattern):
    model=Model()
    observed=response(model.config,pattern)
    metrics=discrepancies(model.config,observed,model.target)
    return metrics,pattern


if __name__=='__main__':
    model=Model()
    coordinates=np.array(model.config['candidates'])
    patterns={}
    for width,height in [(9,6),(6,9)]:
        for column in range(2,15-width):
            for row in range(2,15-height):
                pattern=((coordinates[:,0]>=column)&(coordinates[:,0]<column+width)&(coordinates[:,1]>=row)&(coordinates[:,1]<row+height)).astype(int)
                patterns[pattern.tobytes()]=pattern
    for column in np.arange(2,14,1):
        for row in np.arange(2,14,1):
            for aspect in [.3,.5,1,2,3]:
                for angle in [0,np.pi/4]:
                    first=(coordinates[:,0]-column)*np.cos(angle)+(coordinates[:,1]-row)*np.sin(angle)
                    second=-(coordinates[:,0]-column)*np.sin(angle)+(coordinates[:,1]-row)*np.cos(angle)
                    distance=first**2*aspect+second**2/aspect
                    pattern=np.zeros(144,dtype=int)
                    pattern[np.argsort(distance)[:54]]=1
                    if pattern[65] or not pattern[34]:
                        continue
                    try:
                        validate_design(model.config,pattern)
                        patterns[pattern.tobytes()]=pattern
                    except ValueError:
                        pass
    best=1e9
    print('patterns',len(patterns),flush=True)
    start=time.time()
    with ProcessPoolExecutor(max_workers=8) as executor:
        for index,(metrics,pattern) in enumerate(executor.map(evaluate,patterns.values(),chunksize=1)):
            if metrics['relative_rmse']<best:
                best=metrics['relative_rmse']
                print(index,time.time()-start,metrics,flush=True)
                (OUTPUT/'geometry_best.json').write_text(json.dumps({'pattern':pattern.tolist()}))
            if metrics['core_score']>=.96 and metrics['worst_family_score']>=.94:
                (OUTPUT/'design.json').write_text(json.dumps({'pattern':pattern.tolist()}))
                break
