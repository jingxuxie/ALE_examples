import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import sys
import time
import json
import numpy as np
from scipy.optimize import minimize
from gradient_search import Objective
from search import OUT,KINETIC,evaluate,save

random=np.random.default_rng(int(sys.argv[1]))
started=time.time()

def objective(hopping):
    return Objective(.75,both=False,kinetic=KINETIC*hopping)

class Constraint:
    def __init__(self):
        self.previous=None
    def update(self,parameters):
        if self.previous is not None and np.array_equal(parameters,self.previous):
            return
        hopping=parameters[0]
        fields=parameters[1:]
        value,gradient=objective(hopping)(fields)
        epsilon=1e-5
        derivative=(objective(hopping+epsilon)(fields)[0]-objective(hopping-epsilon)(fields)[0])/(2*epsilon)
        self.previous=parameters.copy()
        self.value=-value-1e-5
        self.gradient=-np.concatenate([[derivative],gradient])
    def function(self,parameters):
        self.update(parameters)
        return self.value
    def jacobian(self,parameters):
        self.update(parameters)
        return self.gradient

def main():
    best=2
    archive=[]
    for restart in range(5000):
        if (OUT/'witness.json').exists() or (OUT/'STOP_HOPPING').exists():
            return
        if not archive or restart%10==0:
            filename=['critical_best_698.json','structured_best.json','single_best_921.json'][restart%3]
            fields=np.array(json.loads((OUT/filename).read_text())['fields'],dtype=float)
        else:
            fields=archive[int(random.integers(min(8,len(archive))))][1].copy()
        if restart:
            for change in range(int(random.integers(1,10))):
                site=int(random.integers(16))
                fields[:,site]=np.roll(fields[:,site],int(random.choice([-4,-2,-1,1,2,4])))
            if restart%3==0:
                for swap in range(int(random.integers(1,4))):
                    sites=random.choice(16,size=2,replace=False)
                    fields[:,sites]=fields[:,sites[::-1]]
        initial=minimize(objective(1.3),fields.ravel(),jac=True,method='L-BFGS-B',bounds=[(-1,1)]*256,
                         options={'maxiter':250,'ftol':1e-12,'gtol':1e-8})
        if initial.fun>=0:
            continue
        constraint=Constraint()
        parameters=np.concatenate([[1.3],initial.x])
        gradient=np.zeros(257)
        gradient[0]=1
        result=minimize(lambda parameters:(parameters[0],gradient),parameters,jac=True,method='SLSQP',
                        constraints=[{'type':'ineq','fun':constraint.function,'jac':constraint.jacobian}],
                        bounds=[(.9,1.6)]+[(-1,1)]*256,options={'maxiter':100,'ftol':1e-9})
        if constraint.function(result.x)<-1e-6:
            continue
        hopping=result.x[0]
        fields=result.x[1:].reshape(16,16)
        rounded=np.where(fields>0,1,-1)
        score=evaluate(rounded)[0]
        if hopping<best:
            best=hopping
            save(rounded,'hopping_best_'+sys.argv[1]+'.json')
            print(f'{time.time()-started:.2f}s restart={restart} best_hopping={hopping:.12g} ratio={score:.12g}',flush=True)
        if score < -1e-7:
            save(rounded)
            print('FOUND',flush=True)
            return
        if all(abs(hopping-previous[0])>1e-6 for previous in archive):
            archive.append((hopping,fields.copy()))
            archive.sort(key=lambda entry:entry[0])
            archive=archive[:64]
        if restart%10==0:
            print(f'{time.time()-started:.2f}s restart={restart} hopping={hopping:.12g} archive={len(archive)}',flush=True)

if __name__=='__main__':
    main()
