import argparse
import time
import numpy as np
from scipy.optimize import minimize
import fermion
from search import Engine
from control import Control


parser=argparse.ArgumentParser()
parser.add_argument('--case',type=int,default=0)
parser.add_argument('--seconds',type=float,default=300)
parser.add_argument('--seed',type=int,default=924)
args=parser.parse_args()
engine=Engine(fermion.load_cases()[args.case])
engine.best=engine.load()[2]
rng=np.random.default_rng(args.seed)
iteration=0
while time.time()-engine.started<args.seconds:
    iteration+=1
    labels,angles,loss=engine.load()
    fixed_target=engine.target.copy()
    active=np.zeros(len(labels),bool)
    active[rng.choice(len(labels),int(rng.choice([2,3,4,5])),replace=False)]=True
    controls=np.zeros((len(labels),250))
    controls[np.arange(len(labels)),labels]=angles
    control=Control(engine,len(labels),active=active,fixed_labels=labels)
    parameters=controls.ravel()
    for penalty,bias in [(0.0001,0.03),(0.003,0.01),(0.03,0.01),(0.2,0.0)]:
        engine.target=fixed_target.copy()
        result=minimize(lambda values:control.evaluate(values,penalty,old_penalty=bias)[:2],parameters,jac=True,method='L-BFGS-B',options={'maxiter':120,'ftol':1e-10,'gtol':1e-7,'maxcor':10,'maxls':25})
        parameters=result.x
        controls=parameters.reshape(len(labels),250)
        chosen=np.argmax(abs(controls),axis=1).astype(np.int32)
        chosen_angles=controls[np.arange(len(labels)),chosen]
        found=engine.optimize(chosen,chosen_angles,300)
        engine.save(*found)
        print('local control',iteration,'active',np.flatnonzero(active),'penalty',penalty,'hard',found[2],'best',engine.best,'elapsed',time.time()-engine.started,flush=True)
        engine.target=fixed_target.copy()
