import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import ctypes
import json
import time
from pathlib import Path
import numpy as np
from nominal import solve,PARTICIPANT
from optimize import LIB,POINTER

LIB.scan.argtypes=[POINTER,ctypes.c_int,ctypes.POINTER(ctypes.c_int),POINTER]
LIB.scan_mode.argtypes=LIB.scan.argtypes+[ctypes.c_int,ctypes.POINTER(ctypes.c_int)]

def scan(probabilities,keep=30):
    probabilities=np.ascontiguousarray(probabilities,dtype=np.float64)
    syndromes=np.empty(keep,dtype=np.int32)
    scores=np.empty(keep)
    LIB.scan(probabilities.ctypes.data_as(POINTER),keep,syndromes.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),scores.ctypes.data_as(POINTER))
    return [[detector for detector in range(20) if mask>>detector&1] for mask in syndromes],scores

def main():
    baseline=json.loads((PARTICIPANT/'baseline/champion.json').read_text())
    rng=np.random.default_rng(8617)
    directory=Path('nominal_search');directory.mkdir(exist_ok=True)
    pool=[np.array(baseline['probabilities'])]
    best=0
    mode=int(os.environ.get('SCANMODE','0'))
    if mode:rng=np.random.default_rng(72166)
    started=time.time()
    for attempt in range(4000):
        if attempt==0:probabilities=pool[0]
        elif attempt%3==0:
            probabilities=np.clip(pool[rng.integers(len(pool))]+rng.normal(0,.025+.003*(attempt%15),39),.02,.14)
        elif attempt%3==1:
            probabilities=rng.uniform(.02,.14,39)
        else:
            probabilities=np.where(rng.random(39)<rng.uniform(.25,.65),.14,.02)
            probabilities=np.clip(probabilities+rng.normal(0,.01,39),.02,.14)
        syndromes,scores=scan(probabilities)
        physicals=[None]*len(syndromes)
        if mode:
            codes=np.empty(30,dtype=np.int32);physicals=np.empty(30,dtype=np.int32);scores=np.empty(30)
            LIB.scan_mode(probabilities.ctypes.data_as(POINTER),30,codes.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),scores.ctypes.data_as(POINTER),mode,physicals.ctypes.data_as(ctypes.POINTER(ctypes.c_int)))
            syndromes=[[detector for detector in range(20) if mask>>detector&1] for mask in codes]
        for rank,syndrome in enumerate(syndromes[:8]):
            score,solution,result=solve(probabilities,syndrome,physical=physicals[rank],iterations=160)
            if score>.95:
                pool.append(solution)
                if len(pool)>100:pool.pop(1)
            if score>.98:
                witness={'version':1,'probabilities':solution.tolist(),'syndrome':syndrome}
                (directory/f'c{mode}-{attempt}-{rank}_{score:.8f}.json').write_text(json.dumps(witness))
                print('candidate',attempt,rank,syndrome,score,flush=True)
            if score>best:
                best=score;print('BEST',attempt,rank,syndrome,score,round(time.time()-started,1),flush=True)
        if attempt%10==0:print('progress',attempt,float(scores[0]),round(time.time()-started,1),flush=True)

if __name__=='__main__':main()
