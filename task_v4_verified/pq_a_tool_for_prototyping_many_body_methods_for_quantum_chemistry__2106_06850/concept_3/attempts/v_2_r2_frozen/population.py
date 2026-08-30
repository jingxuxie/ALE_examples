from synth import *
from improve import best_insert,best_delete

def random_grow(engine,rng,style):
    labels=[]; angles=np.zeros(0)
    for depth in range(engine.case.max_gates):
        values,guesses=engine.scan(labels,angles)
        if style%4==1: values[:-1]=np.inf
        if style%4==2: values[1:]=np.inf
        if style%4==3 and depth<6 and style<4: values[:,20:]=np.inf
        if 4<=style<8 and depth<6:
            for label,excitation in enumerate(engine.labels):
                if len(excitation.annihilate)!=2 or excitation.annihilate[0]//2!=excitation.annihilate[1]//2 or excitation.create[0]//2!=excitation.create[1]//2:
                    values[:,label]=np.inf
        if style>=8:
            occupied={orbital for orbital in range(10) if engine.case.reference_mask>>orbital&1}
            for label,excitation in enumerate(engine.labels):
                if not (set(excitation.annihilate)<=occupied and not set(excitation.create)&occupied):
                    values[:,label]=np.inf
        order=np.argsort(values,axis=None)
        pool=[]; seen=set()
        for pick in order:
            position,label=divmod(int(pick),250)
            if label in seen or not np.isfinite(values[position,label]):continue
            seen.add(label); pool.append((position,label))
            if len(pool)>=4:break
        if depth<8 or rng.random()<0.2:
            position,label=pool[int(rng.integers(len(pool)))]
        else:
            position,label=pool[0]
        proposal=labels[:position]+[label]+labels[position:]
        parameters=np.insert(angles,position,guesses[position,label])
        value,angles=engine.optimize(proposal,parameters,iterations=160)
        labels=proposal
    return value,labels,angles

def run(case_index,seed,seconds):
    engine=Engine(case_index)
    rng=np.random.default_rng(seed)
    deadline=time.time()+seconds
    iteration=0
    while time.time()<deadline:
        if iteration%3==0:
            value,labels,angles=random_grow(engine,rng,seed%12)
        else:
            labels,angles=engine.load()
            value,angles=engine.optimize(labels,angles)
            count=int(rng.integers(2,6))
            for move in range(count):
                position=int(rng.integers(len(labels)))
                if rng.random()<0.6:
                    label=labels.pop(position); angle=angles[position]; angles=np.delete(angles,position)
                    destination=int(rng.integers(len(labels)+1))
                    labels.insert(destination,label); angles=np.insert(angles,destination,angle)
                else:
                    labels[position]=int(rng.integers(250)); angles[position]=rng.normal()
            value,angles=engine.optimize(labels,angles,iterations=200)
        local_best=value
        stale=0
        for sweep in range(100):
            values,guesses=engine.scan(labels,angles,replacement=True)
            order=np.argsort(values,axis=None)
            pool=[]; seen=set()
            for pick in order:
                position,label=divmod(int(pick),250)
                if labels[position]==label or (label,round(guesses[position,label],8)) in seen:continue
                seen.add((label,round(guesses[position,label],8)))
                pool.append((position,label))
                if len(pool)>=32:break
            results=[]
            for position,label in pool:
                proposal=labels.copy(); proposal[position]=label
                parameters=angles.copy(); parameters[position]=guesses[position,label]
                loss,parameters=engine.optimize(proposal,parameters,iterations=120)
                results.append((loss,proposal,parameters))
            loss,proposal,parameters=min(results,key=lambda item:item[0])
            if loss < value-1e-10:
                value,labels,angles=loss,proposal,parameters
                stale=0
            else:
                stale+=1
                if stale>2:break
                value,labels,angles=best_insert(engine,labels,angles,rng,limit=4)
                value,labels,angles=best_delete(engine,labels,angles,limit=8)
            if value<engine.best:
                engine.save(labels,angles,value)
            if time.time()>deadline:break
        print('POP',case_index,seed,iteration,value,'seconds',time.time()-engine.started,flush=True)
        iteration+=1

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',type=int,required=True)
    parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--seconds',type=int,default=1200)
    args=parser.parse_args()
    run(args.case,args.seed,args.seconds)
