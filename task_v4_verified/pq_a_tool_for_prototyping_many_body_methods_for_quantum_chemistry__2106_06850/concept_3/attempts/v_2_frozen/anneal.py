import argparse
import time
import numpy as np
import fermion
from search import Engine


parser=argparse.ArgumentParser()
parser.add_argument('--case',type=int,default=0)
parser.add_argument('--seconds',type=float,default=480)
parser.add_argument('--seed',type=int,default=5492)
args=parser.parse_args()
engine=Engine(fermion.load_cases()[args.case])
engine.best=engine.load()[2]
rng=np.random.default_rng(args.seed)
cycle=0
while time.time()-engine.started<args.seconds:
    cycle+=1
    labels,angles,loss=engine.load()
    for iteration in range(240):
        temperature=0.012*(0.00015/0.012)**(iteration/239)
        removed=rng.choice(len(labels),int(rng.choice([1,1,2,2,3,4])),replace=False)
        blocked=int(labels[removed[0]])
        trial_labels,trial_angles,trial_loss=engine.optimize(np.delete(labels,removed),np.delete(angles,removed),200)
        while len(trial_labels)<len(labels):
            values,optimal=engine.projected(trial_labels,trial_angles)
            if len(trial_labels)==len(labels)-len(removed) and rng.random()<0.7:values[:,blocked]=-np.inf
            order=np.argsort(values.ravel())[::-1]
            top=order[:8] if rng.random()<0.4 else rng.choice(order[:60],5,replace=False)
            possibilities=[]
            for flat in top:
                position,label=np.unravel_index(flat,values.shape)
                possibilities.append(engine.optimize(np.insert(trial_labels,position,label),np.insert(trial_angles,position,optimal[position,label]),150))
            trial_labels,trial_angles,trial_loss=min(possibilities,key=lambda item:item[2])
        if trial_loss<engine.best-1e-10:engine.save(trial_labels,trial_angles,trial_loss)
        if trial_loss<loss or rng.random()<np.exp(min(0,(loss-trial_loss)/temperature)):
            labels,angles,loss=trial_labels,trial_angles,trial_loss
        if iteration%60==59:
            print('anneal',cycle,iteration+1,'current',loss,'best',engine.best,'temperature',temperature,'elapsed',time.time()-engine.started,flush=True)
        if time.time()-engine.started>=args.seconds:break
