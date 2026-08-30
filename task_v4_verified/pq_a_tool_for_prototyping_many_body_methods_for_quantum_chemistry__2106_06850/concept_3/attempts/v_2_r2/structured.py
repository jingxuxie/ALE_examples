from synth import *

def run(case_index,seed,seconds):
    engine=Engine(case_index)
    rng=np.random.default_rng(seed)
    occupied={orbital for orbital in range(10) if engine.case.reference_mask>>orbital&1}
    hf=[index for index,label in enumerate(engine.labels) if set(label.annihilate)<=occupied and not set(label.create)&occupied]
    paired=[index for index,label in enumerate(engine.labels) if len(label.annihilate)==1 or (label.annihilate[0]//2==label.annihilate[1]//2 and label.create[0]//2==label.create[1]//2)]
    singles=list(range(20))
    near=[index for index,label in enumerate(engine.labels) if (len(label.annihilate)==1 and label.create[0]-label.annihilate[0]==2) or (len(label.annihilate)==2 and label.annihilate[0]//2==label.annihilate[1]//2 and label.create[0]//2==label.create[1]//2 and label.create[0]-label.annihilate[0]==2)]
    patterns=[hf,hf[::-1],sorted(hf,key=lambda index:(-len(engine.labels[index].annihilate),index)),paired,paired[::-1],near*2,near*3]
    deadline=time.time()+seconds
    trial=0
    while time.time()<deadline:
        pattern=trial%len(patterns)
        labels=patterns[pattern].copy()
        if trial//len(patterns)%4==3:rng.shuffle(labels)
        angles=rng.normal(scale=[0.1,0.4,0.9,1.5][trial//len(patterns)%4],size=len(labels))
        value,angles=engine.optimize(labels,angles,iterations=1000,precise=True)
        print('STRUCT',case_index,seed,trial,pattern,len(labels),value,flush=True)
        if value<1e-10:
            active=abs(angles)>1e-5
            chosen=np.array(labels)[active].tolist(); parameters=angles[active]
            loss,parameters=engine.optimize(chosen,parameters,precise=True)
            print('EXACT',case_index,len(chosen),loss,flush=True)
            engine.save(chosen,parameters,loss,tag=f'exact_{seed}')
            if len(chosen)<=engine.case.max_gates:engine.save(chosen,parameters,loss)
        if len(labels)<=engine.case.max_gates:engine.save(labels,angles,value)
        trial+=1

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',type=int,required=True)
    parser.add_argument('--seed',type=int,default=401)
    parser.add_argument('--seconds',type=int,default=600)
    args=parser.parse_args()
    run(args.case,args.seed,args.seconds)
