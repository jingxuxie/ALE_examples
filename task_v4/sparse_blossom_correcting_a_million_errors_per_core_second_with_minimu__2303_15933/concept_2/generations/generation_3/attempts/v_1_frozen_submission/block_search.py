import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
import itertools
import time
from pathlib import Path
import numpy as np
from nominal import solve

def main():
    rng=np.random.default_rng(812514)
    motifs=[]
    for left,center,paircol in itertools.combinations(range(5),3):
        for row in range(4):
            for pairrows in itertools.combinations([other for other in range(4) if other!=row],2):
                motifs.append((left,center,paircol,row,pairrows))
    rng.shuffle(motifs)
    directory=Path('nominal_search')
    best=0;started=time.time()
    for attempt in range(10000):
        left,center,paircol,row,pairrows=motifs[attempt%len(motifs)]
        syndrome=sorted([4*left+row,4*center+row,4*paircol+pairrows[0],4*paircol+pairrows[1]])
        probabilities=np.full(39,.02)
        horizontal=probabilities[:24].reshape(6,4)
        vertical=probabilities[24:].reshape(5,3)
        rows=slice(min(row,*pairrows),max(row,*pairrows)+1)
        vertical_rows=slice(min(row,*pairrows),max(row,*pairrows))
        horizontal[:left+1,rows]=.14
        vertical[:left+1,vertical_rows]=.14
        horizontal[0,row]=.025
        horizontal[left+1:center+1,row]=.05 if center-left==2 else .1
        horizontal[center+1:,rows]=.14
        vertical[center:,vertical_rows]=.14
        mode=rng.integers(5)
        if paircol==4 and mode<4:
            horizontal[5,pairrows[0]]=.02
            horizontal[5,pairrows[1]]=.02
        if mode==1:
            horizontal[center+1:,3]=.14
            vertical[center:,2]=.14
        elif mode==2:
            horizontal[center+1:,0]=.14
            vertical[center:,0]=.14
        elif mode==3:
            horizontal[:left+1]=.14
            vertical[:left+1]=.14
            horizontal[0,row]=.025
        elif mode==4:
            probabilities=np.clip(probabilities+rng.normal(0,.04,39),.02,.14)
        score,solution,result=solve(probabilities,syndrome,physical=0,iterations=220)
        if score>.98:
            witness={'version':1,'probabilities':solution.tolist(),'syndrome':syndrome}
            (directory/f'z{attempt}_{score:.8f}.json').write_text(json.dumps(witness))
            print('candidate',attempt,syndrome,score,flush=True)
        if score>best:
            best=score;print('BEST',attempt,syndrome,score,round(time.time()-started,1),flush=True)
        if attempt%100==0:print('progress',attempt,round(time.time()-started,1),flush=True)

if __name__=='__main__':main()
