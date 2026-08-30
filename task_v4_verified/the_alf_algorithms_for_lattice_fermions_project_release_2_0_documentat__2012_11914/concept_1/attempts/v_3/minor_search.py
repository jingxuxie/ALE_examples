import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import json
import sys
import time
import numpy as np
from boundary_search import response
from search import OUT,evaluate,save

random=np.random.default_rng(int(sys.argv[1]))
started=time.time()

def main():
    for epoch in range(500):
        filename=['structured_best.json','critical_best_698.json','single_best_921.json'][epoch%3]
        fields=np.array(json.loads((OUT/filename).read_text())['fields'],dtype=np.int8)
        if epoch%2==0:
            positions=[]
            for site in range(16):
                boundaries=np.flatnonzero(fields[:,site]!=np.roll(fields[:,site],1))
                for boundary in boundaries:
                    positions.extend([((int(boundary)+offset)%16,site) for offset in [-1,0]])
            positions=list(dict.fromkeys(positions))
        else:
            positions=[(time_index,site) for time_index in range(16) for site in range(16)]
        matrices=response(fields,positions)
        normalization=np.log(np.abs(np.diagonal(matrices,axis1=1,axis2=2))).sum(axis=0)
        size=len(positions)
        best=100
        for restart in range(200):
            if (OUT/'witness.json').exists() or (OUT/'STOP_MINOR').exists():
                return
            count=int(random.choice([6,8,10,12,16,20,24]))
            selected=random.choice(size,size=count,replace=False)
            current=np.inf
            for iteration in range(150):
                neighbors=np.repeat(selected[None],256,axis=0)
                outside=np.setdiff1d(np.arange(size),selected)
                replace=random.integers(count,size=len(neighbors))
                neighbors[np.arange(len(neighbors)),replace]=random.choice(outside,size=len(neighbors))
                signs=np.ones(len(neighbors))
                scores=-normalization[neighbors].sum(axis=1)
                for spin in range(2):
                    sign,logabs=np.linalg.slogdet(matrices[spin,neighbors[:,:,None],neighbors[:,None,:]])
                    signs*=sign
                    scores+=logabs
                for index in np.flatnonzero(signs<0):
                    varied=fields.copy()
                    for position in neighbors[index]:
                        varied[positions[position]]*=-1
                    score=evaluate(varied)[0]
                    if score < -1e-7:
                        save(varied)
                        print('FOUND',epoch,restart,iteration,score,flush=True)
                        return
                    scores[index]=np.inf
                chosen=np.argmin(scores)
                if scores[chosen]>=current-1e-9:
                    break
                selected=neighbors[chosen].copy()
                current=scores[chosen]
                if current<best:
                    best=current
                    print(f'{time.time()-started:.2f}s epoch={epoch} restart={restart} iteration={iteration} flips={count} best_log={best:.12g}',flush=True)
            if restart%50==0:
                print(f'{time.time()-started:.2f}s epoch={epoch} restart={restart} log={current:.12g}',flush=True)

if __name__=='__main__':
    main()
