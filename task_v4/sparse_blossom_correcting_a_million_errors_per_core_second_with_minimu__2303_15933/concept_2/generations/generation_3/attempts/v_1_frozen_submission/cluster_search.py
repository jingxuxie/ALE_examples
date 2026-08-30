import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
import itertools
import time
from pathlib import Path
import numpy as np
from nominal import solve,PARTICIPANT

def main():
    graph=json.loads((PARTICIPANT/'input/graph.json').read_text())
    edges=[edge for edge in graph['edges'] if len(edge['detectors'])==2 and min(edge['detectors'])>=12]
    motifs=[]
    for row in range(4):
        for first,second in itertools.combinations(edges,2):
            right=[12+row,*first['detectors'],*second['detectors']]
            if len(set(right))==5:motifs.append((row,first['id'],second['id'],sorted([row,*right])))
    rng=np.random.default_rng(80912)
    rng.shuffle(motifs)
    directory=Path('nominal_search')
    print('motifs',len(motifs),flush=True)
    best=0;started=time.time()
    for attempt in range(10000):
        row,first,second,syndrome=motifs[attempt%len(motifs)]
        probabilities=np.full(39,.02)
        horizontal=probabilities[:24].reshape(6,4)
        vertical=probabilities[24:].reshape(5,3)
        horizontal[0]=.14;horizontal[0,row]=.0245
        vertical[0]=.14
        horizontal[1:4,row]=.1
        horizontal[4:]=.14
        vertical[3:]=.14
        horizontal[5]=.02
        mode=rng.integers(5)
        if mode<4:horizontal[5,mode]=.14
        if attempt%3==0:probabilities=np.clip(probabilities+rng.normal(0,.035,39),.02,.14)
        probabilities[[first,second]]=.14
        score,solution,result=solve(probabilities,syndrome,physical=0,iterations=200)
        if score>.96:
            witness={'version':1,'probabilities':solution.tolist(),'syndrome':syndrome}
            (directory/f'f{attempt}_{score:.8f}.json').write_text(json.dumps(witness))
            print('candidate',attempt,syndrome,score,flush=True)
        if score>best:
            best=score;print('BEST',attempt,syndrome,score,round(time.time()-started,1),flush=True)
        if attempt%100==0:print('progress',attempt,round(time.time()-started,1),flush=True)

if __name__=='__main__':main()
