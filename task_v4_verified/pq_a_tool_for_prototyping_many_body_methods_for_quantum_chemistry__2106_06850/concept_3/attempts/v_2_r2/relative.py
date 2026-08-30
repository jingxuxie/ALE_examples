from synth import *

def run(seed=0,width=48):
    engine=Engine(0)
    cases=load_cases()
    left=cases[0].target[engine.keep].copy()
    if seed==0:
        right=cases[1].target[engine.keep].copy()
    else:
        lookup={mask:value for mask,value in zip(cases[2].determinants,cases[2].target)}
        right=np.array([lookup[int(format(1023^cases[0].determinants[index],'010b')[::-1],2)] for index in engine.keep])
    engine.setup(reference=left,target=right)
    states=[(float(np.sum((left-right)**2)/2),[],np.zeros(0))]
    print('RELATIVE initial',seed,states[0][0],flush=True)
    for depth in range(4 if seed==0 else 8):
        pool=[]
        for old_value,labels,angles in states:
            values,guesses=engine.scan(labels,angles)
            order=np.argsort(values[-1])
            for label in order[:250 if depth<3 else 80]:
                proposal=labels+[int(label)]
                parameters=np.append(angles,guesses[-1,label])
                value,parameters=engine.optimize(proposal,parameters,iterations=100)
                pool.append((value,proposal,parameters))
        pool.sort(key=lambda item:item[0])
        states=[]; seen=set()
        for value,labels,angles in pool:
            state=engine.state(labels,angles)
            key=tuple(np.round(state,7))
            if key in seen:continue
            seen.add(key); states.append((value,labels,angles))
            if len(states)>=width:break
        print('RELATIVE',seed,depth+1,states[0][0],states[0][1],states[0][2].tolist(),time.time()-engine.started,flush=True)
        if states[0][0]<1e-11:
            engine.save(states[0][1],states[0][2],states[0][0],tag=f'relative_{seed}')
            break

if __name__=='__main__':
    import sys
    run(int(sys.argv[1]))
