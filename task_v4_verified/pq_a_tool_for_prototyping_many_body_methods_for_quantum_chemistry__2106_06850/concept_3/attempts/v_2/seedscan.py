import argparse
import ctypes
import time
import numpy as np
import fermion
from search import Engine, LIB, INT


LIB.support_batch.argtypes=[ctypes.c_int,ctypes.c_int,INT,ctypes.c_int,INT]
parser=argparse.ArgumentParser()
parser.add_argument('--case',type=int,default=0)
parser.add_argument('--limit',type=int,default=300000)
args=parser.parse_args()
engine=Engine(fermion.load_cases()[args.case])
engine.best=engine.load()[2]
length=engine.case.max_gates
best=2.0
for variant in ['integer','choice','interleaved']:
    full=0
    for begin in range(0,args.limit,2000):
        seeds=list(range(begin,min(begin+2000,args.limit)))
        labels=np.empty((len(seeds),length),np.int32)
        angles=np.empty((len(seeds),length))
        for row,seed in enumerate(seeds):
            rng=np.random.default_rng(seed)
            if variant=='integer':
                labels[row]=rng.integers(250,size=length)
                angles[row]=rng.uniform(-1,1,size=length)
            elif variant=='choice':
                labels[row]=rng.choice(250,size=length,replace=False)
                angles[row]=rng.uniform(-1,1,size=length)
            else:
                raw=rng.bit_generator.random_raw(3*((length+1)//2))
                words=raw[::3]
                labels[row,::2]=((words&np.uint64(0xffffffff))*np.uint64(250))>>np.uint64(32)
                labels[row,1::2]=((words[:length//2]>>np.uint64(32))*np.uint64(250))>>np.uint64(32)
                angles[row,::2]=(raw[1::3]>>np.uint64(11)).astype(float)*(2.0**-52)-1
                angles[row,1::2]=(raw[2::3][:length//2]>>np.uint64(11)).astype(float)*(2.0**-52)-1
        sizes=np.empty(len(seeds),np.int32)
        LIB.support_batch(len(seeds),length,labels,0,sizes)
        for row in np.flatnonzero(sizes==100):
            full+=1
            for initial in [angles[row],angles[row]*np.pi,(angles[row]+1)*0.6]:
                result=engine.optimize(labels[row],initial,400)
                if result[2]<best:
                    best=result[2]
                    print('seedbest',variant,seeds[row],'loss',best,'full',full,'elapsed',time.time()-engine.started,flush=True)
                if result[2]<engine.best:
                    engine.save(*result)
                if result[2]<1e-10:
                    print('SOLVED',variant,seeds[row],flush=True)
                    raise SystemExit
        if begin%20000==0:
            print('scan',variant,begin,'full',full,'best',best,'elapsed',time.time()-engine.started,flush=True)
