from synth import *

def jacobian(engine, labels, angles):
    residual=np.empty(engine.dimension)
    derivatives=np.empty((engine.dimension,len(labels)))
    LIB.residual_jac(len(labels),np.asarray(labels,dtype=np.int32),np.asarray(angles,dtype=float),residual,derivatives)
    return residual,derivatives

def insertion_choices(engine,labels,angles,limit=12):
    residual,derivatives=jacobian(engine,labels,angles)
    tangents=np.empty(((len(labels)+1)*250,engine.dimension))
    LIB.insertion_tangents(len(labels),np.asarray(labels,dtype=np.int32),np.asarray(angles,dtype=float),tangents)
    left,singular,right=np.linalg.svd(derivatives,full_matrices=False)
    left=left[:,singular>1e-8]
    projected=tangents-(tangents@left)@left.T
    gradients=tangents@residual
    norms=np.sum(projected**2,axis=1)
    scores=gradients**2/np.maximum(norms,1e-16)
    scores[norms<1e-12]=0
    values,guesses=engine.scan(labels,angles)
    selected=[]
    normalized=tangents/np.maximum(np.linalg.norm(tangents,axis=1)[:,None],1e-16)
    for order in (np.argsort(-scores),np.argsort(values,axis=None)):
        added=0
        for pick in order:
            if any(abs(normalized[pick]@normalized[other])>1-1e-8 for other in selected):
                continue
            selected.append(int(pick)); added+=1
            if added>=limit:break
    return [(pick//250,pick%250,guesses.flat[pick],scores[pick]) for pick in selected]

def best_insert(engine,labels,angles,rng,limit=6,randomness=0):
    choices=insertion_choices(engine,labels,angles,limit)
    if randomness:
        choices=choices[:2]+[choices[index] for index in rng.choice(len(choices),size=min(len(choices),randomness),replace=False)]
    results=[]
    for position,label,angle,score in choices:
        proposal=labels[:position]+[label]+labels[position:]
        parameters=np.insert(angles,position,angle)
        value,parameters=engine.optimize(proposal,parameters,iterations=120)
        results.append((value,proposal,parameters))
    return min(results,key=lambda item:item[0])

def best_delete(engine,labels,angles,limit=7):
    residual,derivatives=jacobian(engine,labels,angles)
    hessian=derivatives.T@derivatives
    inverse=np.linalg.pinv(hessian,rcond=1e-10)
    importance=angles**2/np.maximum(np.diag(inverse),1e-15)
    order=np.argsort(importance)
    results=[]
    for position in order[:limit]:
        proposal=labels[:position]+labels[position+1:]
        parameters=np.delete(angles,position)
        value,parameters=engine.optimize(proposal,parameters,iterations=160)
        results.append((value,proposal,parameters))
    return min(results,key=lambda item:item[0])

def run(case_index,seconds,seed):
    engine=Engine(case_index)
    rng=np.random.default_rng(seed)
    labels,angles=engine.load()
    value,angles=engine.optimize(labels,angles,precise=True)
    best_value,best_labels,best_angles=value,labels.copy(),angles.copy()
    engine.best=value
    deadline=time.time()+seconds
    iteration=0
    stale=0
    while time.time()<deadline and best_value>1e-11:
        add_count=1 if stale<5 else int(rng.integers(2,5))
        for added in range(add_count):
            value,labels,angles=best_insert(engine,labels,angles,rng,limit=5 if stale<5 else 3,randomness=0)
        for removed in range(add_count):
            value,labels,angles=best_delete(engine,labels,angles,limit=8)
        if value<best_value-1e-10:
            best_value,best_labels,best_angles=value,labels.copy(),angles.copy()
            engine.save(labels,angles,value)
            stale=0
        else:
            stale+=1
            if stale%4==0:
                labels=best_labels.copy(); angles=best_angles.copy()
                for move in range(1+stale//12):
                    position=int(rng.integers(len(labels)))
                    new_position=int(rng.integers(len(labels)))
                    label=labels.pop(position); angle=angles[position]; angles=np.delete(angles,position)
                    labels.insert(new_position,label); angles=np.insert(angles,new_position,angle)
                value,angles=engine.optimize(labels,angles,iterations=160)
        iteration+=1
        if iteration%5==0:
            print('IMPROVE',case_index,iteration,'current',value,'best',best_value,'stale',stale,'time',time.time()-engine.started,flush=True)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',type=int,required=True)
    parser.add_argument('--seconds',type=int,default=900)
    parser.add_argument('--seed',type=int,default=50)
    args=parser.parse_args()
    run(args.case,args.seconds,args.seed)
