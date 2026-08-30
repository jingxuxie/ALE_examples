from synth import *
from gauge import mappings,mutate
import multiprocessing as mp
from itertools import combinations
from collections import deque

LIB.pair_scan_spaced.argtypes=[ctypes.c_int,INTS,FLOATS,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,INTS,FLOATS,FLOATS]
WORKER=None

def initialize(case_index):
    global WORKER
    WORKER=Engine(case_index)

def batch(job):
    labels,angles,first,second,keep=job
    choices=np.empty((keep,2),dtype=np.int32)
    parameters=np.empty((keep,2))
    values=np.empty(keep)
    LIB.pair_scan_spaced(len(labels),np.asarray(labels,dtype=np.int32),np.asarray(angles,dtype=float),first,first+1,second-first,keep,choices,parameters,values)
    results=[]
    for choice,guess in zip(choices,parameters):
        proposal=labels.copy();proposal[first]=int(choice[0]);proposal[second]=int(choice[1])
        candidate_angles=angles.copy();candidate_angles[first]=guess[0];candidate_angles[second]=guess[1]
        value,candidate_angles=WORKER.optimize(proposal,candidate_angles,iterations=180)
        results.append((value,proposal,candidate_angles))
    return sorted(results,key=lambda item:item[0])[:3]

def run(case_index,workers,seconds,seed):
    engine=Engine(case_index)
    rng=np.random.default_rng(seed)
    maps=mappings(engine)
    labels,angles=engine.load();value,angles=engine.optimize(labels,angles,precise=True)
    best_value,best_labels,best_angles=value,labels.copy(),angles.copy()
    deadline=time.time()+seconds
    iteration=0;stale=0;tabu=deque(maxlen=120)
    with mp.Pool(workers,initializer=initialize,initargs=(case_index,)) as pool:
        while time.time()<deadline:
            tabu.append(tuple(labels))
            positions=list(combinations(range(len(labels)),2))
            if iteration%3!=0:
                rng.shuffle(positions);positions=positions[:120]
            jobs=[(labels,angles,first,second,32 if iteration%4 else 64) for first,second in positions]
            batches=pool.map(batch,jobs,chunksize=1)
            results=sorted((entry for batch_entries in batches for entry in batch_entries),key=lambda item:item[0])
            novel=[entry for entry in results if tuple(entry[1]) not in tabu or entry[0]<best_value-1e-10]
            if not novel:novel=results[:20]
            loss,proposal,parameters=novel[0]
            print('SPACED',case_index,iteration,'from',value,'to',loss,'best',best_value,'time',time.time()-engine.started,flush=True)
            if loss<best_value-1e-10:
                best_value,best_labels,best_angles=loss,proposal.copy(),parameters.copy();stale=0
                engine.save(proposal,parameters,loss)
                engine.save(proposal,parameters,loss,tag=f'spaced_{seed}')
            else:stale+=1
            value,labels,angles=loss,proposal,parameters
            if stale%5==0 or value>best_value*1.7:
                stored_labels,stored_angles=engine.load();stored_value,stored_angles=engine.optimize(stored_labels,stored_angles)
                if stored_value<best_value:
                    best_value,best_labels,best_angles=stored_value,stored_labels,stored_angles
                labels=best_labels.copy();angles=best_angles.copy()
                for move in range(1+stale%7):labels,angles=mutate(engine,labels,angles,maps,rng)
                if stale%10==0:
                    for move in range(2):
                        position=int(rng.integers(len(labels)));label=labels.pop(position);angle=angles[position];angles=np.delete(angles,position)
                        new_position=int(rng.integers(len(labels)+1));labels.insert(new_position,label);angles=np.insert(angles,new_position,angle)
                value,angles=engine.optimize(labels,angles,iterations=400)
            iteration+=1

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',type=int,required=True)
    parser.add_argument('--workers',type=int,default=24)
    parser.add_argument('--seed',type=int,default=1401)
    parser.add_argument('--seconds',type=int,default=800)
    args=parser.parse_args()
    run(args.case,args.workers,args.seconds,args.seed)
