import os

os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor,as_completed

import numpy as np
from scipy.ndimage import label

from enumerate_patterns import Screen
from optimize import OUTPUT,response,discrepancies


def search(job):
    masks,halos,anchor,number=job
    model=Screen()
    anchor_mask=masks[anchor]
    available=[(mask,halo) for mask,halo in zip(masks,halos) if not halo&anchor_mask and not mask&(1<<65)]
    tested=0
    closest=1e9
    def recurse(current,start,remaining):
        nonlocal tested,closest
        if (OUTPUT/'enumeration_found.json').exists():
            return
        if remaining==0:
            pattern=np.array([(current>>index)&1 for index in range(144)],dtype=int)
            grid=np.ones((16,16),dtype=int)
            grid.ravel()[model.candidates]=1-pattern
            if label(grid)[1]!=1:
                return
            value=model.screen(pattern)
            tested+=1
            error=abs(value-model.value)
            closest=min(closest,error)
            if error<1e-10:
                metrics=discrepancies(model.config,response(model.config,pattern),model.target)
                if metrics['core_score']>=.96 and metrics['worst_family_score']>=.94:
                    result={'pattern':pattern.tolist()}
                    (OUTPUT/'enumeration_found.json').write_text(json.dumps(result))
                    (OUTPUT/'design.json').write_text(json.dumps(result))
                    os.chmod(OUTPUT/'design.json',0o444)
                    print('FOUND',anchor,metrics,flush=True)
            return
        for index in range(start,len(available)-remaining+1):
            if not current&available[index][1]:
                recurse(current|available[index][0],index+1,remaining-1)
    recurse(anchor_mask,0,number-1)
    return anchor,tested,closest


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--area',type=int,default=9)
    parser.add_argument('--workers',type=int,default=16)
    parser.add_argument('--spacing',type=int,default=0)
    arguments=parser.parse_args()
    shapes={9:[(3,3)],18:[(3,6),(6,3),(2,9),(9,2)],27:[(3,9),(9,3)]}[arguments.area]
    masks=[]
    halos=[]
    for width,height in shapes:
        for column in range(12-width+1):
            for row in range(12-height+1):
                mask=0
                for offset_column in range(width):
                    for offset_row in range(height):
                        mask|=1<<((row+offset_row)*12+column+offset_column)
                masks.append(mask)
                halo=0
                for halo_column in range(max(0,column-arguments.spacing),min(12,column+width+arguments.spacing)):
                    for halo_row in range(max(0,row-arguments.spacing),min(12,row+height+arguments.spacing)):
                        halo|=1<<(halo_row*12+halo_column)
                halos.append(halo)
    anchors=[index for index,mask in enumerate(masks) if mask&(1<<34) and not mask&(1<<65)]
    print('SHAPES',len(masks),'anchors',len(anchors),flush=True)
    start=time.time()
    with ProcessPoolExecutor(max_workers=arguments.workers) as executor:
        futures=[executor.submit(search,(masks,halos,anchor,54//arguments.area)) for anchor in anchors]
        for future in as_completed(futures):
            print(time.time()-start,future.result(),flush=True)
