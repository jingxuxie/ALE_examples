from synth import *
from improve import best_insert,best_delete
from fermion import Excitation

LIB.entropy_fungrad.argtypes=[ctypes.c_int,INTS,FLOATS,FLOATS]
LIB.entropy_fungrad.restype=ctypes.c_double
LIB.fourth_scan.argtypes=[FLOATS,FLOATS,FLOATS]

def entropy_optimize(labels,angles,iterations=200):
    labels=np.asarray(labels,dtype=np.int32)
    gradient=np.empty(len(labels))
    def objective(parameters):
        value=LIB.entropy_fungrad(len(labels),labels,parameters,gradient)
        return value,gradient.copy()
    result=minimize(objective,np.asarray(angles),jac=True,method='L-BFGS-B',options={'maxiter':iterations,'ftol':1e-13,'gtol':1e-9,'maxcor':30})
    return result.fun,(result.x+np.pi)%(2*np.pi)-np.pi

def preparation(engine,basis_index):
    start=engine.case.reference_mask
    final=engine.case.determinants[engine.keep[basis_index]]
    removed=[orbital for orbital in range(10) if start>>orbital&1 and not final>>orbital&1]
    added=[orbital for orbital in range(10) if final>>orbital&1 and not start>>orbital&1]
    moves=[]
    for orbital in removed:
        replacement=next(candidate for candidate in added if candidate%2==orbital%2)
        added.remove(replacement); moves.append((orbital,replacement))
    labels=[]; angles=[]
    lookup={label:index for index,label in enumerate(engine.labels)}
    current=start
    for offset in range(0,len(moves),2):
        group=moves[offset:offset+2]
        annihilate=tuple(sorted(move[0] for move in group))
        create=tuple(sorted(move[1] for move in group))
        if annihilate>create:annihilate,create=create,annihilate
        label=lookup[Excitation(annihilate,create)]
        full_index=engine.case.determinants.index(current)
        reduced_index=int(np.flatnonzero(engine.keep==full_index)[0])
        count=engine.lengths[label]
        if reduced_index in engine.sources[label,:count]:
            pair=int(np.flatnonzero(engine.sources[label,:count]==reduced_index)[0]); angle=engine.signs[label,pair]*np.pi/2
        else:
            pair=int(np.flatnonzero(engine.destinations[label,:count]==reduced_index)[0]); angle=-engine.signs[label,pair]*np.pi/2
        labels.append(label); angles.append(angle)
        for old,new in group:current^=(1<<old)|(1<<new)
    return labels,np.array(angles)

def save_reverse(engine,labels,angles,basis_index,original_ref,original_target):
    prefix,prefix_angles=preparation(engine,basis_index)
    forward_labels=prefix+labels[::-1]
    forward_angles=np.concatenate((prefix_angles,-angles[::-1]))
    if len(forward_labels)>engine.case.max_gates:return
    reverse_ref=engine.reference.copy(); reverse_target=engine.target.copy()
    engine.setup(reference=original_ref,target=original_target)
    state=engine.state(forward_labels,forward_angles)
    if state@original_target<0:
        forward_angles[0]+=np.pi
    value,forward_angles=engine.optimize(forward_labels,forward_angles,iterations=300)
    engine.save(forward_labels,forward_angles,value)
    engine.setup(reference=reverse_ref,target=reverse_target)

def run(case_index,seed,seconds):
    engine=Engine(case_index)
    original_ref=engine.reference.copy(); original_target=engine.target.copy()
    rng=np.random.default_rng(seed)
    deadline=time.time()+seconds
    trial=0
    while time.time()<deadline:
        engine.setup(reference=original_target,target=original_ref)
        labels=[]; angles=np.zeros(0); state=original_target.copy()
        for depth in range(engine.case.max_gates-2):
            gains=np.empty(250); guesses=np.empty(250)
            if trial%3==1:
                LIB.entropy_scan(state,1,gains,guesses); order=np.argsort(gains)
            else:
                LIB.fourth_scan(state,gains,guesses); order=np.argsort(-gains)
            label=int(order[int(rng.integers(3)) if depth<5 and trial>0 else 0])
            labels.append(label); angles=np.append(angles,guesses[label])
            if trial%3!=1 or depth%4==3:
                value,angles=entropy_optimize(labels,angles)
            state=engine.state(labels,angles)
        basis_index=int(np.argmax(abs(state)))
        endpoint=np.zeros(engine.dimension); endpoint[basis_index]=np.sign(state[basis_index])
        engine.setup(target=endpoint)
        value,angles=engine.optimize(labels,angles,iterations=500)
        prefix,_=preparation(engine,basis_index)
        while len(labels)+len(prefix)<engine.case.max_gates:
            value,labels,angles=best_insert(engine,labels,angles,rng,limit=5)
        stale=0
        for iteration in range(60):
            values,guesses=engine.scan(labels,angles,replacement=True)
            order=np.argsort(values,axis=None)
            pool=[]; seen=set()
            for pick in order:
                position,label=divmod(int(pick),250)
                if labels[position]==label or (label,round(guesses[position,label],8)) in seen:continue
                seen.add((label,round(guesses[position,label],8))); pool.append((position,label))
                if len(pool)>=24:break
            results=[]
            for position,label in pool:
                proposal=labels.copy(); proposal[position]=label
                parameters=angles.copy(); parameters[position]=guesses[position,label]
                loss,parameters=engine.optimize(proposal,parameters,iterations=150)
                results.append((loss,proposal,parameters))
            loss,proposal,parameters=min(results,key=lambda item:item[0])
            if loss<value-1e-10:
                value,labels,angles=loss,proposal,parameters; stale=0
            else:
                stale+=1
                if stale>2:break
                value,labels,angles=best_insert(engine,labels,angles,rng,limit=5)
                value,labels,angles=best_delete(engine,labels,angles,limit=8)
            if time.time()>deadline:break
        print('REVERSE',case_index,seed,trial,value,'basis',basis_index,'time',time.time()-engine.started,flush=True)
        save_reverse(engine,labels,angles,basis_index,original_ref,original_target)
        trial+=1

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',type=int,required=True)
    parser.add_argument('--seed',type=int,default=701)
    parser.add_argument('--seconds',type=int,default=900)
    args=parser.parse_args()
    run(args.case,args.seed,args.seconds)
