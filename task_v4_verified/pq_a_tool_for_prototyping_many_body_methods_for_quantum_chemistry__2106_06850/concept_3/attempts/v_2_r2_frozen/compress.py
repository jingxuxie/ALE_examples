from synth import *

def sparse_optimize(engine,labels,angles,penalty,weights,iterations=500):
    labels=np.asarray(labels,dtype=np.int32)
    count=len(labels)
    gradient=np.empty(count)
    split=np.concatenate((np.maximum(angles,0),np.maximum(-angles,0)))
    weights=np.asarray(weights)
    def objective(parameters):
        angles=np.ascontiguousarray(parameters[:count]-parameters[count:])
        value=LIB.fungrad(count,labels,angles,gradient)
        regularizer=penalty*np.dot(weights,parameters[:count]+parameters[count:])
        return value+regularizer,np.concatenate((gradient+penalty*weights,-gradient+penalty*weights))
    result=minimize(objective,split,jac=True,method='L-BFGS-B',bounds=[(0,None)]*(2*count),options={'maxiter':iterations,'ftol':1e-13,'gtol':1e-8,'maxcor':30,'maxls':30})
    angles=result.x[:count]-result.x[count:]
    value=LIB.fungrad(count,labels,angles,gradient)
    return value,angles

def run(case_index,seed,seconds):
    engine=Engine(case_index)
    rng=np.random.default_rng(seed)
    deadline=time.time()+seconds
    cycle=0
    while time.time()<deadline:
        if cycle%2==0:
            labels=[]
            for layer in range(3):labels.extend(rng.permutation(250).tolist())
            angles=rng.normal(scale=0.07,size=len(labels))
        else:
            old_labels,old_angles=engine.load()
            labels=[]; parameters=[]
            for position,label in enumerate(old_labels):
                additions=rng.choice(250,size=15,replace=False).tolist()
                labels.extend(additions+[label]); parameters.extend([0.0]*len(additions)+[old_angles[position]])
            angles=np.array(parameters)
        value,angles=engine.optimize(labels,angles,iterations=600)
        print('DENSE',case_index,seed,cycle,len(labels),value,flush=True)
        weights=np.ones(len(labels))
        for stage in range(20):
            penalty=0.002 if stage<2 else 0.0001
            value,angles=sparse_optimize(engine,labels,angles,penalty,weights,iterations=800)
            active=abs(angles)>1e-7
            labels=np.asarray(labels)[active].tolist(); angles=angles[active]
            weights=1/(abs(angles)+0.015)
            print('SPARSE',case_index,seed,cycle,stage,len(labels),value,'l1',sum(abs(angles)),flush=True)
            if len(labels)<=engine.case.max_gates:
                loss,parameters=engine.optimize(labels,angles,iterations=500,precise=True)
                engine.save(labels,parameters,loss)
                break
            if stage%3==2:
                take=np.argsort(-abs(angles))[:engine.case.max_gates]
                take.sort()
                chosen=[labels[position] for position in take]
                loss,parameters=engine.optimize(chosen,angles[take],iterations=500)
                engine.save(chosen,parameters,loss)
                print('TRIM',case_index,seed,cycle,stage,loss,flush=True)
            if time.time()>deadline:break
        cycle+=1

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',type=int,required=True)
    parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--seconds',type=int,default=1000)
    args=parser.parse_args()
    run(args.case,args.seed,args.seconds)
