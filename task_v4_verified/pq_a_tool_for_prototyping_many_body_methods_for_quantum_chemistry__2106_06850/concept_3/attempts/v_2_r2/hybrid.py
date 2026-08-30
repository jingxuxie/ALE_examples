from synth import *
from gauge import mappings,mutate
from spaced import LIB
import multiprocessing as mp
from itertools import combinations
from collections import deque

WORKER=None

def initialize(case_index):
    global WORKER
    WORKER=Engine(case_index)

def unique_results(results,keep=4):
    selected=[]
    for entry in sorted(results,key=lambda item:item[0]):
        if all(abs(entry[0]-previous[0])>1e-9 for previous in selected):selected.append(entry)
        if len(selected)>=keep:break
    return selected

def batch(job):
    mode,labels,angles,first,second,seed=job
    rng=np.random.default_rng(seed)
    results=[]
    if mode=='pair':
        keep=48
        choices=np.empty((keep,2),dtype=np.int32);parameters=np.empty((keep,2));values=np.empty(keep)
        LIB.pair_scan_spaced(len(labels),np.asarray(labels,dtype=np.int32),np.asarray(angles,dtype=float),first,first+1,second-first,keep,choices,parameters,values)
        for choice,guess in zip(choices,parameters):
            proposal=labels.copy();proposal[first]=int(choice[0]);proposal[second]=int(choice[1])
            candidate_angles=angles.copy();candidate_angles[first]=guess[0];candidate_angles[second]=guess[1]
            value,candidate_angles=WORKER.optimize(proposal,candidate_angles,iterations=180)
            results.append((value,proposal,candidate_angles))
    elif mode=='relocate':
        old_label=labels[first]
        reduced_labels=labels[:first]+labels[first+1:];reduced_angles=np.delete(angles,first)
        values,guesses=WORKER.scan(reduced_labels,reduced_angles)
        for position in range(len(labels)):
            chosen=np.argsort(values[position])[:12].tolist()
            if old_label not in chosen:chosen.append(old_label)
            for label in chosen:
                proposal=reduced_labels[:position]+[label]+reduced_labels[position:]
                parameters=np.insert(reduced_angles,position,guesses[position,label])
                value,parameters=WORKER.optimize(proposal,parameters,iterations=220)
                results.append((value,proposal,parameters))
    elif mode=='angles':
        for trial in range(24):
            if trial%4==0:parameters=rng.uniform(-np.pi,np.pi,size=len(labels))
            elif trial%4==1:parameters=angles+rng.normal(scale=0.6,size=len(labels))
            elif trial%4==2:parameters=angles+np.pi*rng.binomial(1,0.2,size=len(labels))
            else:parameters=angles+rng.normal(scale=0.25,size=len(labels))
            value,parameters=WORKER.optimize(labels,parameters,iterations=500)
            results.append((value,labels,parameters))
    else:
        for kind in range(3):
            proposal=labels.copy();parameters=angles.copy()
            if kind==0:
                proposal[first],proposal[second]=proposal[second],proposal[first]
                parameters[first],parameters[second]=parameters[second],parameters[first]
            else:
                source,destination=(first,second) if kind==1 else (second,first)
                label=proposal.pop(source);angle=parameters[source];parameters=np.delete(parameters,source)
                proposal.insert(destination,label);parameters=np.insert(parameters,destination,angle)
            value,parameters=WORKER.optimize(proposal,parameters,iterations=250)
            results.append((value,proposal,parameters))
    return unique_results(results)

def run(case_index,workers,seconds,seed):
    engine=Engine(case_index)
    rng=np.random.default_rng(seed);maps=mappings(engine)
    labels,angles=engine.load();value,angles=engine.optimize(labels,angles,precise=True)
    best_value,best_labels,best_angles=value,labels.copy(),angles.copy()
    deadline=time.time()+seconds
    iteration=0;stale=0;tabu=deque(maxlen=100)
    with mp.Pool(workers,initializer=initialize,initargs=(case_index,)) as pool:
        while time.time()<deadline:
            tabu.append(value)
            mode=['pair','relocate','angles','order'][iteration%4]
            if mode in ('pair','order'):positions=list(combinations(range(len(labels)),2))
            elif mode=='relocate':positions=[(position,0) for position in range(len(labels))]
            else:positions=[(position,0) for position in range(96)]
            jobs=[(mode,labels,angles,first,second,int(rng.integers(1000000000))) for first,second in positions]
            batches=pool.map(batch,jobs,chunksize=1)
            results=sorted((entry for entries in batches for entry in entries),key=lambda item:item[0])
            if results[0][0]<best_value-1e-10:
                best_value,best_labels,best_angles=results[0][0],results[0][1].copy(),results[0][2].copy();stale=0
                engine.save(best_labels,best_angles,best_value)
                engine.save(best_labels,best_angles,best_value,tag=f'hybrid_{seed}')
            else:stale+=1
            novel=[entry for entry in results if all(abs(entry[0]-old)>1e-8 for old in tabu)]
            loss,proposal,parameters=novel[0] if novel else results[0]
            print('HYBRID',case_index,iteration,mode,'from',value,'to',loss,'best',best_value,'time',time.time()-engine.started,flush=True)
            value,labels,angles=loss,proposal,parameters
            if stale%8==0 or value>best_value*1.6:
                stored_labels,stored_angles=engine.load();stored_value,stored_angles=engine.optimize(stored_labels,stored_angles)
                if stored_value<best_value:best_value,best_labels,best_angles=stored_value,stored_labels,stored_angles
                labels=best_labels.copy();angles=best_angles.copy()
                for move in range(1+stale%5):labels,angles=mutate(engine,labels,angles,maps,rng)
                if stale>15:
                    for move in range(1+stale%3):
                        position=int(rng.integers(len(labels)));label=labels.pop(position);angle=angles[position];angles=np.delete(angles,position)
                        destination=int(rng.integers(len(labels)+1));labels.insert(destination,label);angles=np.insert(angles,destination,angle)
                value,angles=engine.optimize(labels,angles,iterations=350)
            iteration+=1

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',type=int,required=True)
    parser.add_argument('--workers',type=int,default=24)
    parser.add_argument('--seed',type=int,default=1501)
    parser.add_argument('--seconds',type=int,default=600)
    args=parser.parse_args()
    run(args.case,args.workers,args.seconds,args.seed)
