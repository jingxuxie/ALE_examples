import json
import time
import itertools
from pathlib import Path
import numpy as np
from nominal import solve, PARTICIPANT

def canonical(syndrome):
    variations=[]
    for flip_col,flip_row in itertools.product((False,True),repeat=2):
        variations.append(tuple(sorted(4*(4-detector//4 if flip_col else detector//4)+(3-detector%4 if flip_row else detector%4) for detector in syndrome)))
    return min(variations)

def main():
    rng=np.random.default_rng(562145)
    baseline=json.loads((PARTICIPANT/'baseline/champion.json').read_text())
    base=np.array(baseline['probabilities'])
    out=Path('nominal_search');out.mkdir(exist_ok=True)
    all_syndromes=[]
    for count in [3,4,5,6]:
        choices=[]
        for syndrome in itertools.combinations(range(20),count):
            if len({detector//4 for detector in syndrome})<3 or len({detector%4 for detector in syndrome})<3:continue
            if syndrome==canonical(syndrome):choices.append(syndrome)
        rng.shuffle(choices)
        all_syndromes.append(choices)
    print('counts',list(map(len,all_syndromes)),flush=True)
    best=-1e10
    elites=[]
    started=time.time()
    for attempt in range(20000):
        if attempt<300:
            syndrome=baseline['syndrome']
            if attempt%5==0:probabilities=rng.uniform(.02,.14,39)
            else:probabilities=np.clip(base+rng.normal(0,.012+.003*(attempt%20),39),.02,.14)
        elif attempt<600:
            syndrome=[0,2,5,13,16,18]
            probabilities=rng.uniform(.02,.14,39)
        elif attempt%5==0 and elites:
            prior=elites[rng.integers(len(elites))]
            syndrome=prior['syndrome']
            probabilities=np.clip(np.array(prior['probabilities'])+rng.normal(0,.025,39),.02,.14)
        else:
            category=rng.choice(4,p=[.15,.4,.15,.3])
            syndrome=list(all_syndromes[category][rng.integers(len(all_syndromes[category]))])
            probabilities=rng.uniform(.02,.14,39)
        score,probabilities,result=solve(probabilities,syndrome,physical=int(rng.integers(2)),iterations=180)
        if score>.98:
            witness={'version':1,'probabilities':probabilities.tolist(),'syndrome':syndrome}
            filename=out/f'b{attempt}_{score:.8f}.json'
            filename.write_text(json.dumps(witness))
            elites.append(witness)
            if len(elites)>200:elites.pop(0)
        if score>best:
            best=score
            print('BEST',attempt,syndrome,score,round(time.time()-started,2),flush=True)
        if attempt%100==0:print('progress',attempt,best,score,round(time.time()-started,2),flush=True)

if __name__=='__main__':main()
