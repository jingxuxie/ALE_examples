from synth import *
from improve import best_insert
from gauge import refine

def run(case_index,seed,seconds):
    engine=Engine(case_index)
    rng=np.random.default_rng(seed)
    deadline=time.time()+seconds
    trial=0
    while time.time()<deadline:
        labels,angles=engine.load()
        removed=int(rng.integers(2,9))
        if trial%2:
            start=int(rng.integers(len(labels)-removed+1));positions=np.arange(start,start+removed)
        else:
            positions=np.sort(rng.choice(len(labels),size=removed,replace=False))
        selected=np.ones(len(labels),dtype=bool);selected[positions]=False
        labels=np.array(labels)[selected].tolist();angles=angles[selected]
        value,angles=engine.optimize(labels,angles,iterations=300)
        for added in range(removed):
            value,labels,angles=best_insert(engine,labels,angles,rng,limit=4)
        if trial%3==0:value,labels,angles=refine(engine,labels,angles,rng,steps=4)
        engine.save(labels,angles,value)
        print('NEIGHBOR',case_index,seed,trial,removed,value,'best',engine.best,'time',time.time()-engine.started,flush=True)
        trial+=1

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',type=int,required=True)
    parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--seconds',type=int,default=180)
    args=parser.parse_args()
    run(args.case,args.seed,args.seconds)
