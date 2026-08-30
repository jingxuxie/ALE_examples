import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
import time
import itertools
from pathlib import Path
import numpy as np
from nominal import solve
from optimize import oracle
from map_search import configurations
from search_nominal import canonical

def main():
    started=time.time();seeds=[]
    count=int(os.environ.get('COUNT','5'))
    per_physical=int(os.environ.get('PER_PHYSICAL','2'))
    candidates=[list(syndrome) for syndrome in itertools.combinations(range(20),count) if len({detector%4 for detector in syndrome})>=3 and len({detector//4 for detector in syndrome})>=3 and syndrome==canonical(syndrome)]
    for index,syndrome in enumerate(candidates):
        for physical in range(2):
            masks=np.array(configurations(syndrome,physical),dtype=np.uint64)
            if not len(masks):continue
            selected=((masks[:,None]>>np.arange(39,dtype=np.uint64))&1).astype(bool)
            probabilities=np.where(selected,.14,.02)
            values,jac,current=oracle(probabilities,syndrome,physical,False)
            current_bits=((current[:,0,None]>>np.arange(39,dtype=np.uint64))&1).astype(float)
            weights=np.log1p(-probabilities)-np.log(probabilities)
            valid=np.sum(weights*(current_bits-selected),axis=1)>-1e-8
            entropy=values[:,0]+values[:,1]
            entropy[~valid]=-1e10
            for choice in np.argsort(entropy)[-per_physical:]:
                if not valid[choice]:continue
                seeds.append((float(entropy[choice]),syndrome,physical,int(masks[choice])))
        if index%200==0:print('prepare',index,len(seeds),round(time.time()-started,1),flush=True)
    seeds.sort(reverse=True)
    print('prepared',len(seeds),round(time.time()-started,1),flush=True)
    directory=Path('nominal_search');best=0
    for attempt,(entropy,syndrome,physical,mask) in enumerate(seeds):
        selected=np.array([bool(mask>>edge&1) for edge in range(39)])
        probabilities=np.where(selected,.14,float(os.environ.get('BACKGROUND','.02')))
        score,solution,result=solve(probabilities,syndrome,physical=physical,iterations=160)
        if score>.96:
            witness={'version':1,'probabilities':solution.tolist(),'syndrome':syndrome}
            tag=os.environ.get('TAG','g')
            (directory/f'{tag}{attempt}_{score:.8f}.json').write_text(json.dumps(witness))
            print('candidate',attempt,syndrome,physical,score,flush=True)
        if score>best:
            best=score;print('BEST',attempt,syndrome,physical,score,entropy,round(time.time()-started,1),flush=True)
        if attempt%100==0:print('progress',attempt,round(time.time()-started,1),flush=True)

if __name__=='__main__':main()
