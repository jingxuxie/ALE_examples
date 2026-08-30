import argparse
import glob
import time
from pathlib import Path
import numpy as np
import fermion
from search import Engine
from local import insert


parser=argparse.ArgumentParser()
parser.add_argument('--case',type=int,default=0)
parser.add_argument('--seconds',type=float,default=600)
parser.add_argument('--choices',type=int,default=12)
parser.add_argument('--pattern',default='elite_*')
args=parser.parse_args()
engine=Engine(fermion.load_cases()[args.case])
initial=engine.load();engine.best=initial[2]
population={tuple(sorted(initial[0])):initial}
for filename in glob.glob(str(Path(__file__).resolve().parent/(engine.case.case_id+'_'+args.pattern+'.json'))):
    suffix=Path(filename).stem[len(engine.case.case_id)+1:]
    item=engine.load(suffix);key=tuple(sorted(item[0]))
    if key not in population or item[2]<population[key][2]:population[key]=item
rng=np.random.default_rng(393)
ordered=sorted(population.values(),key=lambda item:item[2])
for rank,(labels,angles,loss) in enumerate(ordered):
    labels,angles=labels.copy(),angles.copy()
    state,_=engine.state_jac(labels,angles)
    if state@engine.target<0:engine.target=-engine.target
    for sweep in range(3):
        original_loss=loss
        for position in rng.permutation(len(labels)):
            removed=engine.optimize(np.delete(labels,position),np.delete(angles,position),200)
            trial=insert(engine,removed[0],removed[1],choices=args.choices)
            if trial[2]<loss-1e-10:
                labels,angles,loss=trial
                engine.save(labels,angles,loss)
        for original in rng.permutation(len(labels)):
            base_labels=np.delete(labels,original);base_angles=np.delete(angles,original)
            for position in range(len(labels)):
                if original==position:continue
                trial=engine.optimize(np.insert(base_labels,position,labels[original]),np.insert(base_angles,position,angles[original]),150)
                if trial[2]<loss-1e-10:
                    labels,angles,loss=trial
                    engine.save(labels,angles,loss)
        if loss>=original_loss-1e-10:break
    print('elite',rank,'initial',ordered[rank][2],'final',loss,'best',engine.best,'elapsed',time.time()-engine.started,flush=True)
    if time.time()-engine.started>args.seconds:break
