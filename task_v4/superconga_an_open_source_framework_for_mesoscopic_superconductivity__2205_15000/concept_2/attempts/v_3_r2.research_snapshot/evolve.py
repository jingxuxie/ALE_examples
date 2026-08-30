import os

os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
from pathlib import Path

import numpy as np

from discrete import Discrete
from optimize import OUTPUT,response,discrepancies,validate_design


def descend(job):
    pattern,seed,steps,limit,sigma,weights=job
    model=Discrete()
    model.scale/=np.sqrt(weights[None,:,None])
    for smooth in ([sigma,0] if sigma else [0]):
        model.sigma=smooth
        for iteration in range(steps):
            new_pattern,loss,observed,previous=model.search(pattern,limit)
            if np.array_equal(new_pattern,pattern):
                break
            pattern=new_pattern
    metrics=discrepancies(model.config,observed,model.target)
    true_scale=np.maximum(np.sqrt(np.mean(model.target**2,axis=2,keepdims=True)),.02)
    metrics['probe_errors']=np.mean(((observed-model.target)/true_scale)**2,axis=(0,2)).tolist()
    return pattern,metrics


def run(arguments):
    model=Discrete()
    random=np.random.default_rng(arguments.seed)
    population=[]
    used=set()
    for name in ['discrete_best_101.json','discrete_best_102.json','discrete_best_103.json','discrete_best_104.json']:
        pattern=np.asarray(json.loads((OUTPUT/name).read_text())['pattern'])
        observed=response(model.config,pattern)
        metrics=discrepancies(model.config,observed,model.target)
        probe_errors=np.mean(((observed-model.target)/model.scale)**2,axis=(0,2))
        population.append((metrics['relative_rmse'],pattern,probe_errors))
        used.add(pattern.tobytes())
    best=min(item[0] for item in population)
    coordinates=np.array(model.config['candidates'])
    start=time.time()
    serial=0

    def offspring():
        nonlocal serial
        serial+=1
        population.sort(key=lambda item:item[0])
        weights=np.ones(8)
        if arguments.specialists and random.random()<.4:
            weights[:]=.15
            weights[random.choice(8,2,replace=False)]=3
        for attempt in range(100):
            parent_index=min(int(random.exponential(arguments.selection)),len(population)-1)
            ranked=population
            if arguments.specialists and random.random()<.6:
                focus=random.exponential(1,size=8)**2
                ranked=sorted(population,key=lambda item:np.dot(item[2],focus))
            pattern=ranked[parent_index][1].copy()
            if len(population)>4 and random.random()<.6:
                other=population[random.integers(len(population))][1]
                if random.random()<.5:
                    angle=random.uniform(0,2*np.pi)
                    projection=coordinates[:,0]*np.cos(angle)+coordinates[:,1]*np.sin(angle)
                    mask=projection>np.quantile(projection,random.uniform(.2,.8))
                else:
                    center=coordinates[random.integers(144)]
                    mask=np.sum((coordinates-center)**2,axis=1)<random.uniform(4,49)
                pattern[mask]=other[mask]
            count=int(random.choice([1,2,3,4,6,8,12],p=[.12,.2,.2,.18,.14,.1,.06]))
            occupied=np.flatnonzero(pattern)
            empty=np.flatnonzero(1-pattern)
            pattern[random.choice(occupied,min(count,len(occupied)),replace=False)]=0
            pattern[random.choice(empty,min(count,len(empty)),replace=False)]=1
            excess=int(pattern.sum()-54)
            if excess>0:
                pattern[random.choice(np.flatnonzero(pattern),excess,replace=False)]=0
            elif excess<0:
                pattern[random.choice(np.flatnonzero(1-pattern),-excess,replace=False)]=1
            if pattern.tobytes() in used:
                continue
            try:
                validate_design(model.config,pattern)
            except ValueError:
                continue
            used.add(pattern.tobytes())
            return pattern,serial,arguments.steps,arguments.limit,(3 if random.random()<.15 else 0),weights
        pattern=population[0][1].copy()
        return pattern,serial,arguments.steps,arguments.limit,0,weights

    with ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        pending={executor.submit(descend,offspring()) for index in range(arguments.workers)}
        completed=0
        while pending:
            finished,pending=wait(pending,return_when=FIRST_COMPLETED)
            for future in finished:
                pattern,metrics=future.result()
                completed+=1
                score=metrics['relative_rmse']
                print('RESULT',completed,'elapsed',round(time.time()-start,1),'error',score,'best',best,flush=True)
                if not any(np.array_equal(pattern,item[1]) for item in population):
                    population.append((score,pattern,np.array(metrics['probe_errors'])))
                population.sort(key=lambda item:item[0])
                if arguments.specialists:
                    retained={item[1].tobytes():item for item in population[:arguments.population]}
                    for probe in range(8):
                        for item in sorted(population,key=lambda item:item[2][probe])[:3]:
                            retained[item[1].tobytes()]=item
                    population=list(retained.values())
                else:
                    population=population[:arguments.population]
                if score<best:
                    best=score
                    print('BEST',metrics,flush=True)
                    (OUTPUT/f'evolve_best_{arguments.seed}.json').write_text(json.dumps({'pattern':pattern.tolist()}))
                    (OUTPUT/'design.json').write_text(json.dumps({'pattern':pattern.tolist()}))
                if completed%20==0:
                    np.savez(OUTPUT/f'evolve_population_{arguments.seed}.npz',patterns=np.array([item[1] for item in population]),errors=np.array([item[0] for item in population]))
                if metrics['core_score']>=.96 and metrics['worst_family_score']>=.94:
                    for task in pending:
                        task.cancel()
                    return
                if time.time()-start<arguments.seconds:
                    pending.add(executor.submit(descend,offspring()))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,default=601)
    parser.add_argument('--workers',type=int,default=12)
    parser.add_argument('--population',type=int,default=40)
    parser.add_argument('--steps',type=int,default=20)
    parser.add_argument('--limit',type=int,default=96)
    parser.add_argument('--selection',type=float,default=8)
    parser.add_argument('--seconds',type=float,default=1500)
    parser.add_argument('--specialists',action='store_true')
    run(parser.parse_args())
