import os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['SPARSE']='1'
os.environ['KEEPALL']='0'
os.environ['TEMPERATURE']='0'
import json
import time
from pathlib import Path
import numpy as np
from optimize import Problem,oracle,check

def main():
    initial=check.load_submission('witness.json')
    problem=Problem(initial)
    seen=set();results=[];started=time.time()
    paths=list(Path('.').rglob('*.json'))
    for index,path in enumerate(paths):
        try:data=check.load_submission(str(path))
        except (ValueError,OSError):continue
        key=(tuple(data['syndrome']),tuple(data['probabilities']))
        if key in seen:continue
        seen.add(key)
        rates=np.array(data['probabilities'])
        physical=int(oracle(rates[None,:],data['syndrome'],0,False)[0][0,0]<0)
        problem.syndrome=data['syndrome'];problem.physical=physical
        score=float(problem.evaluate(rates)[0].min())
        results.append((score,str(path),physical))
        if len(results)%250==0:print('SCREEN',len(results),round(time.time()-started,1),max(results)[:2],flush=True)
    os.environ['SPARSE']='0'
    problem=Problem(initial)
    best=-1e10;winner=None
    for bound,path,physical in sorted(results,reverse=True):
        if bound<best-1e-12:break
        data=check.load_submission(path)
        problem.syndrome=data['syndrome'];problem.physical=physical
        score=float(problem.evaluate(np.array(data['probabilities']))[0].min())
        print('FULL',path,score,flush=True)
        if score>best:best=score;winner=path
    Path('chosen_source.txt').write_text(winner)
    print('WINNER',winner,best,'seconds',time.time()-started,flush=True)

if __name__=='__main__':main()
