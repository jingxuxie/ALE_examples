from synth import *
from improve import best_insert,best_delete

def run(case_index,seed,seconds):
    engine=Engine(case_index)
    rng=np.random.default_rng(seed)
    occupied={orbital for orbital in range(10) if engine.case.reference_mask>>orbital&1}
    singles=[index for index,label in enumerate(engine.labels[:20]) if set(label.annihilate)<=occupied and not set(label.create)&occupied]
    deadline=time.time()+seconds
    trial=0
    while time.time()<deadline:
        if seed%3==0:
            fixed=singles.copy()
        elif seed%3==1:
            fixed=singles[::-1]
        else:
            fixed=singles.copy();rng.shuffle(fixed)
        labels=fixed.copy()
        angles=rng.normal(scale=0.8,size=len(labels))
        value,angles=engine.optimize(labels,angles,iterations=400)
        for depth in range(engine.case.max_gates-len(labels)):
            values,guesses=engine.scan(labels,angles)
            values[:len(fixed)]=np.inf
            values[:, :20]=np.inf
            order=np.argsort(values,axis=None)
            choices=[]; seen=set()
            for pick in order:
                position,label=divmod(int(pick),250)
                if label in seen:continue
                seen.add(label);choices.append((position,label))
                if len(choices)>=6:break
            results=[]
            for position,label in choices:
                proposal=labels[:position]+[label]+labels[position:]
                parameters=np.insert(angles,position,guesses[position,label])
                loss,parameters=engine.optimize(proposal,parameters,iterations=250)
                results.append((loss,proposal,parameters))
            value,labels,angles=min(results,key=lambda item:item[0])
        best=value
        stale=0
        for step in range(100):
            values,guesses=engine.scan(labels,angles,replacement=True)
            values[:len(fixed)]=np.inf
            order=np.argsort(values,axis=None)
            choices=[];seen=set()
            for pick in order:
                position,label=divmod(int(pick),250)
                if not np.isfinite(values[position,label]):break
                if labels[position]==label or (label,round(guesses[position,label],8)) in seen:continue
                seen.add((label,round(guesses[position,label],8)));choices.append((position,label))
                if len(choices)>=40:break
            results=[]
            for position,label in choices:
                proposal=labels.copy();proposal[position]=label
                parameters=angles.copy();parameters[position]=guesses[position,label]
                loss,parameters=engine.optimize(proposal,parameters,iterations=200)
                results.append((loss,proposal,parameters))
            loss,proposal,parameters=min(results,key=lambda item:item[0])
            if loss<value-1e-10:
                value,labels,angles=loss,proposal,parameters;stale=0
            else:
                stale+=1
                if stale>2:break
                position=int(rng.integers(len(fixed),len(labels)))
                label=labels.pop(position);angle=angles[position];angles=np.delete(angles,position)
                new_position=int(rng.integers(len(fixed),len(labels)+1));labels.insert(new_position,label);angles=np.insert(angles,new_position,angle)
                value,angles=engine.optimize(labels,angles,iterations=200)
            engine.save(labels,angles,value)
            if time.time()>deadline:break
        print('GAUSS',case_index,seed,trial,value,time.time()-engine.started,flush=True)
        trial+=1

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',type=int,required=True)
    parser.add_argument('--seed',type=int,default=801)
    parser.add_argument('--seconds',type=int,default=1000)
    args=parser.parse_args()
    run(args.case,args.seed,args.seconds)
