from synth import *
from improve import best_insert,best_delete

def mappings(engine):
    path=ROOT/f'gauge_{engine.case.n_electrons}.npz'
    if path.exists():
        data=np.load(path)
        return data['half_labels'],data['half_signs'],data['full_signs'],data['stable']
    lookup={}
    def key(source,destination,sign):
        lower=np.minimum(source,destination);upper=np.maximum(source,destination)
        directed=sign*np.where(source<destination,1,-1)
        edges=lower*engine.dimension+upper
        order=np.argsort(edges);directed=directed[order];edges=edges[order]
        first=int(directed[0])
        return (tuple(edges.tolist()),tuple((directed*first).astype(int).tolist())),first
    for label in range(250):
        count=engine.lengths[label]
        signature,sign=key(engine.sources[label,:count],engine.destinations[label,:count],engine.signs[label,:count])
        lookup[signature]=(label,sign)
    half_labels=np.full((250,250),-1,dtype=np.int32)
    half_signs=np.zeros((250,250),dtype=np.int32)
    full_signs=np.zeros((250,250),dtype=np.int32)
    stable=np.zeros(250,dtype=bool)
    refindex=int(np.argmax(engine.reference))
    for conjugator in range(250):
        count=engine.lengths[conjugator]
        source=engine.sources[conjugator,:count];destination=engine.destinations[conjugator,:count];sign=engine.signs[conjugator,:count]
        permutation=np.arange(engine.dimension);phases=np.ones(engine.dimension)
        permutation[source]=destination;permutation[destination]=source
        phases[source]=sign;phases[destination]=-sign
        active=np.zeros(engine.dimension,dtype=bool);active[source]=True;active[destination]=True
        stable[conjugator]=not active[refindex]
        for label in range(250):
            length=engine.lengths[label]
            left=engine.sources[label,:length];right=engine.destinations[label,:length]
            signature,first=key(permutation[left],permutation[right],engine.signs[label,:length]*phases[left]*phases[right])
            if signature in lookup:
                mapped,mapped_first=lookup[signature]
                half_labels[conjugator,label]=mapped;half_signs[conjugator,label]=first*mapped_first
            flips=active[left]^active[right]
            if np.all(flips):full_signs[conjugator,label]=-1
            elif not np.any(flips):full_signs[conjugator,label]=1
    np.savez(path,half_labels=half_labels,half_signs=half_signs,full_signs=full_signs,stable=stable)
    return half_labels,half_signs,full_signs,stable

def mutate(engine,labels,angles,maps,rng):
    half_labels,half_signs,full_signs,stable=maps
    choices=[]
    for position,conjugator in enumerate(labels):
        if position==0:continue
        prefix=np.asarray(labels[:position])
        if stable[conjugator] and np.all(half_labels[conjugator,prefix]>=0):choices.append((position,True))
        if np.all(full_signs[conjugator,prefix]!=0):choices.append((position,False))
    if not choices:return labels,angles
    position,half=choices[int(rng.integers(len(choices)))]
    conjugator=labels[position]
    labels=labels.copy();angles=angles.copy()
    prefix=np.asarray(labels[:position])
    if half:
        labels[:position]=half_labels[conjugator,prefix].tolist()
        angles[:position]*=half_signs[conjugator,prefix]
        angles[position]-=np.pi/2
    else:
        angles[:position]*=full_signs[conjugator,prefix]
        angles[position]-=np.pi
    state=engine.state(labels,angles)
    if state@engine.target<0:angles[0]+=np.pi
    return labels,(angles+np.pi)%(2*np.pi)-np.pi

def refine(engine,labels,angles,rng,steps=15):
    value,angles=engine.optimize(labels,angles,iterations=250)
    for step in range(steps):
        values,guesses=engine.scan(labels,angles,replacement=True)
        pool=[]
        for position in range(len(labels)):
            order=np.argsort(values[position])
            chosen=0
            for label in order:
                if label==labels[position]:continue
                pool.append((position,int(label)));chosen+=1
                if chosen>=4:break
        results=[]
        for position,label in pool:
            proposal=labels.copy();proposal[position]=label
            parameters=angles.copy();parameters[position]=guesses[position,label]
            loss,parameters=engine.optimize(proposal,parameters,iterations=140)
            results.append((loss,proposal,parameters))
        loss,proposal,parameters=min(results,key=lambda item:item[0])
        if loss>=value-1e-10:break
        value,labels,angles=loss,proposal,parameters
        engine.save(labels,angles,value)
    return value,labels,angles

def run(case_index,seed,seconds):
    engine=Engine(case_index)
    maps=mappings(engine)
    rng=np.random.default_rng(seed)
    deadline=time.time()+seconds
    trial=0
    worker_best=1.0
    while time.time()<deadline:
        labels,angles=engine.load()
        if trial%7==6:
            parents=list(ROOT.glob(f'gauge_*_{case_index}.json'))
            if parents:
                parent=parents[int(rng.integers(len(parents)))].stem.rsplit('_',1)[0]
                other_labels,other_angles=engine.load(parent)
                position=int(rng.integers(1,len(labels)))
                labels[position:]=other_labels[position:];angles[position:]=other_angles[position:]
        else:
            for move in range(1+trial%5):labels,angles=mutate(engine,labels,angles,maps,rng)
        if trial%4==3:
            for move in range(1+trial%3):
                position=int(rng.integers(len(labels)));new_position=int(rng.integers(len(labels)))
                label=labels.pop(position);angle=angles[position];angles=np.delete(angles,position)
                labels.insert(new_position,label);angles=np.insert(angles,new_position,angle)
        value,labels,angles=refine(engine,labels,angles,rng)
        if trial%3==2:
            value,labels,angles=best_insert(engine,labels,angles,rng,limit=8)
            value,labels,angles=best_delete(engine,labels,angles,limit=12)
            value,labels,angles=refine(engine,labels,angles,rng,steps=5)
        engine.save(labels,angles,value)
        if value<worker_best-1e-10:
            worker_best=value;engine.save(labels,angles,value,tag=f'gauge_{seed}')
        print('GAUGE',case_index,seed,trial,value,'best',engine.best,'time',time.time()-engine.started,flush=True)
        trial+=1

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',type=int,required=True)
    parser.add_argument('--seed',type=int,default=1201)
    parser.add_argument('--seconds',type=int,default=900)
    args=parser.parse_args()
    run(args.case,args.seed,args.seconds)
