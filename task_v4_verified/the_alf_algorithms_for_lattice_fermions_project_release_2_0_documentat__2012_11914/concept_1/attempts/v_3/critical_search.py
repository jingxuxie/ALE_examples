import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import sys
import time
import json
import numpy as np
from scipy.optimize import minimize
from gradient_search import Objective
from search import OUT,evaluate,save

random=np.random.default_rng(int(sys.argv[1]))
started=time.time()

class Constraint:
    def __init__(self):
        self.previous=None
        self.value=None
        self.gradient=None
    def update(self,parameters):
        if self.previous is not None and np.array_equal(parameters,self.previous):
            return
        beta=parameters[0]
        fields=parameters[1:]
        value,gradient=Objective(beta,both=False)(fields)
        epsilon=1e-5
        plus=Objective(beta+epsilon,both=False)(fields)[0]
        minus=Objective(beta-epsilon,both=False)(fields)[0]
        self.previous=parameters.copy()
        self.value=-value-1e-5
        self.gradient=-np.concatenate([[(plus-minus)/(2*epsilon)],gradient])
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
        if (OUT/'witness.json').exists() or (OUT/'STOP_CRITICAL').exists():
            return
        if len(sys.argv)>2 and (not archive or restart%2==0):
            blocks=int(random.choice([3,4,5,6,8]))
            values=random.choice([-1,1],size=(blocks,16)).astype(float)
            fields=values[(np.arange(16)*blocks)//16]
        elif not archive or restart%10==0:
            filename=['critical_best_698.json','single_best_921.json','quotient_best_815.json','gradient_best_619.json'][restart%4]
            fields=np.array(json.loads((OUT/filename).read_text())['fields'],dtype=float)
        else:
            fields=archive[int(random.integers(min(4,len(archive))))][1].copy()
        if restart:
            if restart%3==0:
                for swap in range(int(random.integers(1,5))):
                    sites=random.choice(16,size=2,replace=False)
                    fields[:,sites]=fields[:,sites[::-1]]
            for change in range(int(random.integers(2,13))):
                site=int(random.integers(16))
                if restart%10==0 and random.random()<.35:
                    fields[:,site]=random.choice([-1,1])
                elif random.random()<.5:
                    fields[:,site]=np.roll(fields[:,site],int(random.choice([-2,-1,1,2])))
                else:
                    boundaries=np.flatnonzero(np.sign(fields[:,site])!=np.roll(np.sign(fields[:,site]),1))
                    if len(boundaries):
                        boundary=int(random.choice(boundaries))
                        time_index=(boundary+int(random.choice([-1,0])))%16
                        fields[time_index,site]=-np.sign(fields[time_index,site])
            if restart%10==0 and random.random()<.3:
                fields*=random.choice([-1,1],size=fields.shape,p=[.15,.85])
        initial_beta=.80
        if Objective(initial_beta,both=False)(fields.ravel())[0]<-1e-4:
            initial_fields=fields.ravel()
        else:
            initial_beta=.85
            initial=minimize(Objective(initial_beta,both=False),fields.ravel(),jac=True,method='L-BFGS-B',bounds=[(-1,1)]*256,
                             options={'maxiter':250,'ftol':1e-12,'gtol':1e-8})
            if initial.fun>=0:
                continue
            initial_fields=initial.x
        constraint=Constraint()
        parameters=np.concatenate([[initial_beta],initial_fields])
        gradient=np.zeros(257)
        gradient[0]=1
        result=minimize(lambda parameters:(parameters[0],gradient),parameters,jac=True,method='SLSQP',
                        constraints=[{'type':'ineq','fun':constraint.function,'jac':constraint.jacobian}],
                        bounds=[(.73,.95)]+[(-1,1)]*256,options={'maxiter':100,'ftol':1e-9})
        if constraint.function(result.x)<-1e-6:
            print(f'{time.time()-started:.2f}s restart={restart} infeasible={constraint.function(result.x):.8g}',flush=True)
            continue
        beta=result.x[0]
        fields=result.x[1:].reshape(16,16)
        rounded=np.where(fields>0,1,-1)
        score=evaluate(rounded)[0]
        if beta<best:
            best=beta
            save(rounded,'critical_best_'+sys.argv[1]+'.json')
            (OUT/('critical_continuous_'+sys.argv[1]+'.json')).write_text(json.dumps({'beta':float(beta),'fields':fields.tolist()}))
            print(f'{time.time()-started:.2f}s restart={restart} best_beta={beta:.12g} ratio={score:.12g} constraint={constraint.function(result.x):.12g} success={result.success}',flush=True)
        if score < -1e-5:
            save(rounded)
            print('FOUND',flush=True)
            return
        if all(abs(beta-previous[0])>1e-6 for previous in archive):
            archive.append((beta,fields.copy()))
            archive.sort(key=lambda entry:entry[0])
            archive=archive[:64]
        if restart%10==0:
            print(f'{time.time()-started:.2f}s restart={restart} beta={beta:.12g} archive={len(archive)}',flush=True)

if __name__=='__main__':
    main()
