import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
import itertools
import time
from pathlib import Path
import numpy as np
from nominal import solve
from search_nominal import canonical

def main():
    data=json.loads(Path('robust_best.json').read_text())
    base=np.array(data['probabilities'])
    rng=np.random.default_rng(5126)
    candidates=[list(syndrome) for syndrome in itertools.combinations(range(20),3) if len({detector%4 for detector in syndrome})==3 and len({detector//4 for detector in syndrome})==3]
    directory=Path('nominal_search')
    best=0;started=time.time()
    favored=[[1,14,16],[1,12,18],[2,13,19],[2,15,17],[1,15,16],[2,12,19]]
    for attempt in range(10000):
        syndrome=favored[rng.integers(len(favored))] if attempt%3 else candidates[rng.integers(len(candidates))]
        probabilities=base.copy()
        if attempt%4==0:probabilities=rng.uniform(.02,.14,39)
        else:probabilities=np.clip(probabilities+rng.normal(0,.012*(attempt%5),39),.02,.14)
        if attempt%4==1:
            probabilities[:24].reshape(6,4)[:,:3]=probabilities[:24].reshape(6,4)[:,:3][:,::-1]
            probabilities[24:].reshape(5,3)[:,:2]=probabilities[24:].reshape(5,3)[:,:2][:,::-1]
        score,solution,result=solve(probabilities,syndrome,physical=0 if attempt%3 else int(rng.integers(2)),iterations=180)
        if score>.98:
            witness={'version':1,'probabilities':solution.tolist(),'syndrome':syndrome}
            (directory/f'u{attempt}_{score:.8f}.json').write_text(json.dumps(witness))
            print('candidate',attempt,syndrome,score,flush=True)
        if score>best:
            best=score;print('BEST',attempt,syndrome,score,round(time.time()-started,1),flush=True)
        if attempt%100==0:print('progress',attempt,round(time.time()-started,1),flush=True)

if __name__=='__main__':main()
