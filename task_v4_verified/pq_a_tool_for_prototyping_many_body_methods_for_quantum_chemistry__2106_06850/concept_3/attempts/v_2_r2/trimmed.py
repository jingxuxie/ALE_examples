from synth import *
from compress import sparse_optimize

def run(case_index,seed,seconds):
    engine=Engine(case_index)
    rng=np.random.default_rng(seed)
    budget=engine.case.max_gates
    deadline=time.time()+seconds
    trial=0
    while time.time()<deadline:
        mode=(seed+trial)%4
        if mode==0:
            labels=list(range(250))
            angles=rng.normal(scale=0.04,size=len(labels))
        elif mode==1:
            labels=list(range(249,-1,-1))
            angles=rng.normal(scale=0.04,size=len(labels))
        else:
            old_labels,old_angles=engine.load()
            labels=[];parameters=[]
            for position,label in enumerate(old_labels):
                choices=list(range(250)) if mode==2 else rng.permutation(250).tolist()
                labels.extend(choices)
                parameters.extend([old_angles[position] if candidate==label else 0.0 for candidate in choices])
            angles=np.array(parameters)
            if trial%2:
                active=np.flatnonzero(angles)
                angles[active]+=rng.normal(scale=0.3,size=len(active))
        count=len(labels)
        best=1.0
        for stage in range(36):
            penalty=0.00002*(1.35**stage)
            keep=np.argsort(-abs(angles))[:budget]
            weights=np.ones(count);weights[keep]=0.0
            value,angles=sparse_optimize(engine,labels,angles,penalty,weights,iterations=160)
            active=np.flatnonzero(abs(angles)>1e-7)
            if stage%4==0 or len(active)<=budget:
                take=np.argsort(-abs(angles))[:budget];take.sort()
                chosen=np.array(labels)[take].tolist()
                loss,parameters=engine.optimize(chosen,angles[take],iterations=300)
                engine.save(chosen,parameters,loss)
                best=min(best,loss)
                print('TRIMMED',case_index,seed,trial,mode,stage,len(active),'soft',value,'hard',loss,'best',best,'time',time.time()-engine.started,flush=True)
            if len(active)<=budget:
                break
            if time.time()>deadline:break
        trial+=1

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',type=int,required=True)
    parser.add_argument('--seed',type=int,default=1101)
    parser.add_argument('--seconds',type=int,default=1000)
    args=parser.parse_args()
    run(args.case,args.seed,args.seconds)
