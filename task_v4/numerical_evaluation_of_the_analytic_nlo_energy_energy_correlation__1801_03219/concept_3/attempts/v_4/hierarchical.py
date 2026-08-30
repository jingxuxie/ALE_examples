import argparse
import json
from pathlib import Path
import time
import ctypes

import numpy as np

parser=argparse.ArgumentParser()
parser.add_argument('--size',type=int,default=64)
parser.add_argument('--seed',type=int,default=1)
parser.add_argument('--beta',type=float,default=0.5)
parser.add_argument('--seconds',type=float,default=1200)
parser.add_argument('--stage-seconds',type=float,default=120)
parser.add_argument('--known')
parser.add_argument('--backtrack',action='store_true')
parser.add_argument('--noise',type=float,default=0)
parser.add_argument('--pairs',action='store_true')
parser.add_argument('--parity',action='store_true')
arguments=parser.parse_args()
root=Path(__file__).resolve().parent
target=np.array(json.loads((root/'../../participant/input/target.json').read_text())['cyclic_autocorrelation'],dtype=np.int64)
generator=np.random.default_rng(arguments.seed)
started=time.monotonic()
size=arguments.size
known=np.load(arguments.known).astype(float) if arguments.known else None
solutions={}
if known is not None:
    solutions[len(known)]=known.copy()
visited=set()
if arguments.pairs:
    library=ctypes.CDLL(str(root/'pair_projection.so'))
    array_type=np.ctypeslib.ndpointer(dtype=np.float64,ndim=1,flags='C_CONTIGUOUS')
    library.project_pairs.argtypes=[array_type,array_type,array_type,ctypes.c_int,ctypes.c_int]
while size<=4096 and time.monotonic()-started<arguments.seconds:
    expected=target.reshape(-1,size).sum(axis=0)
    magnitudes=np.sqrt(np.maximum(np.fft.rfft(expected).real,0))
    capacity=8192//size
    parity_projection=None
    if arguments.parity and known is not None:
        from parity import ParityProjection
        parity_projection=ParityProjection(known,expected,capacity)
        print('PARITY',size,'feasible',parity_projection.feasible,'free',parity_projection.free_count,flush=True)
        if not parity_projection.feasible:
            if arguments.backtrack and size>arguments.size:
                size//=2;known=solutions.get(size//2)
                continue
            break
    if known is None:
        values=generator.normal(1024/size,np.sqrt(1280/size),size)
    else:
        values=np.empty(size)
        values[:size//2]=known/2+generator.normal(0,np.sqrt(1280/size),size//2)
        values[size//2:]=known-values[:size//2]
        known_spectrum=np.fft.rfft(known)
        lower=np.maximum(0,known-capacity)
        upper=np.minimum(known,capacity)
    stage_started=time.monotonic()
    last_log=stage_started
    iterations=0
    best=float('inf')
    solved=False
    while time.monotonic()-stage_started<arguments.stage_seconds and time.monotonic()-started<arguments.seconds:
        if known is None:
            discrete=np.clip(np.rint(values),0,capacity)
        else:
            if parity_projection is not None:
                discrete=parity_projection.project(values)
                if discrete is None:break
            elif arguments.pairs and size>=256:
                discrete=np.empty(size)
                if not library.project_pairs(values,discrete,known,size,capacity):
                    print('INFEASIBLE FOLD',size,flush=True)
                    break
            else:
                first=np.clip(np.rint((values[:size//2]-values[size//2:]+known)/2),lower,upper)
                discrete=np.concatenate([first,known-first])
        spectrum=np.fft.rfft(2*discrete-values)
        spectrum*=magnitudes/np.maximum(abs(spectrum),1e-20)
        spectrum[0]=1024
        if known is not None:
            spectrum[::2]=known_spectrum
        second=np.fft.irfft(spectrum,n=size)
        difference=second-discrete
        values+=arguments.beta*difference
        residual=float(difference@difference)
        best=min(best,residual)
        iterations+=1
        if arguments.noise and iterations%1000==0:
            if known is None:
                values+=generator.normal(0,arguments.noise,size)
            else:
                perturbation=generator.normal(0,arguments.noise,size//2)
                values[:size//2]+=perturbation
                values[size//2:]-=perturbation
        now=time.monotonic()
        if now-last_log>10 or residual<1e-8:
            print('size',size,'seconds',round(now-started,2),'iterations',iterations,'residual',residual,'best',best,flush=True)
            last_log=now
        if residual<1e-8:
            actual=np.rint(np.fft.irfft(abs(np.fft.rfft(discrete))**2,n=size)).astype(np.int64)
            if np.array_equal(actual,expected):
                candidate=discrete.astype(np.int64)
                identity=(tuple(known) if known is not None else (),min(tuple(candidate),tuple(np.roll(candidate,size//2))))
                if arguments.backtrack and identity in visited:
                    if known is None:
                        values=generator.normal(1024/size,np.sqrt(1280/size),size)
                    else:
                        values[:size//2]=known/2+generator.normal(0,np.sqrt(1280/size),size//2)
                        values[size//2:]=known-values[:size//2]
                    continue
                visited.add(identity)
                solutions[size]=candidate.astype(float)
                np.save(root/f'fold_{arguments.seed}_{size}.npy',candidate)
                print('FOLD SOLVED',size,flush=True)
                if size==4096 and np.array_equal(np.bincount(candidate,minlength=3),[3328,512,256]) and not np.any(candidate*np.roll(candidate,1)):
                    (root/'design.json').write_text(json.dumps({'schema_version':1,'a':candidate.tolist()},separators=(',',':'))+'\n')
                    print('EXACT SOLUTION',flush=True)
                known=candidate.astype(float)
                size*=2
                solved=True
                break
    if not solved:
        print('STAGE FAILED',size,'best',best,flush=True)
        if arguments.backtrack:
            size=max(arguments.size,size//2)
            known=solutions.get(size//2)
        else:
            break
