import os
os.environ['SPARSE']='1'
os.environ['KEEPALL']='1'
os.environ['TEMPERATURE']='.001'
import json
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from optimize import Problem, PARTICIPANT
from search_nominal import canonical

def main():
    rng=np.random.default_rng(2579)
    baseline=json.loads((PARTICIPANT/'baseline/champion.json').read_text())
    base=np.array(baseline['probabilities'])
    directory=Path('robust_search');directory.mkdir(exist_ok=True)
    source=Path('route_best.json') if Path('route_best.json').exists() else Path('robust_best.json')
    best_data=json.loads(source.read_text()) if source.exists() else baseline
    best=Problem(best_data).evaluate(np.array(best_data['probabilities']))[0].min()
    tried=set()
    tried_syndromes=set()
    started=time.time()
    for attempt in range(500):
        sources=sorted(Path('nominal_search').glob('*.json'),key=lambda filename:float(filename.stem.split('_')[1]),reverse=True)
        sources=[source for source in sources if str(source) not in tried]
        diverse=[]
        for source in sources:
            data=json.loads(source.read_text())
            if canonical(data['syndrome']) not in tried_syndromes:
                diverse.append(source)
        if diverse:sources=diverse
        if (attempt%3==0 or diverse) and sources:
            source=sources[0];tried.add(str(source));data=json.loads(source.read_text())
            tried_syndromes.add(canonical(data['syndrome']))
        else:
            data=best_data.copy()
            data['probabilities']=np.clip(np.array(data['probabilities'])+rng.normal(0,(attempt%8)*.005,39),.02,.14).tolist()
        problem=Problem(data)
        if not ((attempt%3==0 or diverse) and sources):
            problem.physical=Problem(best_data).physical
        problem.verbose=False
        problem.save_path=directory/f'candidate_{attempt}.json'
        probabilities=np.array(data['probabilities'])
        initial=problem.evaluate(probabilities)[0].min()
        variables=np.r_[probabilities*10,initial]
        result=minimize(lambda variables:-variables[39],variables,jac=lambda variables:np.r_[np.zeros(39),-1],
                        method='SLSQP',bounds=[(.2,1.4)]*39+[(-2,2)],
                        constraints={'type':'ineq','fun':problem.fun,'jac':problem.jac},
                        options={'maxiter':180,'ftol':1e-9})
        print(attempt,data['syndrome'],initial,problem.best,result.nit,problem.calls,round(time.time()-started,1),flush=True)
        if problem.best>best:
            best=problem.best
            best_data={'version':1,'probabilities':problem.best_p.tolist(),'syndrome':data['syndrome']}
            Path('robust_best.json').write_text(json.dumps(best_data,indent=2)+'\n')
            print('BEST',attempt,best,flush=True)

if __name__=='__main__':main()
