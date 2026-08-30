import os

os.environ['OPENBLAS_NUM_THREADS']='1'

import itertools
import json
import time
from concurrent.futures import ProcessPoolExecutor,as_completed

import numpy as np
from scipy.ndimage import label

from enumerate_patterns import Screen
from optimize import OUTPUT,response,discrepancies


def batch(masks):
    model=Screen()
    closest=1e9
    tested=0
    for mask in masks:
        if (OUTPUT/'enumeration_found.json').exists():
            break
        pattern=np.array([(mask>>index)&1 for index in range(144)],dtype=int)
        grid=np.ones((16,16),dtype=int)
        grid.ravel()[model.candidates]=1-pattern
        if label(grid)[1]!=1:
            continue
        error=abs(model.screen(pattern)-model.value)
        closest=min(closest,error)
        tested+=1
        if error<1e-10:
            metrics=discrepancies(model.config,response(model.config,pattern),model.target)
            if metrics['core_score']>=.96 and metrics['worst_family_score']>=.94:
                result={'pattern':pattern.tolist()}
                (OUTPUT/'enumeration_found.json').write_text(json.dumps(result))
                (OUTPUT/'design.json').write_text(json.dumps(result))
                os.chmod(OUTPUT/'design.json',0o444)
                print('FOUND',metrics,flush=True)
                break
    return tested,closest


if __name__=='__main__':
    masks=set()
    def add(mask):
        if mask.bit_count()==54 and mask&(1<<34) and not mask&(1<<65):
            masks.add(mask)
    for width,height,count_x,count_y in [(1,1,9,6),(1,1,6,9),(2,3,3,3),(3,2,3,3),(1,3,6,3),(3,1,3,6),(1,2,9,3),(2,1,3,9)]:
        columns=[starts for starts in itertools.combinations(range(13-width),count_x) if all(next_start-start>=width for start,next_start in zip(starts,starts[1:]))]
        rows=[starts for starts in itertools.combinations(range(13-height),count_y) if all(next_start-start>=height for start,next_start in zip(starts,starts[1:]))]
        for column_starts in columns:
            row_mask=sum(1<<(column+offset) for column in column_starts for offset in range(width))
            for row_starts in rows:
                mask=sum(row_mask<<((row+offset)*12) for row in row_starts for offset in range(height))
                add(mask)
    coordinates=np.array([(column,row) for row in range(12) for column in range(12)])
    for modulo in range(3,33):
        for first in range(modulo):
            for second in range(modulo):
                projection=(first*coordinates[:,0]+second*coordinates[:,1])%modulo
                for shift in range(modulo):
                    for threshold in set([int(.375*modulo),int(np.ceil(.375*modulo))]):
                        pattern=(projection+shift)%modulo<threshold
                        if pattern.sum()==54 and pattern[34] and not pattern[65]:
                            mask=sum(1<<int(index) for index in np.flatnonzero(pattern))
                            add(mask)
    masks=list(masks)
    print('PATTERNS',len(masks),flush=True)
    start=time.time()
    with ProcessPoolExecutor(max_workers=24) as executor:
        jobs=[executor.submit(batch,masks[offset:offset+1000]) for offset in range(0,len(masks),1000)]
        for future in as_completed(jobs):
            print(time.time()-start,future.result(),flush=True)
