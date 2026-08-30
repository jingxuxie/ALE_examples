import os

os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from gauss import GaussModel
from optimize import OUTPUT,response,discrepancies


def run(arguments):
    model=GaussModel()
    model.raw=not arguments.poles
    model.guard=True
    model.energy_scale=.01
    model.budget=.002
    random=np.random.default_rng(arguments.seed)
    if arguments.start:
        if arguments.start.endswith('.json'):
            pattern=np.asarray(json.loads(Path(arguments.start).read_text())['pattern'],dtype=float)
        else:
            pattern=np.load(arguments.start)
    else:
        pattern=np.zeros(144)
        pattern[random.choice(144,54,replace=False)]=1
    rounded=model.rounded(pattern)
    if rounded is None:
        rounded=np.zeros(144)
        rounded[np.argsort(pattern)[-54:]]=1
    dual=np.zeros(144)
    rho=arguments.rho
    best=np.inf
    start=time.time()
    for iteration in range(arguments.iterations):
        model.sigma=max(0,arguments.sigma*(1-iteration/15))
        model.last_pattern=None
        coefficient=np.sqrt(rho/144)
        def fun(current):
            return np.concatenate([model.fun(current),coefficient*(current-rounded+dual)])
        def jac(current):
            return np.concatenate([model.compute(current)[1],coefficient*np.eye(144)])
        result=least_squares(fun,np.clip(pattern,1e-8,1-1e-8),jac=jac,bounds=(0,1),max_nfev=arguments.inner,ftol=1e-7,xtol=1e-8,gtol=1e-7,x_scale='jac')
        pattern=result.x
        new_rounded=model.rounded(pattern+dual)
        if new_rounded is None:
            new_rounded=rounded.copy()
        dual+=arguments.relax*(pattern-new_rounded)
        mismatch=np.linalg.norm(pattern-new_rounded)/12
        change=np.linalg.norm(new_rounded-rounded)/12
        rounded=new_rounded
        observed=response(model.config,rounded)
        metrics=discrepancies(model.config,observed,model.target)
        print(arguments.seed,iteration,'elapsed',round(time.time()-start,1),'rho',rho,'sigma',model.sigma,'loss',sum(model.fun(pattern)**2),'primal',mismatch,'dual',change,'metrics',metrics,flush=True)
        np.save(OUTPUT/f'admm_{arguments.seed}_continuous.npy',pattern)
        (OUTPUT/f'admm_current_{arguments.seed}.json').write_text(json.dumps({'pattern':rounded.tolist()}))
        if metrics['relative_rmse']<best:
            best=metrics['relative_rmse']
            (OUTPUT/f'admm_best_{arguments.seed}.json').write_text(json.dumps({'pattern':rounded.tolist()}))
        if metrics['core_score']>=.96 and metrics['worst_family_score']>=.94:
            (OUTPUT/'design.json').write_text(json.dumps({'pattern':rounded.tolist()}))
            return
        if arguments.adaptive and iteration%5==4:
            old=rho
            if mismatch>2*change:
                rho=min(rho*1.5,20)
            elif change>2*mismatch:
                rho=max(rho/1.5,.05)
            dual*=old/rho


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,default=401)
    parser.add_argument('--start')
    parser.add_argument('--rho',type=float,default=1)
    parser.add_argument('--sigma',type=float,default=4)
    parser.add_argument('--relax',type=float,default=.5)
    parser.add_argument('--iterations',type=int,default=45)
    parser.add_argument('--inner',type=int,default=30)
    parser.add_argument('--adaptive',action='store_true')
    parser.add_argument('--poles',action='store_true')
    run(parser.parse_args())
