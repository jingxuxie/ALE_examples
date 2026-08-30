import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['SPARSE']='1'
os.environ['KEEPALL']='1'
os.environ['TEMPERATURE']='.0003'
import json
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from optimize import Problem
from nominal import solve

def main():
    source=json.loads(Path('best.json').read_text())
    base=np.array(source['probabilities'])
    directory=Path('route_search');directory.mkdir(exist_ok=True)
    rng=np.random.default_rng(123711)
    best=0;started=time.time()
    for attempt in range(100):
        column=attempt%4
        probabilities=base.copy()
        horizontal=probabilities[:24].reshape(6,4)
        vertical=probabilities[24:].reshape(5,3)
        horizontal[column+1:4,2]=horizontal[column+1:4,1]
        horizontal[column+1:4,1]=.02
        vertical[3,1]=.02
        vertical[column,1]=.14
        if attempt>=4:probabilities=np.clip(probabilities+rng.normal(0,.005*(attempt%9),39),.02,.14)
        data={'version':1,'probabilities':probabilities.tolist(),'syndrome':source['syndrome']}
        problem=Problem(data);problem.physical=0;problem.verbose=False
        problem.save_path=directory/f'candidate_{attempt}.json'
        initial=problem.evaluate(probabilities)[0].min()
        result=minimize(lambda variables:-variables[39],np.r_[probabilities*10,initial],jac=lambda variables:np.r_[np.zeros(39),-1],
                        method='SLSQP',bounds=[(.2,1.4)]*39+[(-3,3)],constraints={'type':'ineq','fun':problem.fun,'jac':problem.jac},
                        options={'maxiter':200,'ftol':1e-9})
        print(attempt,column,initial,problem.best,result.nit,round(time.time()-started,1),flush=True)
        if problem.best>best:
            best=problem.best;data['probabilities']=problem.best_p.tolist()
            Path('route_best.json').write_text(json.dumps(data,indent=2)+'\n')
            print('BEST',attempt,best,flush=True)

if __name__=='__main__':main()
