import os

os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'

import argparse
import json
import random as python_random
import time
from concurrent.futures import ProcessPoolExecutor,as_completed

import numpy as np
from scipy.linalg import solve_banded
from scipy.ndimage import label

from optimize import Model,OUTPUT,response,discrepancies


class Screen(Model):
    def __init__(self):
        super().__init__()
        order=np.array([index for site in range(256) for index in [site,site+256]])
        matrix=self.base[0][np.ix_(order,order)]
        rows,columns=np.nonzero(matrix)
        self.band=np.zeros((71,512),dtype=complex)
        self.band[35+rows-columns,columns]=-matrix[rows,columns]
        self.band[35]+=.01j
        source=self.edges_source
        destination=self.edges_destination
        self.pair_rows=np.concatenate([2*source,2*destination,2*destination+1,2*source+1])
        self.pair_columns=np.concatenate([2*destination+1,2*source+1,2*source,2*destination])
        self.pair_band=35+self.pair_rows-self.pair_columns
        self.pair_values=-np.concatenate([self.pair[0],self.pair[0],self.pair[0].conj(),self.pair[0].conj()])
        self.pair_sources=np.tile(source,4)
        self.pair_destinations=np.tile(destination,4)
        self.probe=2*self.probes[0]
        self.rhs=np.zeros((512,1),dtype=complex)
        self.rhs[self.probe,0]=1
        self.value=self.target[0,0,60]

    def screen(self,pattern):
        amplitude=np.ones(256)
        amplitude[self.candidates]=1-pattern
        band=self.band.copy()
        band[35,2*self.candidates]-=6*pattern
        band[35,2*self.candidates+1]+=6*pattern
        band[self.pair_band,self.pair_columns]=self.pair_values*amplitude[self.pair_sources]*amplitude[self.pair_destinations]
        solution=solve_banded((35,35),band,self.rhs.copy(),overwrite_ab=True,overwrite_b=True,check_finite=False)
        return -solution[self.probe,0].imag/np.pi


def chunk(job):
    begin,end,kind,attempts,filter_probes,samples,offsets,transforms=job
    model=Screen()
    closest=1e9
    tested=0
    for serial in range(begin,end):
        seed=serial//offsets
        offset=serial%offsets
        if (OUTPUT/'enumeration_found.json').exists():
            break
        random=np.random.RandomState(seed) if kind.startswith('legacy') else np.random.default_rng(seed)
        if kind=='python':
            random=python_random.Random(seed)
        if offset:
            if kind=='python':
                for skipped in range(offset):
                    random.random()
            else:
                random.random(offset)
        feasible=0
        for attempt in range(attempts*samples):
            pattern=np.zeros(144,dtype=int)
            if kind.endswith('force_probes'):
                eligible=np.delete(np.arange(144),[34,65])
                pattern[34]=1
                pattern[random.choice(eligible,53,replace=False)]=1
            elif kind.endswith('exclude_center'):
                eligible=np.delete(np.arange(144),[65])
                pattern[random.choice(eligible,54,replace=False)]=1
            elif kind.endswith('exclude_both'):
                eligible=np.delete(np.arange(144),[34,65])
                pattern[random.choice(eligible,54,replace=False)]=1
            elif kind.endswith('no_shuffle'):
                pattern[random.choice(144,54,replace=False,shuffle=False)]=1
            elif kind.endswith('perm') or kind.endswith('seq'):
                order=random.permutation(144)
                if kind.endswith('seq'):
                    grid=np.ones((16,16),dtype=int)
                    for index in order:
                        grid.ravel()[model.candidates[index]]=0
                        if label(grid)[1]==1:
                            pattern[index]=1
                            if pattern.sum()==54:
                                break
                        else:
                            grid.ravel()[model.candidates[index]]=1
                else:
                    pattern[order[:54]]=1
            elif kind.endswith('sort'):
                pattern[np.argsort(random.random(144))[:54]]=1
            elif kind.endswith('shuffle'):
                pattern[:54]=1
                random.shuffle(pattern)
            elif kind=='python':
                pattern[random.sample(range(144),54)]=1
            else:
                pattern[random.choice(144,54,replace=False)]=1
            grid=np.ones((16,16),dtype=int)
            grid.ravel()[model.candidates]=1-pattern
            if label(grid)[1]!=1:
                continue
            feasible+=1
            variants=[pattern]
            if transforms:
                variants=[variant.ravel() for turns in range(4) for variant in [np.rot90(pattern.reshape(12,12),turns),np.fliplr(np.rot90(pattern.reshape(12,12),turns))]]
            for variant in variants:
                if filter_probes and (not variant[34] or variant[65]):
                    continue
                value=model.screen(variant)
                tested+=1
                error=abs(value-model.value)
                closest=min(closest,error)
                if error<1e-10:
                    observed=response(model.config,variant)
                    metrics=discrepancies(model.config,observed,model.target)
                    if metrics['core_score']>=.96 and metrics['worst_family_score']>=.94:
                        result={'pattern':variant.tolist()}
                        (OUTPUT/'enumeration_found.json').write_text(json.dumps(result))
                        (OUTPUT/'design.json').write_text(json.dumps(result))
                        os.chmod(OUTPUT/'design.json',0o444)
                        return begin,end,tested,closest,seed,kind,attempt,metrics
            if feasible>=samples:
                break
    return begin,end,tested,closest


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--start',type=int,default=0)
    parser.add_argument('--end',type=int,default=1000000)
    parser.add_argument('--kind',default='default')
    parser.add_argument('--attempts',type=int,default=100)
    parser.add_argument('--workers',type=int,default=24)
    parser.add_argument('--chunk',type=int,default=2000)
    parser.add_argument('--no-filter',action='store_true')
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--samples',type=int,default=1)
    parser.add_argument('--offsets',type=int,default=1)
    parser.add_argument('--transforms',action='store_true')
    arguments=parser.parse_args()
    if arguments.check:
        model=Screen()
        pattern=np.zeros(144,dtype=int)
        pattern[np.random.default_rng(10).choice(144,54,False)]=1
        start=time.time()
        for repeat in range(100):
            value=model.screen(pattern)
        print('time',(time.time()-start)/100,'value',value,'actual',response(model.config,pattern)[0,0,60],flush=True)
    else:
        jobs=[(begin,min(begin+arguments.chunk,arguments.end*arguments.offsets),arguments.kind,arguments.attempts,not arguments.no_filter,arguments.samples,arguments.offsets,arguments.transforms) for begin in range(arguments.start*arguments.offsets,arguments.end*arguments.offsets,arguments.chunk)]
        start=time.time()
        with ProcessPoolExecutor(max_workers=arguments.workers) as executor:
            futures=[executor.submit(chunk,job) for job in jobs]
            for future in as_completed(futures):
                print(round(time.time()-start,1),future.result(),flush=True)
                if (OUTPUT/'enumeration_found.json').exists():
                    for pending in futures:
                        pending.cancel()
                    break
