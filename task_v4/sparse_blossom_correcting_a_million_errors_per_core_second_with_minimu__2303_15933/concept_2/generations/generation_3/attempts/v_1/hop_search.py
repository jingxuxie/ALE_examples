import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['SPARSE']='1'
os.environ['KEEPALL']='1'
os.environ['TEMPERATURE']='.0001'
import json
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from optimize import Problem

def main():
    data=json.loads(Path('witness.json').read_text())
    best_data=data.copy()
    best=Problem(data).evaluate(np.array(data['probabilities']))[0].min()
    directory=Path('hop_search');directory.mkdir(exist_ok=True)
    rng=np.random.default_rng(681264)
    started=time.time()
    for attempt in range(300):
        problem=Problem(best_data);problem.verbose=False;problem.physical=0
        problem.save_path=directory/f'biased_{attempt}.json'
        variables=np.r_[np.array(best_data['probabilities'])*10,best]
        strength=[.01,.03,.06,.1,.2,.4][attempt%6]
        bias=rng.normal(0,strength/np.sqrt(39),39)
        gradient=np.r_[-bias,-1]
        result=minimize(lambda variables:np.dot(gradient,variables),variables,jac=lambda variables:gradient,
                        method='SLSQP',bounds=[(.2,1.4)]*39+[(-3,3)],constraints={'type':'ineq','fun':problem.fun,'jac':problem.jac},
                        options={'maxiter':120,'ftol':1e-8})
        variables=result.x.copy()
        biased_score=problem.evaluate(variables[:39]*.1)[0].min()
        problem.save_path=directory/f'candidate_{attempt}.json'
        problem.best=-1e10;problem.last_x=None
        gradient=np.r_[np.zeros(39),-1]
        result=minimize(lambda variables:-variables[39],variables,jac=lambda variables:gradient,
                        method='SLSQP',bounds=[(.2,1.4)]*39+[(-3,3)],constraints={'type':'ineq','fun':problem.fun,'jac':problem.jac},
                        options={'maxiter':220,'ftol':1e-10})
        print(attempt,strength,biased_score,problem.best,round(time.time()-started,1),flush=True)
        if problem.best>best:
            best=problem.best
            best_data={'version':1,'probabilities':problem.best_p.tolist(),'syndrome':data['syndrome']}
            Path('hop_best.json').write_text(json.dumps(best_data,indent=2)+'\n')
            print('BEST',attempt,best,flush=True)

if __name__=='__main__':main()
