import argparse
import time
import numpy as np
import fermion
from search import Engine
from local import insert


parser=argparse.ArgumentParser()
parser.add_argument('--case',type=int,default=0)
parser.add_argument('--seconds',type=float,default=300)
parser.add_argument('--seed',type=int,default=731)
args=parser.parse_args()
engine=Engine(fermion.load_cases()[args.case])
engine.best=engine.load()[2]
rng=np.random.default_rng(args.seed)
iteration=0
while time.time()-engine.started<args.seconds:
    iteration+=1
    labels,angles,loss=engine.load()
    actual=engine.target.copy()
    state,_=engine.state_jac(labels,angles)
    strength=float(rng.choice([0.5,1,1.5,2,3]))
    guide=actual+strength*(actual-state)+rng.normal(0,rng.choice([0,0.005,0.01,0.02]),len(state))
    engine.target=guide/np.linalg.norm(guide)
    labels,angles,loss=engine.optimize(labels,angles,200)
    for position in rng.permutation(len(labels)):
        shortened=engine.optimize(np.delete(labels,position),np.delete(angles,position),150)
        trial=insert(engine,shortened[0],shortened[1],choices=12)
        if trial[2]<loss-1e-10:
            labels,angles,loss=trial
    engine.target=actual
    labels,angles,loss=engine.optimize(labels,angles,300)
    engine.save(labels,angles,loss)
    if iteration%5==0:
        print('guided',iteration,'candidate',loss,'best',engine.best,'elapsed',time.time()-engine.started,flush=True)
