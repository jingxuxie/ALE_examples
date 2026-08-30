from synth import *
from improve import best_insert,best_delete
LIB.pair_scan.argtypes=[ctypes.c_int,INTS,FLOATS,ctypes.c_int,ctypes.c_int,ctypes.c_int,INTS,FLOATS,FLOATS]

def pair_candidates(engine,labels,angles,start,end,keep=8):
    choices=np.empty(((end-start)*keep,2),dtype=np.int32)
    parameters=np.empty(((end-start)*keep,2))
    values=np.empty((end-start)*keep)
    LIB.pair_scan(len(labels),np.asarray(labels,dtype=np.int32),np.asarray(angles,dtype=float),start,end,keep,choices,parameters,values)
    return [(values[index],start+index//keep,choices[index].tolist(),parameters[index]) for index in np.argsort(values)]

def run(case_index,seed,seconds):
    engine=Engine(case_index)
    rng=np.random.default_rng(seed)
    labels,angles=engine.load();value,angles=engine.optimize(labels,angles,precise=True)
    best_value,best_labels,best_angles=value,labels.copy(),angles.copy()
    deadline=time.time()+seconds
    stale=0;iteration=0
    while time.time()<deadline:
        candidates=pair_candidates(engine,labels,angles,0,len(labels)-1,keep=6)
        results=[]
        seen=set()
        for raw,position,selected,guess in candidates:
            proposal=labels.copy();proposal[position:position+2]=selected
            key=tuple(proposal)
            if key in seen:continue
            seen.add(key)
            parameters=angles.copy();parameters[position:position+2]=guess
            loss,parameters=engine.optimize(proposal,parameters,iterations=180)
            results.append((loss,proposal,parameters))
        loss,proposal,parameters=min(results,key=lambda item:item[0])
        if loss < value-1e-10:
            value,labels,angles=loss,proposal,parameters
        else:
            stale+=1
            stored_labels,stored_angles=engine.load();stored_value,stored_angles=engine.optimize(stored_labels,stored_angles)
            if stored_value<best_value:
                best_value,best_labels,best_angles=stored_value,stored_labels,stored_angles
            labels=best_labels.copy();angles=best_angles.copy()
            for move in range(1+min(4,stale//3)):
                position=int(rng.integers(len(labels)))
                if rng.random()<0.7:
                    label=labels.pop(position);angle=angles[position];angles=np.delete(angles,position)
                    new_position=int(rng.integers(len(labels)+1));labels.insert(new_position,label);angles=np.insert(angles,new_position,angle)
                else:
                    labels[position]=int(rng.integers(250));angles[position]=rng.normal()
            value,angles=engine.optimize(labels,angles,iterations=250)
        if value<best_value-1e-10:
            best_value,best_labels,best_angles=value,labels.copy(),angles.copy();stale=0
            engine.save(labels,angles,value)
        iteration+=1
        print('PAIRS',case_index,seed,iteration,value,'best',best_value,'stale',stale,'time',time.time()-engine.started,flush=True)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',type=int,required=True)
    parser.add_argument('--seed',type=int,default=901)
    parser.add_argument('--seconds',type=int,default=1000)
    args=parser.parse_args()
    run(args.case,args.seed,args.seconds)
