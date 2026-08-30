import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import json
import sys
import time
import numpy as np
from search import OUT,BETA,COUPLING,PROPAGATOR,save,evaluate

def response(fields,positions):
    responses=[]
    for spin in [1,-1]:
        action=np.eye(256)
        updates=np.zeros((256,len(positions)))
        selectors=[]
        matrices=np.exp(BETA/16)*PROPAGATOR[None]*np.exp(spin*COUPLING*fields[:,None,:])
        for time_index in range(16):
            previous=(time_index-1)%16
            block=matrices[time_index]*(1 if time_index==0 else -1)
            action[16*time_index:16*(time_index+1),16*previous:16*(previous+1)]=block
        alphas=[]
        for index,(time_index,site) in enumerate(positions):
            previous=(time_index-1)%16
            updates[16*time_index:16*(time_index+1),index]=action[16*time_index:16*(time_index+1),16*previous+site]
            selectors.append(16*previous+site)
            alphas.append(np.exp(-2*spin*COUPLING*fields[time_index,site])-1)
        solved=np.linalg.solve(action,updates)
        responses.append(np.eye(len(positions))+solved[selectors]*np.array(alphas)[None])
    return np.array(responses)

def main():
    started=time.time()
    filename=sys.argv[1] if len(sys.argv)>1 else 'structured_best.json'
    fields=np.array(json.loads((OUT/filename).read_text())['fields'],dtype=np.int8)
    positions=[]
    for site in range(16):
        begin=np.flatnonzero((fields[:,site]>0)&(np.roll(fields[:,site],1)<0))
        end=np.flatnonzero((fields[:,site]>0)&(np.roll(fields[:,site],-1)<0))
        assert len(begin)==1 and len(end)==1
        positions.extend([((int(begin[0])-1)%16,site),((int(end[0])+1)%16,site)])
    responses=response(fields,positions)
    random=np.random.default_rng(931)
    for trial in range(20):
        choices=random.integers(0,3,size=16)
        selected=2*np.flatnonzero(choices)+choices[choices!=0]-1
        signs=np.prod(np.linalg.slogdet(responses[:,selected[:,None],selected[None,:]])[0])
        varied=fields.copy()
        for index in selected:
            varied[positions[index]]*=-1
        assert signs==np.sign(evaluate(varied)[0])
    print('response checks passed',flush=True)
    powers=3**np.arange(16,dtype=np.int64)
    total=3**16
    for start in range(0,total,8192):
        if (OUT/'witness.json').exists() or (OUT/'STOP_BOUNDARY').exists():
            return
        codes=np.arange(start,min(start+8192,total))
        choices=(codes[:,None]//powers[None])%3
        counts=np.count_nonzero(choices,axis=1)
        for count in range(1,17):
            rows=np.flatnonzero(counts==count)
            if not len(rows):
                continue
            choices_part=choices[rows]
            sites=np.nonzero(choices_part)[1].reshape(-1,count)
            selected=2*sites+choices_part[choices_part!=0].reshape(-1,count)-1
            signs=np.ones(len(rows))
            for spin in range(2):
                signs*=np.linalg.slogdet(responses[spin,selected[:,:,None],selected[:,None,:]])[0]
            negative=np.flatnonzero(signs<0)
            if len(negative):
                varied=fields.copy()
                for index in selected[negative[0]]:
                    varied[positions[index]]*=-1
                score=evaluate(varied)[0]
                print('FOUND',filename,'code',codes[rows[negative[0]]],'score',score,flush=True)
                save(varied)
                return
        if start%(8192*100)==0:
            print(f'{time.time()-started:.2f}s done={start} total={total}',flush=True)
    print('exhausted',flush=True)

if __name__=='__main__':
    main()
