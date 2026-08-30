import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json
import time
import itertools
from pathlib import Path
import numpy as np
from nominal import solve
from optimize import oracle
from search_nominal import canonical

COUNTS=[mask.bit_count() for mask in range(16)]

def configurations(syndrome,physical,limit=5):
    required=[sum(1<<(detector%4) for detector in syndrome if detector//4==column) for column in range(5)]
    suffix=np.zeros((6,16),dtype=int)
    for column in range(4,-1,-1):
        for incoming in range(16):
            suffix[column,incoming]=min(COUNTS[vert]+COUNTS[incoming^vert^(vert<<1)^required[column]]+suffix[column+1,incoming^vert^(vert<<1)^required[column]] for vert in range(8))
    found=[]
    def recurse(column,incoming,count,mask):
        if count+suffix[column,incoming]>limit:return
        if column==5:
            found.append(mask);return
        for vert in range(8):
            out=incoming^vert^(vert<<1)^required[column]
            recurse(column+1,out,count+COUNTS[vert]+COUNTS[out],mask|(vert<<(24+3*column))|(out<<(4*(column+1))))
    for incoming in range(16):
        if COUNTS[incoming]%2==physical:recurse(0,incoming,COUNTS[incoming],incoming)
    return found

def main():
    rng=np.random.default_rng(796154)
    known={}
    for path in Path('nominal_search').glob('*.json'):
        data=json.loads(path.read_text());key=tuple(data['syndrome']);score=float(path.stem.split('_')[1])
        if key not in known or score>known[key][0]:known[key]=(score,data)
    good=sorted(known,key=lambda key:-known[key][0])
    candidates=[]
    seen=set()
    for key in good:
        signature=canonical(key)
        if signature in seen:continue
        seen.add(signature);candidates.append(list(key))
    for count in (3,4):
        others=[]
        for syndrome in itertools.combinations(range(20),count):
            if len({detector%4 for detector in syndrome})<3 or len({detector//4 for detector in syndrome})<3:continue
            if syndrome==canonical(syndrome) and syndrome not in seen:others.append(list(syndrome))
        rng.shuffle(others);candidates.extend(others)
    directory=Path('nominal_search')
    started=time.time();attempt=0;best=0
    for index,syndrome in enumerate(candidates):
        for physical in range(2):
            for mask in configurations(syndrome,physical):
                selected=np.array([bool(mask>>edge&1) for edge in range(39)])
                probabilities=np.where(selected,.14,.02)
                current=oracle(np.array([probabilities]),syndrome,physical,False)[2][0,0]
                current_bits=((current>>np.arange(39,dtype=np.uint64))&1).astype(float)
                weights=np.log1p(-probabilities)-np.log(probabilities)
                if np.dot(weights,current_bits)<np.dot(weights,selected)-1e-8:continue
                for mode in range(2):
                    if mode:
                        if tuple(syndrome) in known:
                            probabilities=np.array(known[tuple(syndrome)][1]['probabilities'])
                            old=oracle(np.array([probabilities]),syndrome,physical,False)[2][0,0]
                            old_bits=((old>>np.arange(39,dtype=np.uint64))&1).astype(bool)
                            probabilities[old_bits & ~selected]=.02
                            probabilities[selected]=.14
                        else:probabilities=np.where(selected,.14,rng.uniform(.02,.08,39))
                    score,solution,result=solve(probabilities,syndrome,physical=physical,iterations=180)
                    if score>.98:
                        witness={'version':1,'probabilities':solution.tolist(),'syndrome':syndrome}
                        tag=os.environ.get('TAG','m')
                        (directory/f'{tag}{attempt}_{score:.8f}.json').write_text(json.dumps(witness))
                        print('candidate',attempt,syndrome,physical,score,flush=True)
                    if score>best:
                        best=score;print('BEST',attempt,syndrome,physical,score,round(time.time()-started,1),flush=True)
                    attempt+=1
        if index%10==0:print('progress',index,attempt,round(time.time()-started,1),flush=True)

if __name__=='__main__':main()
