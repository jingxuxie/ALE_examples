import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import sys
import json
import time
import numpy as np
from permutation_search import evaluate
from search import OUT,save

random=np.random.default_rng(int(sys.argv[1]))
started=time.time()

def main():
    replicas=64
    temperatures=np.geomspace(.0001,.02,replicas)
    filename=['critical_best_698.json','single_best_921.json','structured_best.json'][int(sys.argv[1])%3]
    base=np.array(json.loads((OUT/filename).read_text())['fields'],dtype=np.int8)
    fields=np.repeat(base[None],replicas,axis=0)
    values,weights=evaluate(fields)
    best=float(values.min())
    for step in range(1000000):
        if step%100==0 and ((OUT/'witness.json').exists() or (OUT/'STOP_TEMPER').exists()):
            return
        candidates=fields.copy()
        move=random.random()
        if move<.55:
            positions=random.integers(256,size=replicas)
            candidates.reshape(replicas,256)[np.arange(replicas),positions]*=-1
        elif move<.75:
            sites=random.integers(16,size=replicas)
            offsets=random.choice([-2,-1,1,2],size=replicas)
            for replica in range(replicas):
                candidates[replica,:,sites[replica]]=np.roll(candidates[replica,:,sites[replica]],offsets[replica])
        elif move<.9:
            sites=random.integers(16,size=replicas)
            begins=random.integers(16,size=replicas)
            length=int(random.integers(2,5))
            for offset in range(length):
                candidates[np.arange(replicas),(begins+offset)%16,sites]*=-1
        else:
            pairs=random.integers(16,size=(replicas,2))
            for replica,pair in enumerate(pairs):
                if step%2:
                    candidates[replica][:,pair]=candidates[replica][:,pair[::-1]]
                else:
                    candidates[replica][pair]=candidates[replica][pair[::-1]]
        scores,weights=evaluate(candidates)
        negative=np.flatnonzero(weights<-1e-7)
        if len(negative):
            save(candidates[negative[0]])
            print('FOUND',step,weights[negative[0]],flush=True)
            return
        accepted=np.log(random.random(replicas))<(values-scores)/temperatures
        fields[accepted]=candidates[accepted]
        values[accepted]=scores[accepted]
        if values.min()<best-1e-10:
            best=float(values.min())
            save(fields[np.argmin(values)],'temper_best_'+sys.argv[1]+'.json')
            print(f'{time.time()-started:.2f}s step={step} best={best:.12g}',flush=True)
        if step%10==0:
            for left in range((step//10)%2,replicas-1,2):
                right=left+1
                log_accept=(1/temperatures[left]-1/temperatures[right])*(values[left]-values[right])
                if np.log(random.random())<log_accept:
                    fields[[left,right]]=fields[[right,left]]
                    values[[left,right]]=values[[right,left]]
        if step%2000==0:
            print(f'{time.time()-started:.2f}s step={step} min={values.min():.12g} max={values.max():.12g} best={best:.12g}',flush=True)

if __name__=='__main__':
    main()
