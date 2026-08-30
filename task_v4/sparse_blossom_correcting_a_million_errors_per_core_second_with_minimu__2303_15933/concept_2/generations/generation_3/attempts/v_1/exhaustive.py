import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
import time
import itertools
from pathlib import Path
import numpy as np
from nominal import solve,PARTICIPANT
from optimize import oracle
from search_nominal import canonical

def main():
    rng=np.random.default_rng(533116)
    baseline=np.array(json.loads((PARTICIPANT/'baseline/champion.json').read_text())['probabilities'])
    candidates=[]
    for count in (3,4):
        for syndrome in itertools.combinations(range(20),count):
            if len({detector%4 for detector in syndrome})<3 or len({detector//4 for detector in syndrome})<3:continue
            if syndrome==canonical(syndrome):candidates.append(list(syndrome))
    rng.shuffle(candidates)
    directory=Path('nominal_search')
    best=0;started=time.time()
    for round_index in range(8):
        for index,syndrome in enumerate(candidates):
            for physical in range(2):
                mode=round_index%4
                if mode==0:probabilities=rng.uniform(.02,.14,39)
                elif mode==1:probabilities=np.where(rng.random(39)<.5,.14,.02)
                elif mode==2:
                    masks=oracle(np.full((1,39),.1),syndrome,physical,False)[2]
                    selected=((masks[0,0]>>np.arange(39,dtype=np.uint64))&1).astype(bool)
                    probabilities=rng.uniform(.10,.14,39)
                    probabilities[selected]=1/(1+np.exp(rng.uniform(8,12)/selected.sum()))
                    probabilities=np.clip(probabilities,.02,.14)
                else:probabilities=np.clip(baseline+rng.normal(0,.05,39),.02,.14)
                score,solution,result=solve(probabilities,syndrome,physical=physical,iterations=160)
                if score>.98:
                    witness={'version':1,'probabilities':solution.tolist(),'syndrome':syndrome}
                    (directory/f'e{round_index}-{index}-{physical}_{score:.8f}.json').write_text(json.dumps(witness))
                    print('candidate',round_index,index,physical,syndrome,score,flush=True)
                if score>best:
                    best=score;print('BEST',round_index,index,physical,syndrome,score,round(time.time()-started,1),flush=True)
            if index%100==0:print('progress',round_index,index,round(time.time()-started,1),flush=True)

if __name__=='__main__':main()
