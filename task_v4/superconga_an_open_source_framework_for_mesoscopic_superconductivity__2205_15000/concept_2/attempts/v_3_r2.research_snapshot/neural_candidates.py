import os

os.environ['OPENBLAS_NUM_THREADS']='1'

import argparse
import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from optimize import Model,OUTPUT,validate_design,response,discrepancies


def evaluate(pattern):
    model=Model()
    return discrepancies(model.config,response(model.config,pattern),model.target),pattern


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('prior')
    parser.add_argument('--tag',default='learned')
    arguments=parser.parse_args()
    model=Model()
    prior=np.clip(np.load(arguments.prior),.001,.999)
    print('PRIOR',prior.min(),prior.max(),prior.sum(),flush=True)
    random=np.random.default_rng(1873)
    patterns={}
    rounded=model.rounded(prior)
    if rounded is not None:
        patterns[rounded.tobytes()]=rounded
    for attempt in range(10000):
        if len(patterns)>=64:
            break
        scores=np.log(prior/(1-prior))+random.gumbel(size=144)*random.uniform(.05,.7)
        pattern=np.zeros(144,dtype=int)
        pattern[np.argsort(scores)[-54:]]=1
        try:
            validate_design(model.config,pattern)
        except ValueError:
            continue
        patterns[pattern.tobytes()]=pattern
    best=1e9
    with ProcessPoolExecutor(max_workers=12) as executor:
        for metrics,pattern in executor.map(evaluate,patterns.values()):
            if metrics['relative_rmse']<best:
                best=metrics['relative_rmse']
                print('BEST',metrics,flush=True)
                (OUTPUT/f'{arguments.tag}_binary.json').write_text(json.dumps({'pattern':pattern.tolist()}))
                if metrics['core_score']>=.96 and metrics['worst_family_score']>=.94:
                    (OUTPUT/'enumeration_found.json').write_text(json.dumps({'pattern':pattern.tolist()}))
                    (OUTPUT/'design.json').write_text(json.dumps({'pattern':pattern.tolist()}))
                    os.chmod(OUTPUT/'design.json',0o444)
                    break
