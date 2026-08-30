import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
import time
import itertools
from pathlib import Path
import numpy as np
from nominal import solve,PARTICIPANT

def main():
    graph=json.loads((PARTICIPANT/'input/graph.json').read_text())
    incidence=[sum(1<<detector for detector in edge['detectors']) for edge in graph['edges']]
    rng=np.random.default_rng(22715)
    edges=list(range(4,20))+list(range(24,39))
    choices=[]
    for boundary in range(4):
        for first,second in itertools.combinations(edges,2):
            mask=incidence[boundary]^incidence[first]^incidence[second]
            syndrome=[detector for detector in range(20) if mask>>detector&1]
            if 3<=len(syndrome)<=6 and len({detector%4 for detector in syndrome})>=3 and len({detector//4 for detector in syndrome})>=3:
                choices.append((boundary,first,second,syndrome))
    rng.shuffle(choices)
    out=Path('nominal_search');out.mkdir(exist_ok=True)
    best=0;started=time.time()
    for attempt in range(10000):
        boundary,first,second,syndrome=choices[attempt%len(choices)]
        probabilities=np.full(39,.14)
        probabilities[:4]=.02
        probabilities[[boundary,first,second]]=rng.uniform(.025,.06)
        mode=rng.integers(4)
        if mode==0:
            probabilities[:24].reshape(6,4)[:,3]=.02
            probabilities[24:].reshape(5,3)[:,2]=.02
        elif mode==1:
            probabilities[:24].reshape(6,4)[:,0]=.02
            probabilities[24:].reshape(5,3)[:,0]=.02
        elif mode==3:
            probabilities=np.clip(probabilities+rng.normal(0,.04,39),.02,.14)
        score,solution,result=solve(probabilities,syndrome,physical=1,iterations=200)
        if score>.98:
            witness={'version':1,'probabilities':solution.tolist(),'syndrome':syndrome}
            (out/f'p{attempt}_{score:.8f}.json').write_text(json.dumps(witness))
            print('candidate',attempt,syndrome,score,flush=True)
        if score>best:
            best=score;print('BEST',attempt,syndrome,[boundary,first,second],score,round(time.time()-started,1),flush=True)
        if attempt%100==0:print('progress',attempt,round(time.time()-started,1),flush=True)

if __name__=='__main__':main()
