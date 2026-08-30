import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OMP_NUM_THREADS']='1'
os.environ['OPENBLAS_NUM_THREADS']='1'
from synth import *
import torch
torch.set_num_threads(1)

def run(case_index,seed,seconds):
    engine=Engine(case_index)
    rng=np.random.default_rng(seed)
    torch.manual_seed(seed)
    dtype=torch.float64
    sources=torch.tensor(engine.sources,dtype=torch.long)
    destinations=torch.tensor(engine.destinations,dtype=torch.long)
    signs=torch.tensor(engine.signs,dtype=dtype)
    mask=(signs!=0).to(dtype)
    reference=torch.tensor(engine.reference,dtype=dtype)
    target=torch.tensor(engine.target,dtype=dtype)
    count=engine.case.max_gates
    deadline=time.time()+seconds
    trial=0
    while time.time()<deadline:
        labels,angles=engine.load()
        if trial%3==2:
            labels=rng.integers(250,size=count).tolist()
            angles=rng.normal(scale=0.7,size=count)
        logits=torch.nn.Parameter(torch.tensor(rng.normal(scale=0.2,size=(count,250)),dtype=dtype))
        parameters=torch.nn.Parameter(torch.tensor(rng.normal(scale=0.7,size=(count,250)),dtype=dtype))
        with torch.no_grad():
            for position,(label,angle) in enumerate(zip(labels,angles)):
                logits[position,label]=rng.uniform(3.0,6.0)
                parameters[position,label]=angle
        optimizer=torch.optim.Adam([logits,parameters],lr=0.025)
        best=1.0
        steps=1600
        for step in range(steps):
            progress=step/(steps-1)
            temperature=1.5*(0.12/1.5)**progress
            probabilities=torch.softmax(logits/temperature,dim=1)
            state=reference
            for position in range(count):
                cosine=torch.cos(parameters[position])[:,None]
                sine=torch.sin(parameters[position])[:,None]
                left=state[sources]; right=state[destinations]
                change_left=((cosine-1)*left-signs*sine*right)*mask*probabilities[position,:,None]
                change_right=((cosine-1)*right+signs*sine*left)*mask*probabilities[position,:,None]
                state=state.index_add(0,sources.flatten(),change_left.flatten()).index_add(0,destinations.flatten(),change_right.flatten())
                state=state/torch.linalg.norm(state)
            loss=0.5*torch.sum((state-target)**2)
            entropy=-torch.sum(probabilities*torch.log(probabilities+1e-30))/count
            penalty=0.005+0.5*progress**3
            objective=loss+penalty*entropy
            optimizer.zero_grad()
            objective.backward()
            torch.nn.utils.clip_grad_norm_([logits,parameters],2.0)
            optimizer.step()
            if step%200==0 or step==steps-1:
                selected=torch.argmax(logits,dim=1).detach().numpy().tolist()
                selected_angles=parameters.detach().numpy()[np.arange(count),selected].copy()
                value,selected_angles=engine.optimize(selected,selected_angles,iterations=250)
                engine.save(selected,selected_angles,value)
                best=min(best,value)
                print('SOFT',case_index,seed,trial,step,float(loss),float(entropy),'hard',value,'best',best,flush=True)
            if time.time()>deadline:break
        trial+=1

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',type=int,required=True)
    parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--seconds',type=int,default=900)
    args=parser.parse_args()
    run(args.case,args.seed,args.seconds)
