import os

os.environ['OPENBLAS_NUM_THREADS']='1'

import json
import time
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED

import numpy as np

from cumulative import Cumulative
from optimize import OUTPUT,response,discrepancies,validate_design


def descend(pattern):
    model=Cumulative()
    model.sigma=20
    for iteration in range(24):
        proposed,loss,observed,previous=model.search(pattern,96)
        if np.array_equal(proposed,pattern):
            break
        pattern=proposed
    fitness=loss
    best_pattern=pattern.copy()
    metrics=discrepancies(model.config,observed,model.target)
    best_error=metrics['relative_rmse']
    polished=pattern.copy()
    for strength in [4,0]:
        model.sigma=strength
        for iteration in range(8):
            proposed,loss,observed,previous=model.search(polished,96)
            current=discrepancies(model.config,observed,model.target)
            if current['relative_rmse']<best_error:
                best_error=current['relative_rmse']
                metrics=current
                best_pattern=proposed.copy()
            if np.array_equal(proposed,polished):
                break
            polished=proposed
    return fitness,pattern,metrics,best_pattern


if __name__=='__main__':
    model=Cumulative()
    model.sigma=20
    random=np.random.default_rng(911)
    coordinates=np.array(model.config['candidates'])
    population=[]
    best=1e9
    for source in list(OUTPUT.glob('cumulative_best_*.json'))+[OUTPUT/f'evolve_best_{seed}.json' for seed in [601,602,603]]:
        pattern=np.asarray(json.loads(source.read_text())['pattern'])
        observed=response(model.config,pattern)
        fitness=np.mean(model.residual(observed)**2)
        population.append((fitness,pattern))
        best=min(best,discrepancies(model.config,observed,model.target)['relative_rmse'])
    print('INITIAL',len(population),best,flush=True)
    start=time.time()
    used=set()
    def offspring():
        population.sort(key=lambda item:item[0])
        for attempt in range(1000):
            parent=min(int(random.exponential(8)),len(population)-1)
            pattern=population[parent][1].copy()
            if random.random()<.5:
                other=population[random.integers(len(population))][1]
                center=coordinates[random.integers(144)]
                mask=np.sum((coordinates-center)**2,axis=1)<random.uniform(5,70)
                pattern[mask]=other[mask]
            count=int(random.choice([1,2,3,4,6,8,12]))
            occupied=np.flatnonzero(pattern)
            empty=np.flatnonzero(1-pattern)
            pattern[random.choice(occupied,count,False)]=0
            pattern[random.choice(empty,count,False)]=1
            excess=int(pattern.sum()-54)
            if excess>0:
                pattern[random.choice(np.flatnonzero(pattern),excess,False)]=0
            elif excess<0:
                pattern[random.choice(np.flatnonzero(1-pattern),-excess,False)]=1
            if pattern.tobytes() in used:
                continue
            try:validate_design(model.config,pattern)
            except ValueError:continue
            used.add(pattern.tobytes())
            return pattern
        return population[0][1].copy()
    with ProcessPoolExecutor(max_workers=56) as executor:
        pending={executor.submit(descend,offspring()) for repeat in range(56)}
        completed=0
        while pending:
            finished,pending=wait(pending,return_when=FIRST_COMPLETED)
            for future in finished:
                fitness,pattern,metrics,polished=future.result()
                completed+=1
                if not any(np.array_equal(pattern,item[1]) for item in population):
                    population.append((fitness,pattern))
                population.sort(key=lambda item:item[0])
                population=population[:60]
                print('RESULT',completed,'elapsed',round(time.time()-start,1),'fitness',fitness,'best_fitness',population[0][0],'error',metrics['relative_rmse'],'best',best,flush=True)
                if metrics['relative_rmse']<best:
                    best=metrics['relative_rmse']
                    (OUTPUT/'cdf_evolve_best.json').write_text(json.dumps({'pattern':polished.tolist()}))
                    print('BEST',metrics,flush=True)
                if metrics['core_score']>=.96 and metrics['worst_family_score']>=.94:
                    (OUTPUT/'enumeration_found.json').write_text(json.dumps({'pattern':polished.tolist()}))
                    (OUTPUT/'design.json').write_text(json.dumps({'pattern':polished.tolist()}))
                    os.chmod(OUTPUT/'design.json',0o444)
                    for task in pending:task.cancel()
                    raise SystemExit(0)
                if time.time()-start<420:
                    pending.add(executor.submit(descend,offspring()))
