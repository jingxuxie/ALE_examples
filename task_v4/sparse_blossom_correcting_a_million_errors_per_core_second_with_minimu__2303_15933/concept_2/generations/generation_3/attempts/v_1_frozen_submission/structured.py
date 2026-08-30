import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
import itertools
import time
from pathlib import Path
import numpy as np
from nominal import solve

def main():
    rng=np.random.default_rng(991713)
    directory=Path('nominal_search');directory.mkdir(exist_ok=True)
    best=0
    started=time.time()
    candidates=list(itertools.product([1,2,3],[1,2],[1,2],list(itertools.combinations(range(4),2))))
    rng.shuffle(candidates)
    for attempt in range(5000):
        column,left_row,center_row,pair=candidates[attempt%len(candidates)]
        syndrome=sorted([left_row,4*column+center_row,16+pair[0],16+pair[1]])
        if len({detector%4 for detector in syndrome})<3:continue
        probabilities=np.full(39,.02)
        horizontal=probabilities[:24].reshape(6,4)
        vertical=probabilities[24:].reshape(5,3)
        horizontal[0]=.14
        vertical[0]=.14
        horizontal[0,left_row]=.025
        horizontal[1:column+1,center_row]=.1 if column==3 else .06
        horizontal[column+1:]=.14
        vertical[column:]=.14
        mode=rng.integers(4)
        if mode in (0,1):
            horizontal[-1]=.02
            horizontal[-1,center_row]=.1
            horizontal[-1,3-center_row]=.1
        if mode==1:
            low_rows=[row for row in range(4) if row not in (*pair,center_row)]
            for row in low_rows:horizontal[:,row]=.02
        if mode==3:probabilities=np.clip(probabilities+rng.normal(0,.03,39),.02,.14)
        score,solution,result=solve(probabilities,syndrome,physical=0,iterations=200)
        if score>.98:
            witness={'version':1,'probabilities':solution.tolist(),'syndrome':syndrome}
            (directory/f't{attempt}_{score:.8f}.json').write_text(json.dumps(witness))
            print('candidate',attempt,syndrome,score,result.success,flush=True)
        if score>best:
            best=score;print('BEST',attempt,syndrome,score,round(time.time()-started,1),flush=True)
        if attempt%100==0:print('progress',attempt,round(time.time()-started,1),flush=True)

if __name__=='__main__':main()
