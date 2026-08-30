import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['SPARSE']='1'
os.environ['KEEPALL']='1'
os.environ['TEMPERATURE']='.0002'
import json
import time
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from optimize import Problem
from search_nominal import canonical

def main():
    known={(0,2,5,17),(0,6,17),(0,1,2,4,5,17),(1,2,4,17),(0,1,6,18),(0,2,5,6,17),(0,1,6,17)}
    files=set();attempt=0
    directory=Path('discoveries');directory.mkdir(exist_ok=True)
    best_data=json.loads(Path('witness.json').read_text())
    best=Problem(best_data).evaluate(np.array(best_data['probabilities']))[0].min()
    started=time.time()
    while time.time()-started<1400:
        paths=[path for path in Path('nominal_search').glob('*.json') if str(path) not in files]
        paths.sort(key=lambda path:-float(path.stem.split('_')[1]))
        for path in paths:
            files.add(str(path))
            data=json.loads(path.read_text());signature=canonical(data['syndrome'])
            if signature in known:continue
            known.add(signature);attempt+=1
            print('NEW',attempt,signature,path,flush=True)
            problem=Problem(data);problem.verbose=False;problem.save_path=directory/f'candidate_{attempt}.json'
            probabilities=np.array(data['probabilities'])
            initial=problem.evaluate(probabilities)[0].min()
            result=minimize(lambda variables:-variables[39],np.r_[probabilities*10,initial],jac=lambda variables:np.r_[np.zeros(39),-1],
                            method='SLSQP',bounds=[(.2,1.4)]*39+[(-3,3)],constraints={'type':'ineq','fun':problem.fun,'jac':problem.jac},
                            options={'maxiter':250,'ftol':1e-9})
            print('RESULT',attempt,initial,problem.best,result.nit,round(time.time()-started,1),flush=True)
            if problem.best>best:
                best=problem.best
                data['probabilities']=problem.best_p.tolist()
                Path('discovery_best.json').write_text(json.dumps(data,indent=2)+'\n')
                print('BEST',best,flush=True)
        time.sleep(5)

if __name__=='__main__':main()
