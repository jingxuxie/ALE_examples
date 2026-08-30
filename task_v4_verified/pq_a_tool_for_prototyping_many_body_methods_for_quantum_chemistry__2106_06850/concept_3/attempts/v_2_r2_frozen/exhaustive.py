from synth import *
from gauge import mappings,mutate
import multiprocessing as mp

WORKER=None

def initialize(case_index):
    global WORKER
    WORKER=Engine(case_index)

def batch(job):
    labels,angles,position,first,last,guesses,mode=job
    best=(float('inf'),None,None)
    for label in range(first,last):
        if label==labels[position]:continue
        proposal=labels.copy();proposal[position]=label
        parameters=angles.copy();parameters[position]=guesses[label]
        value,parameters=WORKER.optimize(proposal,parameters,iterations=220)
        if value<best[0]:best=value,proposal,parameters
        if mode and label%3==0:
            parameters=angles.copy();parameters[position]=0.0
            value,parameters=WORKER.optimize(proposal,parameters,iterations=160)
            if value<best[0]:best=value,proposal,parameters
    return best

def run(case_index,workers,seconds,seed):
    engine=Engine(case_index)
    rng=np.random.default_rng(seed)
    maps=mappings(engine)
    labels,angles=engine.load();value,angles=engine.optimize(labels,angles,precise=True)
    best_value,best_labels,best_angles=value,labels.copy(),angles.copy()
    deadline=time.time()+seconds
    iteration=0;stale=0
    with mp.Pool(workers,initializer=initialize,initargs=(case_index,)) as pool:
        while time.time()<deadline:
            values,guesses=engine.scan(labels,angles,replacement=True)
            jobs=[(labels,angles,position,first,min(first+25,250),guesses[position].copy(),int(iteration%4==3)) for position in range(len(labels)) for first in range(0,250,25)]
            results=pool.map(batch,jobs,chunksize=1)
            results.sort(key=lambda item:item[0])
            loss,proposal,parameters=results[0]
            print('EXHAUSTIVE',case_index,iteration,'from',value,'to',loss,'best',best_value,'time',time.time()-engine.started,flush=True)
            if loss<value-1e-10:
                value,labels,angles=loss,proposal,parameters
            else:
                stale+=1
                stored_labels,stored_angles=engine.load();stored_value,stored_angles=engine.optimize(stored_labels,stored_angles)
                if stored_value<best_value:
                    best_value,best_labels,best_angles=stored_value,stored_labels,stored_angles
                labels=best_labels.copy();angles=best_angles.copy()
                if stale%3==1:
                    for move in range(1+stale%7):labels,angles=mutate(engine,labels,angles,maps,rng)
                elif stale%3==2:
                    pick=int(rng.integers(min(20,len(results))))
                    value,labels,angles=results[pick]
                else:
                    for move in range(1+min(5,stale//9)):
                        position=int(rng.integers(len(labels)))
                        if rng.random()<0.8:
                            label=labels.pop(position);angle=angles[position];angles=np.delete(angles,position)
                            new_position=int(rng.integers(len(labels)+1));labels.insert(new_position,label);angles=np.insert(angles,new_position,angle)
                        else:
                            labels[position]=int(rng.integers(250));angles[position]=rng.normal()
                value,angles=engine.optimize(labels,angles,iterations=400)
            if value<best_value-1e-10:
                best_value,best_labels,best_angles=value,labels.copy(),angles.copy();stale=0
                engine.save(labels,angles,value)
                engine.save(labels,angles,value,tag=f'exhaustive_{seed}')
            iteration+=1

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',type=int,required=True)
    parser.add_argument('--workers',type=int,default=24)
    parser.add_argument('--seed',type=int,default=1301)
    parser.add_argument('--seconds',type=int,default=1000)
    args=parser.parse_args()
    run(args.case,args.workers,args.seconds,args.seed)
